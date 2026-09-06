"""Generate automotive work instructions for the five Assignment 02 tasks."""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASKS: tuple[dict[str, str], ...] = (
    {
        "id": "1",
        "task_description": (
            "Install the battery module in the rear compartment, connect to the "
            "high-voltage harness, and verify torque on fasteners."
        ),
    },
    {
        "id": "2",
        "task_description": (
            "Calibrate the ADAS (Advanced Driver Assistance Systems) radar sensors "
            "on the front bumper using factory alignment targets."
        ),
    },
    {
        "id": "3",
        "task_description": (
            "Apply anti-corrosion sealant to all exposed welds on the door panels "
            "before painting."
        ),
    },
    {
        "id": "4",
        "task_description": (
            "Perform leak test on coolant system after radiator installation. "
            "Record pressure readings and verify against specifications."
        ),
    },
    {
        "id": "5",
        "task_description": (
            "Program the infotainment ECU with the latest software package and "
            "validate connectivity with dashboard display."
        ),
    },
)


SYSTEM_PROMPT = """You are a senior automotive manufacturing supervisor and technical writer.
Create clear, consistent work instructions suitable for trained assembly-line workers,
technicians, and quality inspectors. Treat every instruction as a draft that requires
approval under the manufacturer's safety and engineering processes.

Safety rules:
- Use only information present in the task description.
- Never invent torque values, pressure limits, dimensions, cure times, calibration
  tolerances, part numbers, software versions, or other engineering specifications.
- When a required value is not supplied, write "per the approved engineering
  specification" and make the missing value an explicit pre-work confirmation.
- Do not claim that a hazardous system is safe merely because a procedure was followed.
- Include stop-work guidance when a safety condition, specification, or result is unclear.

Return Markdown using exactly these section headings:
### Safety precautions
### Required tools and equipment
### Work instructions
### Acceptance criteria

Use bullet points for the first two sections, numbered steps for work instructions,
and Markdown checkboxes for acceptance criteria. Keep the language concise and practical."""


@dataclass(frozen=True)
class RuntimeConfig:
    """Non-secret metadata needed while generating the report."""

    provider: str
    provider_label: str
    model: str


class ConfigurationError(ValueError):
    """Raised when required environment configuration is missing or invalid."""


class GenerationError(RuntimeError):
    """Raised when an instruction cannot be generated or validated."""


def _required_environment(names: tuple[str, ...]) -> dict[str, str]:
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigurationError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )
    return values


