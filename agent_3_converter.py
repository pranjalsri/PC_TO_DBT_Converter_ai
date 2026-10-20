import argparse
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from threading import Event

from utils.pick_llm import llm
from utils.powercenter_xml import (
    build_mapping_context,
    discover_powercenter_xml_files,
    get_attribute,
    get_mapping_name,
    get_xml_output_stem,
    load_powercenter_xml,
    local_tag as _local_tag,
)
from utils.run_control import raise_if_cancelled


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_XML_PATH = PROJECT_ROOT / "Input_xml"
def _name(element: ET.Element) -> str:
    return get_attribute(element, "NAME") or ""


def _slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    if not value:
        raise ValueError("A mapping name must contain at least one letter or digit.")
    if value[0].isdigit():
        value = f"model_{value}"
    return value


def _extract_sql(response: str, mapping_name: str) -> str:
    if not response.strip():
        raise ValueError(f"The LLM returned an empty SQL response for {mapping_name!r}.")

    fenced_sql = re.search(r"```(?:sql)?\s*(.*?)```", response, re.IGNORECASE | re.DOTALL)
    sql = fenced_sql.group(1).strip() if fenced_sql else response.strip()
    if not sql:
        raise ValueError(f"The LLM returned no SQL for mapping {mapping_name!r}.")
    if not re.search(r"\b(select|with)\b", sql, re.IGNORECASE):
        raise ValueError(
            f"The LLM response for {mapping_name!r} does not appear to contain SQL. "
            f"Response begins: {response[:300]!r}"
        )
    return sql + "\n"


def _source_yaml(root: ET.Element) -> str:
    lines = [
        "version: 2",
        "",
        "sources:",
        "  - name: legacy",
        '    schema: "{{ var(\'legacy_source_schema\') }}"',
        "    tables:",
    ]
    seen_sources: set[str] = set()
    for source in root.iter():
        if _local_tag(source.tag) != "SOURCE":
            continue
        source_name = _name(source)
        if not source_name or source_name in seen_sources:
            continue
        seen_sources.add(source_name)
        lines.extend([
            f"      - name: {json.dumps(source_name)}",
            f"        identifier: {json.dumps(source_name)}",
        ])
        fields = [
            field for field in source
            if _local_tag(field.tag) == "SOURCEFIELD" and _name(field)
        ]
        if fields:
            lines.append("        columns:")
            for field in fields:
                data_type = next(
                    (value for key, value in field.attrib.items() if key.upper() == "DATATYPE"),
                    "unspecified",
                )
                lines.extend([
                    f"          - name: {json.dumps(_name(field))}",
                    f"            description: {json.dumps('PowerCenter type: ' + data_type)}",
                ])
    return "\n".join(lines) + "\n"


def _conversion_prompt(mapping_name: str, xml_context: str) -> str:
    return f"""You are a senior data engineer migrating Informatica PowerCenter to dbt.
Convert this mapping into one readable dbt model using Snowflake SQL.

Requirements:
- Use CTEs for the transformation stages and retain the original transformation names
  in CTE names or comments.
- Preserve only logic supported by the XML; do not invent columns or business rules.
- Use {{ source('legacy', 'SOURCE_TABLE') }} for raw source tables; each source is declared
  in the generated models/_sources.yml.
- Include {{ config(materialized='table') }} at the top.
- Flag unsupported or ambiguous operations with a `-- TODO(migration):` SQL comment.
- Return only executable SQL, in one ```sql code block. No prose.

Mapping name: {mapping_name}
PowerCenter XML context:
{xml_context}
"""


