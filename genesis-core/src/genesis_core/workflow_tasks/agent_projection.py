import json
import logging
import re
from pathlib import Path

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams

logger = logging.getLogger(__name__)


class AgentProjectionTaskParams(TaskParams):
    agent: str
    prompt: list[str]
    # Optional: tell the LLM what kind of items to extract (e.g., "Arxiv IDs")
    expected_item_type: str = "strings"
    # Optional: max number of list items.
    max_number: int | None = None
    write_response_to_output: bool = True


class AgentProjectionTask(BaseTask[AgentProjectionTaskParams, TaskOutput]):
    params_model = AgentProjectionTaskParams
    output_model = TaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> TaskOutput:
        args = self.params_model.model_validate(params)

        agent = agent_registry.create_agent(args.agent, working_directory=context.root)
        if not agent:
            raise Exception(f"Cannot find the requested agent {args.agent}")

        # Resolve and add files to agent context
        unique_files = self.resolve_input_file_paths(context=context, input_file_paths=args.files_to_read)
        for file_path in unique_files:
            await agent.add_file(file_path)

        prompt_string = ""
        if args.prompt:
            prompt_string = "\n\n".join(args.prompt)

        # Augment prompt to force JSON list format
        structured_prompt = (
            f"{prompt_string}\n\n"
            f"IMPORTANT: You must return the result as a valid JSON list of {args.expected_item_type}. "
            f'Example format: ["item1", "item2"]. '
            f"Respond ONLY with the JSON list."
        )

        # Get response from LLM
        response_text = await agent.step(structured_prompt, context.root)
        raw_content = str(response_text)

        # Attempt to parse the list
        extracted_list = self._parse_json_list(raw_content)

        if not extracted_list:
            # Simple one-time retry logic if parsing fails
            retry_prompt = 'Your previous response was not a valid JSON list. Please provide the list again in ["item1", "item2"] format.'
            response_text = await agent.step(retry_prompt, context.root)
            extracted_list = self._parse_json_list(str(response_text))

        if args.max_number is not None:
            extracted_list = extracted_list[: args.max_number]
        # Handle file writing (optional, usually for debugging the list)
        output_paths: list[Path] = []
        if args.write_response_to_file and extracted_list:
            output_paths = await self.write_content_to_files(
                content=extracted_list,
                context=context,
                output_filename=args.output_filename or "extracted_list.json",
                output_filename_prefix=args.output_filename_prefix,
                write_response_to_output=args.write_response_to_output,
            )

        return self.output_model(content=extracted_list, file_paths=output_paths)

    def _parse_json_list(self, text: str) -> list[str]:
        """Extracts a list from a string that might contain other text."""
        try:
            # 1. Try a direct JSON load
            data = json.loads(text.strip())
            if isinstance(data, list):
                return [str(item) for item in data]
        except json.JSONDecodeError:
            pass

        # 2. Try to find a list block [...] using regex
        match = re.search(r"\[\s*.*?\s*\]", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return [str(item) for item in data]
            except json.JSONDecodeError:
                logger.warning(f"Found list-like block but failed to parse: {match.group()}")

        # 3. Last ditch: If the SLM returned bullet points instead of JSON
        # This is a fallback for less capable SLMs
        lines = [
            line.strip().lstrip("-*•").strip()
            for line in text.splitlines()
            if line.strip().startswith(("-", "*", "•"))
        ]
        if lines:
            return lines

        return []
