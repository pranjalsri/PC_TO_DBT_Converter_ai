# PowerCenter to dbt Migration Assistant

A Python application that uses a local Ollama language model to analyze Informatica
PowerCenter XML exports and produce migration artifacts for dbt and Snowflake. It
includes a Streamlit UI for uploading a single XML file or a ZIP archive and running
one or all of the migration tasks.

## Features

- Parse PowerCenter XML mappings and create architecture summaries.
- Assess mapping complexity and migration feasibility.
- Generate a dbt project containing Snowflake SQL models and source definitions.
- Generate mapping-focused ETL test case suggestions.
- Process a single XML file or multiple XML files from a directory or ZIP upload.
- Display agent status and error logs in the UI, with cooperative cancellation.

## Requirements

- Windows, macOS, or Linux with Python 3.10 or newer.
- [Ollama](https://ollama.com/) installed and running.
- The configured model, `qwen2.5-coder:7b`, available in Ollama.
- A dbt profile configured before compiling or running generated dbt projects.

Install the configured Ollama model once:

```powershell
ollama pull qwen2.5-coder:7b
```

## Setup

Run these commands from the project directory. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirement.txt langchain-ollama python-dotenv
```

If PowerShell blocks virtual-environment activation, use the environment's Python
directly instead, for example:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirement.txt langchain-ollama python-dotenv
```

The active virtual environment must be used both to install dependencies and to run
the application.

## Run the web UI

Start Ollama, then run:

```powershell
python -m streamlit run agent_ui.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

In the UI:

1. Upload one `.xml` file or a `.zip` containing one or more XML files.
2. Choose **Run all agents** or select Parse, Assess, Convert, or Generate test cases.
3. Monitor the status and execution log. On failure, expand the log to see the
   traceback.
4. Select **Stop execution** to request cancellation.

ZIP uploads extract only XML files. ZIP paths are checked, and extraction is subject
to limits on the number of archive entries and total XML size. Streamlit may also
enforce its own upload-size limit.

Cancellation is cooperative: an in-progress Ollama request cannot currently be
interrupted. The application waits for that request to return, then stops before the
next mapping or agent and reports the cancelled work.

## Run from the command line

The orchestrator accepts a task and an XML file or directory:

```powershell
python agent_orchestrator.py --task assess --input Input_xml
```

Available tasks are `parse`, `assess`, `convert`, `test`, and `all`. If `--task` is
omitted, the command-line interface prompts for a task and input path. The default
input directory is `Input_xml`.

## Agents and outputs

When running all tasks, they execute sequentially in this order:

| Task | Purpose | Default output |
| --- | --- | --- |
| Parse | Summarizes mapping sources, transformations, and targets | `output_reports/` |
| Assess | Estimates mapping complexity and migration feasibility | `output_complexity/` |
| Convert | Generates a dbt project with SQL models and source YAML | `converted/` |
| Test | Generates suggested migration test cases | `output_tests/` |

Separate outputs are created for each input XML. Nested input folders are reflected
in output names to reduce filename collisions.

Generated dbt projects include a `dbt_project.yml`, a `models/_sources.yml`, SQL
models, and a README. Update the generated project's `legacy_source_schema` variable
and configure the `powercenter_migration` profile in your local dbt `profiles.yml`
before compiling or running it. No database credentials are generated.

## Project layout

```text
agent1_Parser.py       Mapping architecture summary agent
agent_2_assessor.py    Complexity and feasibility assessment agent
agent_3_converter.py   PowerCenter-to-dbt conversion agent
agent4_Test_case.py    Migration test-case generation agent
agent_orchestrator.py  Command-line task selection and sequential orchestration
agent_ui.py            Streamlit upload and execution interface
utils/
  pick_llm.py          Ollama model configuration
  powercenter_xml.py   Shared XML parsing and mapping utilities
  run_control.py       Cooperative cancellation support
Input_xml/             Default input directory
output_reports/         Parse reports
output_complexity/      Assessment reports
converted/              Generated dbt projects
output_tests/            Test-case reports
```

## Important limitations

- This is a multi-agent-style, sequential LLM pipeline, not an autonomous agent
  supervisor. The agents do not decide which other agents to call, share their
  outputs as working state, or automatically review one another's results.
- Generated SQL and test cases are suggestions and require engineering review and
  validation. The test-case agent generates cases; it does not execute them.
- Conversion currently expects each mapping response to contain SQL and refuses to
  overwrite an existing generated project with the same output name.
- The converter redacts some sensitive XML values before sending its mapping context
  to the model. Other agents send their mapping contexts without that redaction.
  Review exports for credentials or other sensitive data before using the agents.
- Successful generation does not guarantee that a dbt project will compile or that
  its SQL preserves all PowerCenter behavior.
