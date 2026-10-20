import os
from threading import Event
from utils.pick_llm import llm
from utils.powercenter_xml import (
    build_mapping_context,
    discover_powercenter_xml_files,
    get_mapping_name,
    get_xml_output_stem,
    load_powercenter_xml,
)
import pandas as pd
from utils.run_control import raise_if_cancelled


def parse_xml(
    xml_path: str,
    output_path: str | None = None,
    stop_event: Event | None = None,
):
    print(f"Parsing XML file: {xml_path}")

    root, mapping_elements = load_powercenter_xml(xml_path)
    report_data = []

    for mapping in mapping_elements:
        raise_if_cancelled(stop_event)
        mapping_name = get_mapping_name(mapping)
        xml_snippet = build_mapping_context(root, mapping)

        prompt = f"""
You are an expert Data Migration Architect. Analyze this PowerCenter XML for mapping '{mapping_name}'.
Extract and summarize:
1. Source tables / definitions
2. Transformations used (e.g., Expression, Filter, Joiner, Lookup)
3. Target destination table

Provide the output clearly structured so it can be added to an Excel report.
XML:
{xml_snippet}
"""
        response = llm.invoke(prompt)
        raise_if_cancelled(stop_event)
        summary = response.content
        print(f"Response for mapping '{mapping_name}':\n{summary}\n")
        report_data.append({
            "Mapping Name": mapping_name,
            "Architecture Summary": summary,
            "Status": "Parsed & Analyzed Successfully",
        })

    raise_if_cancelled(stop_event)
    df = pd.DataFrame(report_data)
    output_dir = os.path.join(os.path.dirname(__file__), "output_reports")
    os.makedirs(output_dir, exist_ok=True)
    output_excel = output_path or os.path.join(
        output_dir,
        f"{os.path.splitext(os.path.basename(xml_path))[0]}_mapping_document.xlsx",
    )
    os.makedirs(os.path.dirname(output_excel) or ".", exist_ok=True)
    df.to_excel(output_excel, index=False)
    
    print(f"[Agent 1 Complete] Mapping document saved successfully to '{output_excel}'!")
    return report_data

if __name__ == "__main__":
    input_dir = os.path.join(os.path.dirname(__file__), "Input_xml")
    for xml_file in discover_powercenter_xml_files(input_dir):
        output_name = get_xml_output_stem(xml_file, input_dir)
        output_path = os.path.join(
            os.path.dirname(__file__),
            "output_reports",
            f"{output_name}_mapping_document.xlsx",
        )
        parse_xml(str(xml_file), output_path)
