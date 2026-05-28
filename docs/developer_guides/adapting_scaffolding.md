# Adapting the Scaffolding

This guide walks developers through adapting the scaffolding to serve a different use case. Rather than starting from scratch, you build on top of the existing monorepo structure with its runtime architecture, authentication, agent framework, and workflow framework. The scaffolding ships as a personal productivity system out of the box. This guide shows how to extend that foundation so it serves your target use case instead.

## Prerequisites

Before reading further, read [architecture.md](./architecture.md) for the system overview, runtime processes, and package layout. It links to all the detailed architecture docs for each subsystem.

Also browse [developer_guides_index.md](./developer_guides_index.md) to see the available step-by-step guides. When this guide references a specific developer guide, read that guide in full before making changes.

## Decision Process

### Phase 1: What application do you want to build?

Start by describing the application you have in mind at a high level. What does the user do with it? What are the key agentic workflows? What kind of information does it surface?

Examples:
- A research assistant that monitors arxiv for new papers, summarises them, and keeps a reading log
- A second brain that captures web pages and notes, then lets the user query across them
- A code review companion that watches repositories, drafts reviews, and tracks feedback

From the application description, you can identify which parts of the scaffolding to reuse and which to replace.

### Phase 2: Minimal backend changes

With your application in mind, identify the smallest backend changes needed to serve it. Work through each extension point:

| If your application needs to ... | Read this guide |
|---|---|
| Run multi-step processes as workflows | [create_workflow.md](./developer_guides/create_workflow.md) |
| Build a custom workflow step type | [create_workflow_step.md](./developer_guides/create_workflow_step.md) |
| Give the agent a distinct persona or behavior | [creating_agent_manifests.md](./developer_guides/creating_agent_manifests.md) |
| Add a new capability the agent can call | [creating_agent_tools.md](./developer_guides/creating_agent_tools.md) |
| Store and manage new structured data | [adding_new_entity_to_backend.md](./developer_guides/adding_new_entity_to_backend.md) |

Most applications need only one or two of these. Choose the minimal set that makes the application work.

**Extending the productivity subsystem before adding new entities.**

The productivity subsystem provides Task, Project, and JournalEntry entities. See [productivity_subsystem.md](../productivity_subsystem.md) for the full design. Before adding a new entity, check whether it belongs in this subsystem. JournalEntry is a generic note with markdown content. It supports multiple entry types (daily, weekly, monthly, yearly, project, general). If your application needs notes, sources, synthesis entries, or any other text-based content that a user would write and reference, consider extending the existing JournalEntry entity by adding new entry types instead of creating a separate entity.

For example, a personal knowledge base system might add:

- `source` — a captured web page, article, or video transcript
- `synthesis` — a user's written synthesis connecting multiple sources
- `literature_note` — a note capturing a key insight from a source

These are all journal entry types. Adding them to JournalEntry means you reuse the existing storage, API routes, and agent tools. You only need to:

1. Add new values to the `JournalType` enum in `genesis_core/productivity/models.py`
2. Update the normalization logic in `genesis_tools/productivity_tools.py` if the new type needs special reference date handling
3. Update the agent manifest to handle the new entry types with type-specific instructions
4. Add frontend pages to display and manage the new journal types

Only create a new entity when your data requires structured fields that JournalEntry cannot capture, or when the entity has fundamentally different access patterns. For example, a `Source` entity that tracks URLs, fetching status, and extracted content would justify a separate model because JournalEntry does not support those fields.

### Phase 3: Minimal frontend and UX changes

Once the backend logic is in place, adjust the frontend to present it in a coherent interface. This is often the most impactful part of an adaptation.

- **New pages** — if your application introduces new entities, follow [adding_frontend_entity.md](./developer_guides/adding_frontend_entity.md) to add pages, server actions, and components
- **Navigation** — add new pages to the sidebar in `app/dashboard/layout.tsx` and remove or group productivity pages you do not need
- **Homepage** — replace the productivity dashboard at `app/dashboard/page.tsx` with information and quick access relevant to your application
- **Workflow access** — if your application centres around specific workflows, consider surfacing them directly from the homepage or a dedicated entry point instead of the generic workflow list
- **Quick actions** — expose frequent operations through the quick action menu

## Examples

### Example 1: Personal Knowledge Base

**Application goal**: A second brain that captures web pages and video content, stores them as sources, and lets the user query across all ingested material with the help of an agent.

**Phase 2 changes**:
- Add a new **tool** to fetch and download video content. See [creating_agent_tools.md](./developer_guides/creating_agent_tools.md)
- Extend the productivity subsystem by adding `source` and `synthesis` entry types to the `JournalType` enum in `genesis_core/productivity/models.py`. See [productivity_subsystem.md](../productivity_subsystem.md) for the extension model. These journal entries store the captured content and user-written syntheses respectively
- Build **workflows** for ingesting sources and processing their content. See [create_workflow.md](./developer_guides/create_workflow.md)
- Write a new **agent manifest** that uses the new tools and existing memory tools, with instructions to write and update synthesis notes. See [creating_agent_manifests.md](./developer_guides/creating_agent_manifests.md)

**Phase 3 changes**:
- Add pages and navigation to browse source and synthesis journal entries by type. See [adding_frontend_entity.md](./developer_guides/adding_frontend_entity.md) (the existing journal UI can be reused with type filtering)
- Add a workflow launcher to the homepage for quick ingestion
- Surface synthesis notes and recent sources on the homepage

---

### Example 2: Model Weights Monitor

**Application goal**: Track machine learning models across Hugging Face and other repositories, get notified of updates, and archive model weights on demand.

**Phase 2 changes**:
- Add a **Model entity** to store tracked models and their metadata. See [adding_new_entity_to_backend.md](./developer_guides/adding_new_entity_to_backend.md)
- Add a **tool** for searching and reading model information from Hugging Face. See [creating_agent_tools.md](./developer_guides/creating_agent_tools.md)
- Build **workflows** to poll tracked repositories, gather updates, and download model files. See [create_workflow.md](./developer_guides/create_workflow.md)
- Write a new **agent manifest** with access to the model search tool, configured to be a co-pilot for browsing and selecting models. See [creating_agent_manifests.md](./developer_guides/creating_agent_manifests.md)

**Phase 3 changes**:
- Add pages and navigation for the Model entity
- Replace the homepage with a dashboard showing tracked models, recent updates, and download status
- Add a quick action to trigger a model search workflow

---

### Example 3: Family Recipe Planner

**Application goal**: Ingest recipes from online sources, plan weekly meals, manage a family recipe collection, and get suggestions from an agent.

**Phase 2 changes**:
- Add **Recipe and MealPlan entities** to store recipes and weekly plans. See [adding_new_entity_to_backend.md](./developer_guides/adding_new_entity_to_backend.md)
- Add a **tool** to fetch and parse recipe pages from the web. See [creating_agent_tools.md](./developer_guides/creating_agent_tools.md)
- Build a **workflow** to ingest a recipe URL, extract ingredients and instructions, and store the result. See [create_workflow.md](./developer_guides/create_workflow.md)
- Write a new **agent manifest** with instructions to suggest meals, plan shopping lists, and adapt recipes based on dietary needs. See [creating_agent_manifests.md](./developer_guides/creating_agent_manifests.md)

**Phase 3 changes**:
- Add pages and navigation for recipes and meal plans
- Build a homepage around the weekly meal plan instead of productivity tasks
- Expose recipe ingestion and meal planning as quick actions