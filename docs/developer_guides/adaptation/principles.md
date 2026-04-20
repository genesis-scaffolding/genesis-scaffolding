# Principles for Adapting the Scaffolding

These principles apply whenever you are building on or modifying the Genesis Scaffolding.

---

## 1. Extend Where It Already Lives

Add code to the existing package that makes the most sense. Create a new package only when you genuinely need isolation — a separate deployment, a distinct team ownership boundary, or a clearly scoped subsystem that stands alone.

**Wrong:** Creating `genesis-inventory/` to hold inventory models, then importing them into `genesis-server/`.

**Right:** Adding inventory models to `genesis-core/src/genesis_core/schemas.py` or a new module there, and adding inventory routers to `genesis-server/src/genesis_server/routers/`.

---

## 2. No Unnecessary Abstraction Layers

If one class or function suffices, do not add an interface, a registry, a factory, or a base class. Add complexity only when the problem demands it.

When in doubt, write the simple version first. Refactor to abstraction only when you have seen the pattern repeat three times.

---

## 3. Trim Don't Hide

If you do not need a subsystem — productivity, workflows, agents, tools — remove it. Do not route around it, comment it out, or leave it as dead code. Deleting is cleaner.

---

## 4. Follow Existing Patterns

Every package has patterns. Read the existing code before adding to it. Match the conventions already established: naming, error handling, how models are structured, how routers are registered.

---

## 5. Ask Before Guessing

If the user asks to "build an app" without specifying capabilities, ask them which capabilities they need. Do not assume they want agents, workflows, or productivity features.

If they say "I want to use this to build X" and it's unclear what X needs, ask. Show them the options. Get confirmation before touching code.

---

## 6. Show the Plan, Then Execute

Before changing the scaffold, summarize: what you're keeping, what you're removing, where new code goes. Get the user's agreement. Then execute the relevant playbook.

---

## 7. Authentication Is Never Optional for Web Apps

The authentication system is **always required** for any web app adaptation. A single-user web app still has one user who must be authenticated and authorized. Removing auth breaks the user isolation architecture, session management, and the overall security model of the base web app.

**Wrong:** Removing auth because "there's only one user."
**Right:** Keep the auth system. The single user still logs in.

This applies only to web app adaptations (the base layer). CLI apps bypass the FastAPI server entirely and have no authentication concern.

---

## Anti-Patterns Summary

| Don't | Instead |
|-------|---------|
| Create a new package for domain logic | Add to the existing appropriate package |
| Create registries or interfaces without need | Write the simple class or function |
| Import a new package into the server | Add code directly to the server's routers/services |
| Assume the user wants agents/workflows | Ask and confirm |
| Keep unused subsystems | Remove them |
