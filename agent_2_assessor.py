import os
import re
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
import json
from utils.run_control import raise_if_cancelled


def parse_assessment_response(content: str) -> dict:
    if not content.strip():
        raise ValueError(
            "The LLM returned an empty response. Check that Ollama is running, "
            "the model is available, and the response was not truncated."
        )

    decoder = json.JSONDecoder()
    for index, character in enumerate(content):
        if character == "{":
            try:
                assessment, _ = decoder.raw_decode(content[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(assessment, dict):
                return assessment

    raise ValueError(
        "The LLM response did not contain a valid JSON object. "
        f"Response begins: {content[:500]!r}"
    )


def normalize_complexity(value: object, mapping_name: str) -> str:
    """Normalize a single Low/Medium/High label from model wording."""
    if isinstance(value, str):
        matches = {
            match.group(1).title()
            for match in re.finditer(r"\b(low|medium|high)\b", value, re.IGNORECASE)
        }
        if len(matches) == 1:
            return matches.pop()

    raise ValueError(
        f"The LLM returned invalid complexity {value!r} for mapping "
        f"{mapping_name!r}; expected exactly one of Low, Medium, or High."
    )


def run_agent_2(
    xml_path: str,
    output_path: str | None = None,
    stop_event: Event | None = None,
):
    print(f"Analyzing complexity of the XML file: {xml_path}")

    root, mapping_elements = load_powercenter_xml(xml_path)
    assessments = []
    for index, mapping in enumerate(mapping_elements, start=1):
        raise_if_cancelled(stop_event)
        mapping_name = get_mapping_name(mapping, f"mapping_{index}")
        xml_snippet = build_mapping_context(root, mapping)

        prompt = f"""Analyze this Informatica PowerCenter mapping for migration to dbt on Snowflake.
Use only evidence present in the XML. Assess:
- Complexity: Low for straightforward SQL transformations; Medium for multiple joins or aggregations; High for stateful variable ports, complex/unconnected lookups, multi-group routers, dynamic lookups, or other substantial refactoring else vhigh.
- Feasibility: a reasoned estimate from 0 to 100 based on conversion effort and risks. Do not use a fixed/default value.
- Reasoning: mention detected sources, targets, transformation types, key conversion obstacles, and recommended dbt modeling/materialization approach. Do not claim features that are absent from the XML.

Return exactly one JSON object, with no markdown or surrounding prose. Include:
- `mapping_name`: "{mapping_name}"
- `complexity`: exactly one of the strings "Low", "Medium", "High" or "VHigh"
- `feasibility_percentage`: a number from 0 to 100
- `reasoning`: an evidence-based explanation
Do not add an explanation or other words to the `complexity` field.

Mapping XML:
{xml_snippet}
"""
        response = llm.bind(format="json").invoke(prompt)
        raise_if_cancelled(stop_event)

        content = response.content
        if not isinstance(content, str):
            raise ValueError(
                f"The LLM returned content of unexpected type {type(content).__name__}, "
                "expected text containing a JSON object."
            )
        assessment = parse_assessment_response(content)

        complexity = normalize_complexity(
            assessment.get("complexity"),
            mapping_name,
        )
        assessment["complexity"] = complexity

        feasibility = assessment.get("feasibility_percentage")
        if (
            isinstance(feasibility, bool)
            or not isinstance(feasibility, (int, float))
            or not 0 <= feasibility <= 100
        ):
            raise ValueError(
                "The LLM response must set feasibility_percentage to a number from 0 to 100."
            )

        reasoning = assessment.get("reasoning")
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise ValueError("The LLM response must include non-empty reasoning.")

        assessment["mapping_name"] = mapping_name
        assessments.append(assessment)
        print(
            f"Assessed mapping: {mapping_name} | Complexity: {complexity} | "
            f"Feasibility: {feasibility}%"
        )
        
    raise_if_cancelled(stop_event)
    # Save the assessment to an Excel file in the output folder
    df = pd.DataFrame([
        {
            "Mapping Name": assessment["mapping_name"],
            "Complexity": assessment["complexity"],
            "Feasibility Percentage": f"{assessment['feasibility_percentage']}%",
            "Reasoning": assessment["reasoning"],
        }
        for assessment in assessments
    ])
    
    output_dir = os.path.join(os.path.dirname(__file__), "output_complexity")
    os.makedirs(output_dir, exist_ok=True)
    output_excel = output_path or os.path.join(
        output_dir,
        f"{os.path.splitext(os.path.basename(xml_path))[0]}_complexity_assessment.xlsx",
    )
    os.makedirs(os.path.dirname(output_excel) or ".", exist_ok=True)
    df.to_excel(output_excel, index=False)
    
    print(f"[Agent 2 Complete] Assessment report saved successfully to '{output_excel}'!")
    
    return assessments

if __name__ == "__main__":
    input_dir = os.path.join(os.path.dirname(__file__), "Input_xml")
    for xml_file in discover_powercenter_xml_files(input_dir):
        output_name = get_xml_output_stem(xml_file, input_dir)
        output_path = os.path.join(
            os.path.dirname(__file__),
            "output_complexity",
            f"{output_name}_complexity_assessment.xlsx",
        )
        run_agent_2(str(xml_file), output_path)