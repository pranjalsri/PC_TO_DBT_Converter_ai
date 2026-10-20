import argparse
from pathlib import Path
from threading import Event

from utils.pick_llm import llm
from utils.powercenter_xml import (
    build_mapping_context,
    discover_powercenter_xml_files,
    get_mapping_name,
    get_xml_output_stem,
    load_powercenter_xml,
)
from utils.run_control import raise_if_cancelled


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_XML_PATH = PROJECT_ROOT / "Input_xml"


def _test_case_prompt(mapping_name: str, xml_snippet: str) -> str:
    return f"""Role: You are an expert QA Automation and ETL Testing Engineer specializing
in data warehousing and Informatica PowerCenter migrations and validation.

Task: Generate detailed, executable test cases for this PowerCenter mapping. Base test logic
only on the supplied XML. Do not invent business rules, columns, or expected values. If an
expected value cannot be determined from the XML, state what reference data or business rule
is needed.

For every test case, include these fields:
- Test Case ID (for example, TC_ETL_MAP_001)
- Description
- Steps (numbered)
- Logic (XML-derived expressions, joins, filters, or SQL where available)
- Acceptance Criteria (measurable validation outcome; mark unknown values as requiring
  business-owner confirmation)

Cover relevant source-to-target columns, transformations, lookup/router/filter logic, data
types, null handling, and error/reject handling. Do not claim a feature exists unless it
appears in the XML.

Mapping name: {mapping_name}
PowerCenter mapping XML:
{xml_snippet}
"""


def _test_case_file(
    xml_path: str | Path,
    output_path: str | Path | None = None,
    stop_event: Event | None = None,
) -> Path:
    """Generate and save test cases for every mapping in one XML export."""
    source_path = Path(xml_path).expanduser()
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"PowerCenter XML file not found: {source_path}")

    root, mappings = load_powercenter_xml(source_path)

    sections: list[str] = []
    for index, mapping in enumerate(mappings, start=1):
        raise_if_cancelled(stop_event)
        mapping_name = get_mapping_name(mapping, f"mapping_{index}")
        prompt = _test_case_prompt(
            mapping_name,
            build_mapping_context(root, mapping),
        )
        response = llm.invoke(prompt)
        raise_if_cancelled(stop_event)
        content = response.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"The LLM returned an empty/non-text response for {mapping_name!r}.")
        sections.append(f"# Test cases: {mapping_name}\n\n{content.strip()}")

    raise_if_cancelled(stop_event)
    report = "\n\n---\n\n".join(sections) + "\n"
    if output_path is None:
        destination = PROJECT_ROOT / "output_tests" / f"{source_path.stem}_test_cases.md"
    else:
        destination = Path(output_path).expanduser()
        if not destination.is_absolute():
            destination = PROJECT_ROOT / destination
        if destination.suffix.lower() != ".md":
            destination = destination / f"{source_path.stem}_test_cases.md"
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")

    print(report)
    print(f"Test cases for {len(mappings)} mapping(s) saved to: {destination}")
    return destination


def test_case(
    xml_path: str | Path = DEFAULT_XML_PATH,
    output_path: str | Path | None = None,
    stop_event: Event | None = None,
) -> list[Path]:
    """Generate a separate test-case report for each XML file or directory input."""
    xml_files = discover_powercenter_xml_files(xml_path)
    output_paths = []
    for xml_file in xml_files:
        raise_if_cancelled(stop_event)
        output_name = get_xml_output_stem(xml_file, xml_path)
        file_output = output_path
        if output_path is not None:
            requested_output = Path(output_path).expanduser()
            is_single_output_file = (
                requested_output.suffix.lower() == ".md" and len(xml_files) == 1
            )
            if not is_single_output_file:
                output_directory = (
                    requested_output.parent
                    if requested_output.suffix.lower() == ".md"
                    else requested_output
                )
                file_output = output_directory / f"{output_name}_test_cases.md"
        elif len(xml_files) > 1 or Path(xml_path).is_dir():
            file_output = (
                PROJECT_ROOT / "output_tests" / f"{output_name}_test_cases.md"
            )
        output_paths.append(_test_case_file(xml_file, file_output, stop_event))
    return output_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ETL test cases from a PowerCenter XML export."
    )
    parser.add_argument(
        "xml_path",
        nargs="?",
        default=str(DEFAULT_XML_PATH),
        help=f"PowerCenter XML file or directory (default: {DEFAULT_XML_PATH})",
    )
    parser.add_argument(
        "--output",
        help="Output Markdown file or directory (default: ./output_tests/).",
    )
    args = parser.parse_args()
    test_case(args.xml_path, args.output)


if __name__ == "__main__":
    main()
