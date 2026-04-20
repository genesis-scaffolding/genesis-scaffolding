import re
import unicodedata
from pathlib import Path
from typing import Any, cast

import jinja2

from .schemas import JobContext


async def streamcallback_simple_print(text: str):
    """Simple StreamCallback function to display LLM content and reasoning chunks to terminal
    'end=""' prevents newlines between chunks.
    'flush=True' forces the character to appear immediately (ignoring output buffering).
    """
    print(text, end="", flush=True)


def resolve_placeholders(
    dict_with_placeholders: dict[str, Any], dict_with_source_content: dict[str, Any],
) -> dict[str, Any]:
    """Recursively renders Jinja2 strings in the params dictionary."""
    jinja_env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,  # Errors out if a variable is missing
    )

    def render_value(val):
        if isinstance(val, str) and "{{" in val:
            template = jinja_env.from_string(val)
            return template.render(**dict_with_source_content)
        if isinstance(val, dict):
            return {k: render_value(v) for k, v in val.items()}
        if isinstance(val, list):
            return [render_value(i) for i in val]
        return val

    # The following cast is valid because params is a dict, so render_value would always output a dict after recursion
    return cast("dict[str, Any]", render_value(dict_with_placeholders))


def evaluate_condition(condition_str: str, state: dict) -> bool:
    """Evaluates a Jinja expression string against the current state.
    Expects conditions like: "steps.agent_step.status == 'success'"
    or "{{ steps.agent_step.content | length > 100 }}"
    """
    jinja_env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,  # Errors out if a variable is missing
    )
    # Clean the string
    # If the user included {{ }}, we strip them to get the raw expression
    raw_expression = condition_str.strip()
    if raw_expression.startswith("{{") and raw_expression.endswith("}}"):
        raw_expression = raw_expression[2:-2].strip()

    try:
        # 2. Use Jinja's 'compile_expression' for a true boolean result
        expr = jinja_env.compile_expression(raw_expression)
        result = expr(**state)

        # 3. Ensure we return a boolean (handles truthy/falsy values)
        return bool(result)
    except Exception as e:
        print(f"Error evaluating condition '{condition_str}': {e}")
        return False  # Fail safe: skip the step if the condition is broken


def slugify(text: str) -> str:
    """Transforms user input into a filesystem-safe string.
    'My Project!!' -> 'my-project'
    """
    # Normalize unicode (removes accents)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Remove non-word characters and replace spaces/underscores with hyphens
    text = re.sub(r"[^\w\s-]", "", text).lower()
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    # Limit length to keep paths manageable
    return text[:64] or "untitled-job"


def validate_path_safety(job: JobContext, target_path: Path) -> bool:
    """Security check: Ensures a file operation is within the job root.
    Use this before any agent-driven 'write' or 'read' operation.
    """
    try:
        # Resolve to absolute paths to handle '..' tricks
        abs_job_root = job.root.resolve()
        abs_target = target_path.resolve()
        return abs_target.is_relative_to(abs_job_root)
    except (ValueError, OSError):
        return False
