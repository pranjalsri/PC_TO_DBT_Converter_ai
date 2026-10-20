"""Run one or more PowerCenter migration agents from a single entry point.

Interactive usage: ``python agent_orchestrator.py``
Non-interactive usage: ``python agent_orchestrator.py --task assess --input Input_xml``
"""

import argparse
from pathlib import Path
from threading import Event
from typing import Literal

from utils.run_control import raise_if_cancelled
from agent1_Parser import parse_xml
from agent_2_assessor import run_agent_2
from agent_3_converter import convert_pc_to_dbt
from agent4_Test_case import test_case
from utils.powercenter_xml import discover_powercenter_xml_files, get_xml_output_stem


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_XML_PATH = PROJECT_ROOT / "Input_xml"
TASKS = ("parse", "assess", "convert", "test", "all")
TASK_ORDER = ("parse", "assess", "convert", "test")


def _resolve_input_path(input_path: str | Path) -> Path:
    path = Path(input_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def run_agents(
    task: Literal["parse", "assess", "convert", "test", "all"],
    input_path: str | Path = DEFAULT_XML_PATH,
    stop_event: Event | None = None,
) -> dict[str, list[Path]]:
    """Run the selected agent(s) for a PowerCenter XML file or directory."""
    resolved_input = _resolve_input_path(input_path)
    xml_files = discover_powercenter_xml_files(resolved_input)
    selected_tasks = TASK_ORDER if task == "all" else (task,)
    results: dict[str, list[Path]] = {}

    for selected_task in selected_tasks:
        raise_if_cancelled(stop_event)
        print(f"\n=== Running {selected_task} agent for {len(xml_files)} XML file(s) ===")
        if selected_task == "parse":
            output_dir = PROJECT_ROOT / "output_reports"
            results[selected_task] = []
            for xml_file in xml_files:
                raise_if_cancelled(stop_event)
                output_file = (
                    output_dir
                    / f"{get_xml_output_stem(xml_file, resolved_input)}_mapping_document.xlsx"
                )
                parse_xml(str(xml_file), str(output_file), stop_event)
                results[selected_task].append(output_file)
        elif selected_task == "assess":
            output_dir = PROJECT_ROOT / "output_complexity"
            results[selected_task] = []
            for xml_file in xml_files:
                raise_if_cancelled(stop_event)
                output_file = (
                    output_dir
                    / f"{get_xml_output_stem(xml_file, resolved_input)}_complexity_assessment.xlsx"
                )
                run_agent_2(str(xml_file), str(output_file), stop_event)
                results[selected_task].append(output_file)
        elif selected_task == "convert":
            results[selected_task] = convert_pc_to_dbt(
                resolved_input,
                PROJECT_ROOT / "converted",
                stop_event,
            )
        else:
            results[selected_task] = test_case(
                resolved_input,
                PROJECT_ROOT / "output_tests",
                stop_event,
            )

    return results


def _prompt_for_task() -> str:
    print("Choose which agent to run:")
    for index, task in enumerate(TASKS, start=1):
        label = "Run all agents" if task == "all" else f"{task.title()} mapping"
        print(f"  {index}. {label}")

    while True:
        answer = input("Enter a number or task name: ").strip().lower()
        if answer.isdigit() and 1 <= int(answer) <= len(TASKS):
            return TASKS[int(answer) - 1]
        if answer in TASKS:
            return answer
        print(f"Choose a number from 1 to {len(TASKS)}, or one of: {', '.join(TASKS)}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select and run PowerCenter parsing, assessment, conversion, or test generation."
    )
    parser.add_argument(
        "--task",
        choices=TASKS,
        help="Agent to run (parse, assess, convert, test, or all). Prompts if omitted.",
    )
    parser.add_argument(
        "--input",
        help=f"PowerCenter XML file or directory (default: {DEFAULT_XML_PATH}).",
    )
    args = parser.parse_args()

    task = args.task or _prompt_for_task()
    input_path = args.input
    if input_path is None:
        entered_path = input(
            f"XML file or folder [{DEFAULT_XML_PATH}]: "
        ).strip()
        input_path = entered_path or str(DEFAULT_XML_PATH)

    results = run_agents(task, input_path)
    print("\n=== Orchestration complete ===")
    for agent_name, output_paths in results.items():
        print(f"{agent_name.title()} outputs:")
        for output_path in output_paths:
            print(f"  {output_path}")


if __name__ == "__main__":
    main()
