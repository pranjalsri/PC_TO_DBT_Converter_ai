import copy
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SENSITIVE_ATTRIBUTE_NAMES = ("password", "secret", "credential", "token", "api_key", "apikey")


def local_tag(tag: str) -> str:
    """Return an XML tag name without its namespace and in uppercase."""
    return tag.rsplit("}", 1)[-1].upper()


def get_attribute(element: ET.Element, name: str) -> str | None:
    """Read an XML attribute case-insensitively."""
    wanted = name.upper()
    return next(
        (value for key, value in element.attrib.items() if key.upper() == wanted),
        None,
    )


def get_mapping_name(mapping: ET.Element, fallback: str = "Unnamed mapping") -> str:
    return get_attribute(mapping, "NAME") or fallback


def discover_powercenter_xml_files(
    input_path: str | os.PathLike[str],
) -> list[Path]:
    """Return one XML file or all XML files recursively under a directory."""
    path = Path(input_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"XML input path not found: {path}")
    if path.is_file():
        if path.suffix.lower() != ".xml":
            raise ValueError(f"Input file must have an .xml extension: {path}")
        return [path.resolve()]

    xml_files = sorted(
        (
            item.resolve()
            for item in path.rglob("*")
            if item.is_file() and item.suffix.lower() == ".xml"
        ),
        key=lambda item: str(item).casefold(),
    )
    if not xml_files:
        raise FileNotFoundError(f"No .xml files found in: {path}")
    return xml_files


def get_xml_output_stem(
    xml_file: str | os.PathLike[str],
    input_path: str | os.PathLike[str],
) -> str:
    """Create a stable output name that preserves nested input folders."""
    file_path = Path(xml_file).resolve()
    root_path = Path(input_path).expanduser().resolve()
    input_root = root_path if root_path.is_dir() else root_path.parent
    try:
        relative_path = file_path.relative_to(input_root)
    except ValueError:
        relative_path = Path(file_path.name)
    parts = (*relative_path.parts[:-1], relative_path.stem)
    output_stem = "__".join(parts)
    output_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", output_stem).strip("_")
    return output_stem or file_path.stem


def load_powercenter_xml(
    xml_path: str | os.PathLike[str],
) -> tuple[ET.Element, list[ET.Element]]:
    """Parse a PowerCenter export and return its root and all mapping elements."""
    path = Path(xml_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    root = ET.parse(path).getroot()
    mappings = [element for element in root.iter() if local_tag(element.tag) == "MAPPING"]
    if not mappings:
        raise ValueError(f"No MAPPING elements found in XML file: {path}")
    return root, mappings


def build_mapping_context(
    root: ET.Element,
    mapping: ET.Element,
    *,
    redact_sensitive: bool = False,
) -> str:
    """Serialize source and target definitions together with a mapping, without mutating input."""
    context = ET.Element("MAPPING_CONTEXT")
    for element in root.iter():
        if local_tag(element.tag) in {"SOURCE", "TARGET"}:
            context.append(copy.deepcopy(element))
    context.append(copy.deepcopy(mapping))

    if redact_sensitive:
        for element in context.iter():
            labels = " ".join(
                value
                for key, value in element.attrib.items()
                if key.upper() in {"NAME", "KEY"}
            ).lower()
            for key in list(element.attrib):
                if any(secret in key.lower() for secret in SENSITIVE_ATTRIBUTE_NAMES):
                    element.attrib[key] = "[REDACTED]"
                elif key.upper() in {"VALUE", "VAL"} and any(
                    secret in labels for secret in SENSITIVE_ATTRIBUTE_NAMES
                ):
                    element.attrib[key] = "[REDACTED]"

    return ET.tostring(context, encoding="unicode")
