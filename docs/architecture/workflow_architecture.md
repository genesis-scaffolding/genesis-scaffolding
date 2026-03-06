# Workflow Architecture

## Overview

The Workflow Engine is a system for coordinating step-by-step pipelines involving LLM agents. Each workflow is defined by a set of predefined **inputs**, a sequence of **steps**, and a set of final **outputs**.

### Key Architectural Concepts

* **The Blackboard:** A shared state object maintained throughout execution. It stores all initial inputs and the intermediate outputs of every completed step. This allows subsequent steps to consume data produced earlier in the pipeline.
* **Job Directory:** Every workflow execution is provisioned with an automated workspace. This directory structure isolates input files, intermediate states, and final output artifacts.
* **YAML Manifests:** Workflows are defined in YAML files, removing the need to modify Python code to create new processes.
* **Jinja2 Integration:** Manifests support Jinja2 templating to enable:
* **Conditional Logic:** Executing steps only if specific Jinja2 expressions evaluate to true.
* **Data Routing:** Dynamically injecting blackboard data (inputs or prior step results) into step parameters or agent prompts.



### Framework Capabilities

* **Automatic Discovery:** The engine scans and loads all valid manifests from a designated directory.
* **Dual-Layer Validation:** 
  * **Structural:** Ensures the YAML matches the required Pydantic schema.
  * **Logic (Static):** Verifies that all Jinja2 references (e.g., `{{ steps.task_a.content }}`) are valid based on the output models of the referenced tasks before execution begins.
* **Programmatic Execution:** Validated workflows are exposed via a registry for easy invocation.
* **Observability:** Supports asynchronous callbacks to stream progress to terminals, web sockets, or databases.

---

## How to Write a Workflow

To create a workflow, place a YAML manifest in the `workflows` directory. If it passes static validation, it is automatically registered and made available to the `WorkflowEngine`.

### 1. The Workflow Manifest Schema

```yaml
name: "Sample Multi-Step Agent Workflow"
description: "A simple multi-step workflow to test agent integration."
version: "1.0"

inputs:
  writing_topic:
    type: "string"
    description: "Topic for the agent."
    default: "Python monorepo."
  content_length:
    type: "int"
    description: "Target word count."
    default: 500

steps:
  - id: "agent_outline"
    type: "prompt_agent"
    params:
      prompt: "Create an outline for {{ inputs.writing_topic }}."
      output_filename: "agent_outline.md"

  - id: "agent_drafting"
    type: "prompt_agent"
    params:
      prompt: "Write a draft based on this outline: {{ steps.agent_outline.content }}"
      output_filename: "agent_draft.md"

outputs:
  blog_post:
    description: "The final edited version."
    value: "{{ steps.agent_drafting.content }}"

```

### 2. Understanding the Blackboard

During execution, the engine populates a state object. References in your YAML (e.g., `{{ steps.agent_outline.content }}`) resolve against this structure:

```json
{
  "inputs": {
    "writing_topic": "...",
    "content_length": 500
  },
  "steps": {
    "agent_outline": {
      "content": "...",
      "file_path": "..."
    }
  }
}

```

---

## How to Invoke a Workflow

To run a workflow programmatically, initialize the three core managers and call the engine's `run` method.

```python
async def main():
    # 1. Setup Infrastructure
    wm = WorkspaceManager(settings)
    reg = WorkflowRegistry(settings)
    engine = WorkflowEngine(wm)

    # 2. Retrieve Manifest
    manifest = reg.get_workflow("sample_workflow_multi_agent")

    # 3. Provide Runtime Inputs
    user_data = {"writing_topic": "Python uv guide", "content_length": 1000}

    # 4. Execute with Callbacks
    workflow_output = await engine.run(
        manifest, 
        user_data, 
        callbacks=[streamcallback_simple_print]
    )

```

* **WorkflowRegistry:** Handles discovery, schema validation, and logic checking.
* **WorkflowEngine:** Handles the step-by-step execution, template resolution, and blackboard updates.

---

## Developing New Workflow Steps

Each task type requires three components defined in `myproject_core.workflow_tasks`:

1. **TaskParams:** A Pydantic model defining the task's allowed input parameters.
2. **TaskOutput:** A Pydantic model defining the data the task will write back to the blackboard.
3. **TaskClass:** A subclass of `BaseTask[TParams, TOutput]` implementing the `run()` logic.

```python
class PromptAgentTask(BaseTask[PromptAgentTaskParams, PromptAgentTaskOutput]):
    params_model = PromptAgentTaskParams
    output_model = PromptAgentTaskOutput

    async def run(self, context: JobContext, params: dict) -> PromptAgentTaskOutput:
        # Validate and coerce raw dictionary into typed params
        args = self.params_model.model_validate(params)

        # Execute business logic (e.g., LLM call)
        response_text = await agent.step(args.prompt)

        # Return typed output for the blackboard
        return self.output_model(content=response_text, file_path="...")

```

---

## Technical Implementation Details

The engine maintains reliability through three distinct validation layers:

1. **Manifest Schema Validation:** Uses Pydantic models in `myproject_core.schemas` to verify YAML structure.
2. **Static Logic Validation (`_verify_logic`):** Before execution, the `WorkflowRegistry` generates a "mock blackboard" using the `output_model` of every task. It attempts to render all Jinja2 templates; if a template references a non-existent field, validation fails.
3. **Runtime Validation:** 
  * `WorkflowManifest.validate_runtime_inputs` ensures user-provided data matches the expected types (e.g., coercing strings to `Path` objects).
  * Each task's `params_model` validates its specific input dictionary immediately before the task executes.

All core components—including the engine, tasks, and callbacks—are implemented using Python's `asyncio` to ensure high performance and non-blocking I/O during LLM streaming.
