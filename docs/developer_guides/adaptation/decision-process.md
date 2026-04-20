# Decision Process: Choosing Extensions

When asked to adapt the scaffolding for a new application, follow this process. Do not skip steps or assume which extensions the user needs.

---

## Step 1: Discover the User's Needs

Ask the user what their application needs. Do not assume.

**Ask:**
> "What does your application need to do? Which of these capabilities are relevant?"
>
> - **Web UI** — pages, forms, dashboards, data display
> - **Productivity features** — tasks, projects, journals, calendar
> - **Workflows** — multi-step automated processes, scheduled jobs
> - **AI Agents** — chat interface, tool-use, memory

Give the user a moment to select. If they describe a use case without naming capabilities, help them map their description to the above options.

**Do not proceed to Step 2 until you know which extensions the user wants.**

---

## Step 2: Select the Extensions

Based on the user's selections, determine which extensions to keep.

| Extension | Keep when... |
|----------|--------------|
| **Productivity** | The app needs tasks, projects, journals, or calendar |
| **Workflows & Scheduling** | The app runs automated multi-step processes, scheduled or on-demand |
| **Agents** | The app has a chat interface or needs an AI that acts autonomously |

The **Base Web App** is always kept — it cannot be removed.

---

## Step 3: Show the Plan

Before touching any code, summarize the plan for the user to confirm.

**Template:**
> "Based on what you described, I'll build your app with:
> - **Base:** FastAPI server + NextJS frontend
> - **Extensions:** [list the selected extensions]
>
> I'll add your domain logic in [where it belongs — see the extension playbook].
> I'll remove [extensions not selected].
>
> Does this sound right?"

**Do not touch code until the user confirms.**

---

## Step 4: Execute the Playbook

Follow the playbook for the selected extensions. Each playbook is a checklist.

- [core-web-app.md](core-web-app.md) — Base web app only
- [productivity-app.md](playbooks/productivity-app.md) — Base + Productivity
- [workflow-app.md](playbooks/workflow-app.md) — Base + Workflows & Scheduling
- [full-agent-app.md](playbooks/full-agent-app.md) — Base + all extensions

If the user selected multiple extensions, combine the relevant playbooks. Execute the **keep**, **remove**, and **add** steps from each.

**After executing the playbook:** Review the [configuration guide](../extending-the-server/adding-configuration.md). If the adaptation introduced new capabilities (new extensions, tools, or workflow types), check whether new configuration options are needed. Add them before proceeding to verification.

---

## Step 5: Verify

After completing the adaptation, run the smoke test:

**Backend:**
```bash
cd /path/to/genesis && uv run pyright .
```

**Frontend:**
```bash
cd genesis-frontend && pnpm build
```

Both must pass with no errors. Fix any issues before declaring the adaptation complete.

---

## If the User Changes Mid-Way

If during development the user adds a new requirement, go back to Step 1 and re-confirm. A scope change means a new plan.