def _convert_xml_file(
    xml_path: str | os.PathLike[str],
    output_dir: str | os.PathLike[str] | None = None,
    project_name: str | None = None,
    stop_event: Event | None = None,
) -> Path:
    """Convert each mapping in one PowerCenter XML file to a dbt SQL model."""
    source_path = Path(xml_path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"PowerCenter XML file not found: {source_path}")

    root, mappings = load_powercenter_xml(source_path)

    output_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else PROJECT_ROOT / "converted"
    )
    project_dir = output_root / f"{_slug(project_name or source_path.stem)}_dbt"
    if project_dir.exists():
        raise FileExistsError(
            f"Output project already exists: {project_dir}. "
            "Choose another output directory or rename the existing project."
        )

    seen_names: set[str] = set()
    models: list[tuple[str, str]] = []
    for index, mapping in enumerate(mappings, start=1):
        raise_if_cancelled(stop_event)
        mapping_name = get_mapping_name(mapping, f"mapping_{index}")
        model_name = _slug(mapping_name)
        if model_name in seen_names:
            raise ValueError(f"Mapping names produce duplicate dbt model name {model_name!r}.")
        seen_names.add(model_name)

        xml_context = build_mapping_context(root, mapping, redact_sensitive=True)
        prompt = _conversion_prompt(mapping_name, xml_context)
        response = llm.invoke(prompt)
        raise_if_cancelled(stop_event)
        response_text = response.content
        if not isinstance(response_text, str):
            raise ValueError(
                f"The LLM returned {type(response_text).__name__}, not text, "
                f"for mapping {mapping_name!r}."
            )
        models.append((model_name, _extract_sql(response_text, mapping_name)))

    raise_if_cancelled(stop_event)
    project_dir.mkdir(parents=True)
    try:
        (project_dir / "models").mkdir()
        (project_dir / "models" / "_sources.yml").write_text(
            _source_yaml(root),
            encoding="utf-8",
        )
        for model_name, sql in models:
            (project_dir / "models" / f"{model_name}.sql").write_text(
                sql,
                encoding="utf-8",
            )

        project_name = _slug(project_dir.name.removesuffix("_dbt"))
        (project_dir / "dbt_project.yml").write_text(
            f"""name: '{project_name}_dbt'
version: '1.0.0'
config-version: 2
profile: 'powercenter_migration'
model-paths: ['models']
target-path: 'target'
clean-targets:
  - 'target'
  - 'dbt_packages'
vars:
  legacy_source_schema: 'REPLACE_WITH_SOURCE_SCHEMA'
models:
  {project_name}_dbt:
    +materialized: table
""",
            encoding="utf-8",
        )
        (project_dir / "README.md").write_text(
            f"""# {project_name}_dbt

Generated from `{source_path.name}` by `agent_3_converter.py`.

Review each SQL model, especially any `TODO(migration)` comments. Configure the
`powercenter_migration` profile in your local dbt `profiles.yml`; this generated
project does not contain database credentials. Validate with `dbt parse` and,
after configuring a profile, `dbt compile`.
""",
            encoding="utf-8",
        )
    except Exception:
        # Do not leave a partially generated project behind if writing fails.
        for path in sorted(project_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        project_dir.rmdir()
        raise

    print(f"[Agent 3 Complete] Generated {len(models)} dbt model(s) in: {project_dir}")
    return project_dir


def convert_pc_to_dbt(
    xml_path: str | os.PathLike[str] = DEFAULT_XML_PATH,
    output_dir: str | os.PathLike[str] | None = None,
    stop_event: Event | None = None,
) -> list[Path]:
    """Convert every XML file at the supplied file or directory path."""
    xml_files = discover_powercenter_xml_files(xml_path)
    output_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else PROJECT_ROOT / "converted"
    )
    projects = []
    for xml_file in xml_files:
        raise_if_cancelled(stop_event)
        projects.append(_convert_xml_file(
            xml_file,
            output_root,
            get_xml_output_stem(xml_file, xml_path),
            stop_event,
        ))
    print(f"[Agent 3 Complete] Converted {len(projects)} XML file(s).")
    return projects


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert one or all PowerCenter XML exports into dbt projects."
    )
    parser.add_argument(
        "xml_path",
        nargs="?",
        default=str(DEFAULT_XML_PATH),
        help=f"PowerCenter XML file or directory (default: {DEFAULT_XML_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        help="Parent directory for the generated project (default: ./converted).",
    )
    args = parser.parse_args()
    convert_pc_to_dbt(args.xml_path, args.output_dir)


if __name__ == "__main__":
    main()