def create_client() -> tuple[Any, RuntimeConfig]:
    """Create an Azure or OpenAI-compatible client from environment variables."""

    provider = os.getenv("LLM_PROVIDER", "azure").strip().lower()

    try:
        from openai import AzureOpenAI, OpenAI
    except ImportError as exc:
        raise ConfigurationError(
            "The 'openai' package is not installed. Run: pip install -r requirements.txt"
        ) from exc

    if provider == "azure":
        values = _required_environment(
            (
                "AZURE_OPENAI_API_KEY",
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_DEPLOYMENT",
            )
        )
        api_version = os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-07-01-preview"
        ).strip()
        client = AzureOpenAI(
            api_key=values["AZURE_OPENAI_API_KEY"],
            azure_endpoint=values["AZURE_OPENAI_ENDPOINT"],
            api_version=api_version,
        )
        config = RuntimeConfig(
            provider="azure",
            provider_label="Azure OpenAI",
            model=values["AZURE_OPENAI_DEPLOYMENT"],
        )
        return client, config

    if provider == "gateway":
        values = _required_environment(("OPENAI_API_KEY", "OPENAI_BASE_URL"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        if not model:
            raise ConfigurationError("OPENAI_MODEL cannot be empty.")
        auth_mode = os.getenv("OPENAI_AUTH_MODE", "bearer").strip().lower()
        client_options: dict[str, Any] = {}
        if auth_mode == "litellm":
            client_options["default_headers"] = {
                "X-Litellm-Key": f"Bearer {values['OPENAI_API_KEY']}"
            }
        elif auth_mode != "bearer":
            raise ConfigurationError(
                "OPENAI_AUTH_MODE must be either 'bearer' or 'litellm'; "
                f"received {auth_mode!r}."
            )
        client = OpenAI(
            api_key=values["OPENAI_API_KEY"],
            base_url=values["OPENAI_BASE_URL"],
            **client_options,
        )
        config = RuntimeConfig(
            provider="gateway",
            provider_label="OpenAI-compatible gateway",
            model=model,
        )
        return client, config

    raise ConfigurationError(
        "LLM_PROVIDER must be either 'azure' or 'gateway'; "
        f"received {provider!r}."
    )


def build_messages(task: dict[str, str]) -> list[dict[str, str]]:
    """Build the prompt messages for one fixed assignment task."""

    user_prompt = f"""Generate work instructions for this new car model task.

Task ID: {task['id']}
Task description:
<task>
{task['task_description']}
</task>

Ensure every requested section is present. Do not add facts that are not supported by
the task description."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _validate_instruction(task_id: str, content: str) -> str:
    instruction = content.strip()
    if not instruction:
        raise GenerationError(f"Task {task_id} returned an empty response.")

    required_sections = (
        "safety precautions",
        "required tools and equipment",
        "work instructions",
        "acceptance criteria",
    )
    normalized = instruction.lower()
    missing = [section for section in required_sections if section not in normalized]
    if missing:
        raise GenerationError(
            f"Task {task_id} response is missing required section(s): "
            + ", ".join(missing)
        )
    return instruction


def generate_instruction(
    client: Any, config: RuntimeConfig, task: dict[str, str]
) -> str:
    """Call the configured chat-completions API for one task."""

    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=build_messages(task),
            temperature=0,
        )
    except Exception as exc:
        raise GenerationError(
            f"Task {task['id']} API request failed ({type(exc).__name__}). "
            "Check the credential, endpoint, model or deployment, and network access."
        ) from exc

    try:
        content = response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError) as exc:
        raise GenerationError(
            f"Task {task['id']} returned an unexpected response structure."
        ) from exc
    return _validate_instruction(task["id"], content)


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_report(
    config: RuntimeConfig,
    results: list[tuple[dict[str, str], str]],
) -> str:
    """Render all generated task/result pairs as a submission-friendly report."""

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Generated Automotive Work Instructions",
        "",
        "> **Validation notice:** These AI-generated instructions are drafts. A qualified "
        "manufacturing engineer and safety representative must approve them before shop-floor use.",
        "",
        f"- **Provider:** {config.provider_label}",
        f"- **Model or deployment:** `{config.model}`",
        f"- **Generated:** {generated_at}",
        f"- **Tasks processed:** {len(results)}",
        "",
        "## Task summary",
        "",
        "| ID | Task description |",
        "|---:|---|",
    ]

    for task, _ in results:
        lines.append(
            f"| {task['id']} | {_escape_table_cell(task['task_description'])} |"
        )

    for task, instruction in results:
        lines.extend(
            [
                "",
                f"## Task {task['id']}",
                "",
                "**Task description**",
                "",
                task["task_description"],
                "",
                instruction,
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "Generated by `main.py` from the fixed Assignment 02 input list. "
            "No manual `input()` was used.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report_atomic(output_path: Path, report: str) -> None:
    """Replace the report only after a complete report has been prepared."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(report)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    """Generate all five work instructions and save the Markdown report."""

    try:
        client, config = create_client()
        results = [
            (task, generate_instruction(client, config, task)) for task in TASKS
        ]
        output_path = Path(__file__).resolve().with_name(
            "generated_work_instructions.md"
        )
        write_report_atomic(output_path, render_report(config, results))
    except (ConfigurationError, GenerationError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Generated {len(results)} work instructions: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
