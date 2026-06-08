---
name: "review_and_planning"
description: "Conduct planning or review sessions at weekly, monthly, or yearly horizons. Trigger when user asks to plan for, review, or wrap up a week, month, or year."
version: "1.0"
---

## Review & Planning Sessions

### Pre-step — Identify Intention and Time Frame

Determine whether the user is asking for a **planning** session or a **review** session, and identify the time frame.

**Common triggers:**

- "Plan for this week/month/year" or "let's plan [time frame]" → planning
- "Review last week/month" or "let's review [time frame]" → review
- "Wrap up this week/month" → review

**Time frame reference:**

- "This week" → current week (Mon–Sun)
- "Last week" → previous week
- "This month" → current month (in progress)
- "Last month" → previous month (closed)
- "Next month" → upcoming month
- "This year" → current year (in progress)
- "New year" → upcoming year

**Horizon handling rule:**

- **Planning:** requires the higher-horizon plan to exist. If it doesn't, redirect the user to plan that horizon first.
- **Review:** skip any missing journal entries. Reviews are based on what actually happened, not what was planned.

---

## Part A — Planning Sessions

### A1 — Plan for This Week

**Step 1 — Gather context:**

- Monthly journal for this month (to understand the month's goals)
- Yearly journal for this year (for the bigger picture)
- Active projects relevant to this month's goals
- Existing tasks already assigned to this week

**Step 2 — Identify weekly goals:** Based on the monthly goals, what should this week accomplish? Ask the user to confirm or adjust.

**Step 3 — Select project(s) to focus on:** Which project(s) from the monthly plan should be active this week? This is a subset of the monthly projects — do not create new projects at this horizon.

**Step 4 — Assign tasks to days:** Pick specific tasks from those projects and assign them to Mon–Sun, building the weekly timetable.

**Step 5 — Present the plan:** Show the weekly goals, selected projects, and the timetable. Iterate with the user until they are satisfied and explicitly approve.

**Step 6 — Save to weekly journal:** Once approved, create or update the weekly journal with the goals, projects in focus, and the timetable.

---

### A2 — Plan for This Month

**Step 1 — Gather context:**

- Yearly journal for this year (to understand the year's goals)
- Monthly journal for this month (if it already exists — for mid-month catch-up)
- Active projects that relate to this month's focus areas

**Step 2 — Identify monthly goals:** Break the yearly goals down into what this month should achieve. Some yearly goals may not be relevant this month — that's fine.

**Step 3 — Identify or create projects for the month:** Which existing projects are active this month? Are there new projects that need to be created to move toward this month's goals? This is the only horizon where new projects are identified and created.

**Step 4 — Present the plan:** Monthly goals + active projects. Iterate with the user until they are satisfied and explicitly approve.

**Step 5 — Save to monthly journal:** Once approved, create or update the monthly journal with the goals and active projects.

---

### A3 — Plan for Next Month

**Step 1 — Gather context:**

- Yearly journal for this year (to understand the year's goals)
- Monthly journal for this month (to understand what carries forward into next month)

**Step 2 — Identify monthly goals for next month:** Break the yearly goals down into next month's outcomes. Identify carryover from this month if relevant.

**Step 3 — Identify or create projects for next month:** Which projects continue into next month? Are there new projects to start?

**Step 4 — Present the plan:** Monthly goals + active projects. Iterate with the user until they are satisfied and explicitly approve.

**Step 5 — Save to next month's journal:** Once approved, create the next month's journal entry with the goals and active projects.

---

### A4 — Plan for New Year

**Step 1 — Gather context:**

- Yearly journal for the current year (if it exists — to understand trajectory, what carried forward, what the user wants to build on or change)
- Any ongoing projects that might span into the new year

**Step 2 — Identify life areas and yearly goals:** Ask the user about different areas of life — career, finances, health, personal projects, relationships, etc. — and set high-level goals for each area for the new year.

**Step 3 — Identify projects to support those goals:** Which projects would help achieve each yearly goal? Existing projects that continue, or new ones to create.

**Step 4 — Present the plan:** Goals by life area + supporting projects. Iterate with the user until they are satisfied and explicitly approve.

**Step 5 — Save to new year's journal:** Once approved, create the yearly journal entry for the new year with goals and active projects.

---

## Part B — Review Sessions

### B1 — Review Last Week

**Step 1 — Gather context:**

- Daily journals for each day of last week
- Weekly journal for last week (if it exists)
- Monthly journal for this month (to understand what the monthly goals were, so progress can be measured against them)
- Tasks completed in last week

**Step 2 — Determine what was achieved:** Compare what was done against the monthly goals. Present to the user and confirm accuracy. If anything is missing, ask the user to share and add it to the relevant journal.

**Step 3 — Reflection interview:** Ask three questions, one at a time:

- What momentum did you build this week?
- What derailed you from the plan?
- What would you do differently next week?

After three questions, ask: "Is there anything else on your mind? Feel free to write it down here in free form."

**Step 4 — Write the reflection:** Write into the weekly journal entry for last week. Format each question-answer pair as a standalone paragraph using the user's exact words. Follow with an "Other reflection" paragraph for free-form input.

**Step 5 — Update monthly journal:** Capture what was achieved last week against the monthly goals. This is a progress note, not a close.

---

### B2 — Review This Week (Mid-Week Progress Check)

**Step 1 — Gather context:**

- Daily journals for this week so far
- Weekly journal for this week (if it exists)
- Monthly journal for this month
- Tasks completed this week so far

**Step 2 — Determine what has been done:** Compare progress against the weekly plan. Present to the user and confirm accuracy. If anything is missing, ask the user to share and add it to the relevant journal.

**Step 3 — Reflection interview:** Ask three questions, one at a time:

- What momentum did you build this week?
- What derailed you from the plan?
- What would you do differently next week?

After three questions, ask: "Is there anything else on your mind? Feel free to write it down here in free form."

**Step 4 — Write the reflection:** Write into the weekly journal entry for this week. Format each question-answer pair as a standalone paragraph using the user's exact words. Follow with an "Other reflection" paragraph for free-form input.

**Step 5 — Update monthly journal:** Capture progress so far against monthly goals. This is a mid-week progress note. Do not close the period.

---

### B3 — Review Last Month

**Step 1 — Gather context:**

- Monthly journal for last month (if it exists)
- Weekly journals for all weeks in last month
- Tasks completed in last month
- Yearly journal for this year (to see the yearly goals last month was working toward)

**Step 2 — Determine what was achieved:** Compare last month's output against the monthly goals and yearly goals. Present to the user and confirm accuracy. If anything is missing, ask the user to share and add it to the relevant journal.

**Step 3 — Reflection interview:** Ask three questions, one at a time:

- What was the theme or pattern of this month?
- What decision are you still unsure about?
- What carried forward into next month?

After three questions, ask: "Is there anything else on your mind? Feel free to write it down here in free form."

**Step 4 — Write the reflection:** Write into the monthly journal entry for last month. Format each question-answer pair as a standalone paragraph using the user's exact words. Follow with an "Other reflection" paragraph for free-form input.

**Step 5 — Update yearly journal:** Capture what was achieved last month against the yearly goals. This finalises the closed period.

---

### B4 — Review This Month (Mid-Month Progress Check)

**Step 1 — Gather context:**

- Monthly journal for this month (if it exists)
- Weekly journals for weeks that have passed
- Tasks completed this month so far
- Yearly journal for this year

**Step 2 — Determine what has been done:** Compare progress against the monthly goals. Present to the user and confirm accuracy. If anything is missing, ask the user to share and add it to the relevant journal.

**Step 3 — Reflection interview:** Ask three questions, one at a time:

- What was the theme or pattern of this month so far?
- What decision are you still unsure about?
- What carried forward into next month?

After three questions, ask: "Is there anything else on your mind? Feel free to write it down here in free form."

**Step 4 — Write the reflection:** Write into the monthly journal entry for this month. Format each question-answer pair as a standalone paragraph using the user's exact words. Follow with an "Other reflection" paragraph for free-form input.

**Step 5 — Update yearly journal:** Capture progress so far against yearly goals. This is a mid-month progress note. Do not close the period.

---

### B5 — Review Last Year

**Step 1 — Gather context:**

- Yearly journal for last year (if it exists)
- Monthly journals for all months in last year
- Any other relevant records

**Step 2 — Determine what was achieved:** Compare last year's output against the yearly goals. Present to the user and confirm accuracy. If anything is missing, ask the user to share and add it to the relevant journal.

**Step 3 — Reflection interview:** Ask three questions, one at a time:

- What was the defining story of this year?
- What assumption did you carry that turned out to be wrong?
- What are you most proud of?

After three questions, ask: "Is there anything else on your mind? Feel free to write it down here in free form."

**Step 4 — Write the reflection:** Write into the yearly journal entry for last year. Format each question-answer pair as a standalone paragraph using the user's exact words. Follow with an "Other reflection" paragraph for free-form input.

**Step 5 — No parent-level journal to update.** This is the top level.

---

### B6 — Review This Year (Mid-Year Progress Check)

**Step 1 — Gather context:**

- Yearly journal for this year (if it exists)
- Monthly journals for months that have passed
- Any other relevant records

**Step 2 — Determine what has been done:** Compare progress against the yearly goals. Present to the user and confirm accuracy. If anything is missing, ask the user to share and add it to the relevant journal.

**Step 3 — Reflection interview:** Ask three questions, one at a time:

- What was the defining story of this year so far?
- What assumption did you carry that turned out to be wrong?
- What are you most proud of?

After three questions, ask: "Is there anything else on your mind? Feel free to write it down here in free form."

**Step 4 — Write the reflection:** Write into the yearly journal entry for this year. Format each question-answer pair as a standalone paragraph using the user's exact words. Follow with an "Other reflection" paragraph for free-form input.

**Step 5 — No parent-level journal to update.** This is the top level. This is a mid-year progress note. Do not close the period.

---

## Completion

After a planning session, save the plan to the relevant journal and notify the user.

After a review session, finalise the journal and notify the user.
