"""Streamlit interface for uploading PowerCenter XML files or ZIPs and running agents."""

from __future__ import annotations

import io
import queue
import stat
import tempfile
import threading
import traceback
import zipfile
from pathlib import Path, PurePosixPath
from threading import Event

import streamlit as st

from agent_orchestrator import TASK_ORDER, run_agents
from utils.run_control import RunCancelledError
from utils.powercenter_xml import discover_powercenter_xml_files


MAX_ZIP_ENTRIES = 5_000
MAX_XML_FILE_BYTES = 100 * 1024 * 1024
MAX_TOTAL_XML_BYTES = 1024 * 1024 * 1024
TASK_LABELS = {
    "parse": "Parse",
    "assess": "Assess",
    "convert": "Convert",
    "test": "Generate test cases",
}
STATUS_DISPLAY = {
    "Started": "⏳ Started",
    "Executing": "🔄 Executing",
    "Success": "✅ Success",
    "Failed": "❌ Failed",
    "Cancelled": "⏹️ Cancelled",
    "Stopping": "🛑 Stopping",
}


def _extract_xml_files(zip_data: bytes, destination: Path) -> list[Path]:
    """Extract only XML files from a ZIP while enforcing path and size limits."""
    if not zipfile.is_zipfile(io.BytesIO(zip_data)):
        raise ValueError("The uploaded file is not a valid ZIP archive.")

    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    declared_xml_bytes = 0
    extracted_bytes = 0

    with zipfile.ZipFile(io.BytesIO(zip_data)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise ValueError(
                f"The ZIP contains {len(entries)} entries; the limit is {MAX_ZIP_ENTRIES}."
            )

        for entry in entries:
            if entry.is_dir() or Path(entry.filename.replace("\\", "/")).suffix.lower() != ".xml":
                continue

            archive_path = PurePosixPath(entry.filename.replace("\\", "/"))
            if (
                archive_path.is_absolute()
                or any(part in {"..", ""} for part in archive_path.parts)
                or (archive_path.parts and ":" in archive_path.parts[0])
            ):
                raise ValueError(f"Unsafe XML path in ZIP archive: {entry.filename!r}")

            unix_mode = entry.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise ValueError(f"Symbolic links are not allowed in ZIP archives: {entry.filename!r}")

            if entry.file_size > MAX_XML_FILE_BYTES:
                raise ValueError(
                    f"XML file {entry.filename!r} exceeds the "
                    f"{MAX_XML_FILE_BYTES // (1024 * 1024)} MB per-file limit."
                )
            declared_xml_bytes += entry.file_size
            if declared_xml_bytes > MAX_TOTAL_XML_BYTES:
                raise ValueError(
                    f"XML files in the ZIP exceed the "
                    f"{MAX_TOTAL_XML_BYTES // (1024 * 1024)} MB total extraction limit."
                )

            target = (destination_root / Path(*archive_path.parts)).resolve()
            if not target.is_relative_to(destination_root):
                raise ValueError(f"Unsafe XML path in ZIP archive: {entry.filename!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as output:
                file_bytes = 0
                while chunk := source.read(1024 * 1024):
                    file_bytes += len(chunk)
                    extracted_bytes += len(chunk)
                    if file_bytes > MAX_XML_FILE_BYTES:
                        raise ValueError(
                            f"XML file {entry.filename!r} exceeds the "
                            f"{MAX_XML_FILE_BYTES // (1024 * 1024)} MB per-file limit."
                        )
                    if extracted_bytes > MAX_TOTAL_XML_BYTES:
                        raise ValueError(
                            f"XML files in the ZIP exceed the "
                            f"{MAX_TOTAL_XML_BYTES // (1024 * 1024)} MB total extraction limit."
                        )
                    output.write(chunk)
                if file_bytes != entry.file_size:
                    raise ValueError(
                        f"ZIP entry size mismatch for XML file {entry.filename!r}."
                    )

    return discover_powercenter_xml_files(destination_root)


def _prepare_uploaded_files(
    uploaded_data: bytes,
    uploaded_name: str,
    destination: Path,
) -> list[Path]:
    """Prepare a single XML upload or extract XML files from an uploaded ZIP."""
    extension = Path(uploaded_name).suffix.lower()
    if extension == ".zip":
        return _extract_xml_files(uploaded_data, destination)
    if extension != ".xml":
        raise ValueError("Upload a .xml file or a .zip archive containing XML files.")
    if len(uploaded_data) > MAX_XML_FILE_BYTES:
        raise ValueError(
            f"The uploaded XML exceeds the {MAX_XML_FILE_BYTES // (1024 * 1024)} MB limit."
        )

    destination.mkdir(parents=True, exist_ok=True)
    safe_name = PurePosixPath(uploaded_name.replace("\\", "/")).name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("The uploaded XML file must have a valid filename.")
    xml_file = destination / safe_name
    xml_file.write_bytes(uploaded_data)
    return discover_powercenter_xml_files(xml_file)


def _run_uploaded_file(
    uploaded_data: bytes,
    uploaded_name: str,
    tasks: tuple[str, ...],
    events: queue.Queue[tuple[str, str, str]],
    stop_event: Event,
) -> None:
    """Run each selected agent and send progress and error details to the UI."""
    try:
        with tempfile.TemporaryDirectory(prefix="powercenter_upload_") as temp_dir:
            xml_root = Path(temp_dir) / "xml"
            xml_files = _prepare_uploaded_files(
                uploaded_data,
                uploaded_name,
                xml_root,
            )
            events.put(
                (
                    "info",
                    "Upload ready",
                    f"Found {len(xml_files)} XML file(s): "
                    + ", ".join(path.name for path in xml_files),
                )
            )

            for task_index, task in enumerate(tasks):
                if stop_event.is_set():
                    for pending_task in tasks[task_index:]:
                        events.put((pending_task, "Cancelled", "Cancelled before this agent started."))
                    break

                events.put((task, "Started", "Agent run started."))
                events.put((task, "Executing", f"Processing {len(xml_files)} XML file(s)."))
                try:
                    outputs = run_agents(task, xml_root, stop_event)
                except RunCancelledError:
                    events.put((task, "Cancelled", "Stopped after the current operation completed."))
                    for pending_task in tasks[task_index + 1:]:
                        events.put((pending_task, "Cancelled", "Cancelled before this agent started."))
                    break
                except Exception:
                    events.put((task, "Failed", traceback.format_exc()))
                else:
                    output_summary = "\n".join(str(path) for path in outputs[task])
                    events.put(
                        (
                            task,
                            "Success",
                            f"Completed successfully.\nOutput(s):\n{output_summary}",
                        )
                    )
    except Exception:
        error_log = traceback.format_exc()
        for task in tasks:
            events.put((task, "Failed", error_log))
    finally:
        events.put(("run", "Finished", "Run finished."))


def _render_statuses(
    placeholder: st.delta_generator.DeltaGenerator,
    tasks: tuple[str, ...],
    statuses: dict[str, str],
) -> None:
    with placeholder.container():
        columns = st.columns([1, 2, 3])
        columns[0].markdown("**Agent**")
        columns[1].markdown("**Status**")
        columns[2].markdown("**Progress**")
        for task in tasks:
            columns = st.columns([1, 2, 3])
            columns[0].write(TASK_LABELS[task])
            columns[1].write(STATUS_DISPLAY.get(statuses[task], statuses[task]))
            columns[2].write(statuses.get(f"{task}_message", "Waiting to start"))


@st.fragment(run_every=0.5)
def _render_running_job() -> None:
    tasks = st.session_state["job_tasks"]
    statuses = st.session_state["job_statuses"]
    event_log = st.session_state["job_log"]
    events = st.session_state["job_events"]
    worker = st.session_state["job_thread"]
    stop_event = st.session_state["job_stop_event"]

    while True:
        try:
            event_task, event_status, message = events.get_nowait()
        except queue.Empty:
            break

        if event_task == "run" and event_status == "Finished":
            st.session_state["job_finished"] = True
            event_log.append(message)
        elif event_task == "info":
            event_log.append(f"{event_status}: {message}")
        else:
            statuses[event_task] = event_status
            statuses[f"{event_task}_message"] = (
                "See execution log for details."
                if event_status == "Failed"
                else message.replace("\n", " ")
            )
            event_log.append(f"[{TASK_LABELS[event_task]} — {event_status}]\n{message}")

    if worker.is_alive() and not st.session_state["job_finished"]:
        if stop_event.is_set():
            st.info(
                "Stop requested. The current Ollama response cannot be interrupted; "
                "the agent will stop when that request returns."
            )
            st.button("Stopping…", key="stop_agent_run", disabled=True)
        elif st.button("Stop execution", key="stop_agent_run", type="secondary"):
            stop_event.set()
            for task in tasks:
                if statuses[task] == "Executing":
                    statuses[f"{task}_message"] = "Stop requested; waiting for current operation."
            event_log.append(
                "Stop requested. Waiting for any in-progress Ollama request to return."
            )
            st.info(
                "Stop requested. The current Ollama response cannot be interrupted; "
                "the agent will stop when that request returns."
            )

    _render_statuses(st.empty(), tasks, statuses)
    if event_log:
        st.code("\n\n".join(event_log)[-30_000:], language="text")

    failed = any(statuses[task] == "Failed" for task in tasks)
    cancelled = any(statuses[task] == "Cancelled" for task in tasks)
    if st.session_state["job_finished"]:
        if failed:
            st.error("One or more agents failed. The execution log includes the error details.")
        elif cancelled:
            st.warning("The run was cancelled.")
        else:
            st.success("All selected agents completed successfully.")


def main() -> None:
    st.set_page_config(page_title="PowerCenter Migration Agents", page_icon="🔄", layout="wide")
    st.title("PowerCenter Migration Agents")
    st.write("Upload a PowerCenter XML file or a ZIP containing XML exports, then choose which agents to run.")

    with st.form("agent_run_form"):
        uploaded_file = st.file_uploader(
            "PowerCenter XML file or ZIP archive",
            type=["xml", "zip"],
            help="Upload one .xml file or a .zip archive containing one or more XML files.",
        )
        selected_label = st.selectbox(
            "Choose agents",
            ["Run all agents", *[TASK_LABELS[task] for task in TASK_ORDER]],
        )
        submitted = st.form_submit_button("Run")

    if not submitted:
        st.caption(
            "Agents run in this order when you choose all: Parse, Assess, Convert, then Generate test cases."
        )
    elif uploaded_file is None:
        st.error("Upload a .xml file or .zip archive before starting the agents.")
    elif (
        "job_thread" in st.session_state
        and st.session_state["job_thread"].is_alive()
    ):
        st.warning("An agent run is already in progress.")
    else:
        tasks = (
            TASK_ORDER
            if selected_label == "Run all agents"
            else (next(task for task, label in TASK_LABELS.items() if label == selected_label),)
        )
        events: queue.Queue[tuple[str, str, str]] = queue.Queue()
        stop_event = Event()
        worker = threading.Thread(
            target=_run_uploaded_file,
            args=(uploaded_file.getvalue(), uploaded_file.name, tasks, events, stop_event),
            daemon=True,
        )
        st.session_state["job_tasks"] = tasks
        st.session_state["job_statuses"] = {task: "Started" for task in tasks}
        st.session_state["job_log"] = [
            f"Started run for: {', '.join(TASK_LABELS[task] for task in tasks)}"
        ]
        st.session_state["job_events"] = events
        st.session_state["job_stop_event"] = stop_event
        st.session_state["job_thread"] = worker
        st.session_state["job_finished"] = False
        worker.start()

    if "job_thread" in st.session_state:
        _render_running_job()


if __name__ == "__main__":
    main()
