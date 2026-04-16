from pathlib import Path

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


# Prompting an LLM agent
class AgentMapTaskParams(TaskParams):
    agent: str
    prompts: list[str]
    prompts_prefix: str | None = None
    output_filename: str = "output.md"
    write_response_to_output: bool = True


class AgentMapTaskOutput(TaskOutput):
    # content and file_paths are inherited from TaskOutput as lists
    pass


class AgentMapTask(BaseTask[AgentMapTaskParams, AgentMapTaskOutput]):
    params_model = AgentMapTaskParams
    output_model = AgentMapTaskOutput

    async def run(
        self,
        context: JobContext,
        agent_registry: AgentRegistry,
        params: dict,
    ) -> AgentMapTaskOutput:
        args = self.params_model.model_validate(params)

        # Initialize agent by querying agent registry
        agent = agent_registry.create_agent(args.agent, working_directory=context.root)
        if not agent:
            raise Exception(f"Cannot find the requested agent {args.agent}")

        # Resolve the list of files to read (context for the agent)
        unique_files = self.resolve_input_file_paths(context=context, input_file_paths=args.files_to_read)

        # Add the files to the clipboard of the agent once
        for file_path in unique_files:
            await agent.add_file(file_path)

        # Iterate through the list of prompts sequentially
        all_responses: list[str] = []
        for prompt in args.prompts:
            # Trigger the agent for each prompt
            prompt_string = ""
            if args.prompts_prefix:
                prompt_string = f"{args.prompts_prefix} \n\n {prompt}"
            else:
                prompt_string = prompt
            response_text = await agent.step(prompt_string, context.root)

            all_responses.append(str(response_text))

        # Handle file writing logic
        if args.write_response_to_file:
            # write_content_to_files handles a list of content and returns a list of Paths
            output_paths: list[Path] = await self.write_content_to_files(
                content=all_responses,
                context=context,
                output_filename=args.output_filename,
                output_filename_prefix=args.output_filename_prefix,
                write_response_to_output=args.write_response_to_output,
            )

            # Returns the list of response strings and the list of output file Paths
            return self.output_model(content=all_responses, file_paths=output_paths)
        # If no files are written, file_paths defaults to an empty list or None
        return self.output_model(content=all_responses, file_paths=[])
