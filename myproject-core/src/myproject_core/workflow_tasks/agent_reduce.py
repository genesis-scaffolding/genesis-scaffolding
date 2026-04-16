import logging
from pathlib import Path

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams

logger = logging.getLogger(__name__)


class AgentReduceTaskParams(TaskParams):
    agent: str
    prompts: list[str]
    # How to join the input prompts
    separator: str = "\n\n---\n\n"
    # An optional final instruction to wrap around the combined text
    reduction_instruction: str = "Please synthesize the above information into a single, cohesive report."
    output_filename: str = "summary_report.md"
    write_response_to_output: bool = True


class AgentReduceTask(BaseTask[AgentReduceTaskParams, TaskOutput]):
    params_model = AgentReduceTaskParams
    output_model = TaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> TaskOutput:
        args = self.params_model.model_validate(params)

        agent = agent_registry.create_agent(args.agent, working_directory=context.root)
        if not agent:
            raise Exception(f"Cannot find the requested agent {args.agent}")

        # 1. Resolve and add files to agent context (Supporting materials)
        unique_files = self.resolve_input_file_paths(context=context, input_file_paths=args.files_to_read)
        for file_path in unique_files:
            await agent.add_file(file_path)

        # 2. Combine the prompts into one single block of text
        combined_prompts = args.separator.join(args.prompts)

        # 3. Formulate the final one-shot prompt
        final_one_shot_prompt = (
            f"I am providing multiple pieces of information below:\n\n"
            f"{combined_prompts}\n\n"
            f"TASK:\n{args.reduction_instruction}"
        )

        # 4. Execute the agent run
        response_text = await agent.step(final_one_shot_prompt, context.root)
        response_str = str(response_text)

        # 5. Handle output (content is a list of 1 string)
        all_responses = [response_str]
        output_paths: list[Path] = []

        if args.write_response_to_file:
            output_paths = await self.write_content_to_files(
                content=all_responses,
                context=context,
                output_filename=args.output_filename,
                output_filename_prefix=args.output_filename_prefix,
                write_response_to_output=args.write_response_to_output,
            )

        return self.output_model(content=all_responses, file_paths=output_paths)
