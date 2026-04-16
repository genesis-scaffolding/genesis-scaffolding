from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams


### SAMPLE TASK
class SampleTaskParams(TaskParams):
    pass


class SampleTaskOutput(TaskOutput):
    pass


class SampleTask(BaseTask[SampleTaskParams, SampleTaskOutput]):
    params_model = SampleTaskParams
    output_model = SampleTaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> output_model:  # type: ignore
        self.params_model.model_validate(params)
        output = self.output_model(content=[""], file_paths=None)
        return output
