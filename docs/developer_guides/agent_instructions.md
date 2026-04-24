# Additional Instructions for AI Coding Agent

If you are an AI coding agent tasked with working with this repository, please follow the following instructions during your work session.

## General Working Protocol

A work session might serve one or more of the following **purposes**: 

- Adding new features to the system
- Fixing bugs
- Adding or modifying the existing tests, makefile, dockerfiles, docker compose, CI/CD, and other engineering support tool of the project
- Updating the documentation of the project
- Brainstorming ways to design or refactor the codebase to support a large new feature or architecture change
- Adapting the entire scaffolding for a different use case


A work session might start with one of the following **input types** from the developer: 

- An ad-hoc request describing one particular feature request, maintenance request, information request, or a bug report
- A set of requests provided within a chat message
- A document or a set of documents, which describe a set of requests


If a work session has multiple requests, create a task list of track these requests. Then, follow the general protocol below to handle each request.



General protocol for each request: 

- **Investigate**:Do the necessary investigative activities before starting discussion with developer or proposing any code change
- **Interview the developer**: Based on your understand of the codebase and the information that you need to write up a spec, ask developer questions to get their exact idea about what is needed to implement.
- **Write spec**: Write detailed specification of the code change and present to the developer for feedback. Revise the spec according to developer's feedback until receiving explicit approval. See the section below for a detail of what is expected in a spec.
- **Develop a plan**: Based on the approved spec, write a detailed plan, showing step by step to implement the spec, and present to the developer for feedback. Revise the plan according to developer's feedback until receiving explicit approval. See the section below for a detail of what is expected in a plan.
- **Implement code change**: Follow the approved plan to modify the codebase. 
- **Verify code change**: Perform code quality check before notifying developer for review and feedback.
- **Revise and refine code change**: Fix issues and implement modifications required by the developer, until receiving explicit approval from the developer.
- **Document and move on**: If there are more requests to be done, mark the current request as complete, and repeat the protocol with the next request.



A work session is considered completed when:

- The codebase passes all the quality check (e.g., `make check-all` shows no error)
- All of the requests the developer specified in the input are verified and approved explicitly by the developer


## How to investigate the codebase

Before engaging in discussion with developer or coding activity, you need to do **the following investigative activities**:

- Read the docs. The architecture docs provide short cuts to understand the codebase. The developer guides provide instructions for commonly done tasks with the codebase.
- Investigate the codebase related to the requests thoroughly before starting to respond. Always assume that the docs could be outdated, and therefore verify with the actual code first before starting to plan your implementation approach.


## How to write spec

A spec is a short document that specify precise what to be built or modified.

A spec could contain the following parts:

- Problem statement – One‑sentence description of the goal and why it matters.
- Scope & boundaries – What the code must do, and what it must not do.
- Functional requirements – List of features or behaviours, expressed as “When X happens, the system shall Y” or as user‑story style prompts.
- Non‑functional requirements – Performance, latency, memory limits, security, scalability, compliance, etc.
- Input & output contracts – Exact shapes, types, and validation rules for all data the model receives and produces (e.g., JSON schema, CSV column definitions, tensor dimensions).
- Success criteria / acceptance tests – Concrete criteria that determine whether the implementation is correct (e.g., “accuracy ≥ 95 % on test set”, “no runtime exceptions for inputs in A‑B”).
- Constraints & assumptions – Resource limits, library versions, platform restrictions, external services, or data‑privacy rules the code must respect.
- Examples / edge‑cases – Sample inputs with expected outputs, plus known tricky cases to handle.
- Environment & tooling – Required runtime (Python 3.11, PyTorch 2.3, etc.), build steps, and any scaffolding the AI should use.
- Version & ownership metadata – Title, author, date, and optionally a project ID or issue tracker reference so the spec can be tracked.


## How to write a plan

A plan describes the steps, or work units, to implement a code change, such as one described in a spec. 

Given an approved spec, you need follow the following procedure to create an implementation plan: 

- Identity a sequence or sequences of code changes to implement the spec
- If a code change introduces or modify logic in the core of the system, consider adding automated tests to the plan
- For each identified code change, identify and clearly describe the condition to review the code change so that it satisfies the spec
- Draft the plan

**Scope of work units**: you should aim to keep units of work granular and not-overlapping, so that they can be executed in parallel by subagents whenever possible.


## How to handle version control

Before implementing a spec, create a new branch and switch to it.

Commit to the new branch as you make progress throughout the coding. 

Write your commit message simple and clear. Do not add "co-author by" or anything similarly wasteful.

DO NOT commit when are you in the middle of iterative code fixing or refinement with user, so that you do not commit the solutions that do not work. Only commit when you finally fix the issue. 

When a spec has been finished, merge the branch back to master. Run the test on master branch again, and when everything works properly, you can delete the feature branch.
