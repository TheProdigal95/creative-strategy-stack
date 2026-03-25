---
name: critique
description: 'Critique copy or creative work against a chosen skill/framework. Use when the user says "critique this," "review this," "score this," "what''s wrong with this," "give me feedback," or "how can I improve this."'
---

# Critique

A meta-skill for evaluating work against any loaded skill or framework.

---

## Before Critiquing

### 1. Load the Relevant Skill

Ask the user which skill or framework they want to use for the critique.

Browse available skills (e.g., in `Skills/Copywriting/` or other skill folders) and present options, or let the user specify directly.

**Example prompt:**
> "Which framework do you want me to critique this against? I can see [list available skills], or you can specify another."

### 2. Read and Internalize the Skill

Once the user picks a skill:
- Read the entire skill file
- Identify all principles, rules, and criteria within it
- These become your critique dimensions

### 3. Gather Context

Ask for any context the skill requires before you can properly evaluate the work:
- What type of work is this?
- Who is the target audience?
- What is the goal or desired outcome?
- Any other context the chosen skill specifies

---

## The Critique Process

### Step 1: Extract Criteria from the Skill

Turn the skill's principles into evaluation criteria. Each major principle = one dimension to score.

For example, if the skill says "Clarity over cleverness," that becomes a scoring dimension for Clarity.

### Step 2: Score Each Dimension (1-10)

For each principle/criterion from the skill:

| Score | Meaning |
|-------|---------|
| 1-3 | Fundamentally broken, violates the principle |
| 4-5 | Needs significant work before use |
| 6-7 | Acceptable, room to improve |
| 8-9 | Strong execution of the principle |
| 10 | Exceptional, textbook example |

**Calibration:**
- 7 = "good enough to ship"
- 5 = "needs work first"
- Below 5 = "rewrite required"
- 10 is rare — 9 is exceptional

### Step 3: Provide Specific Feedback

For each score below 8:
- **What's wrong** — be specific, quote the work
- **Why it matters** — connect to the principle
- **How to fix it** — concrete suggestion or rewrite

---

## Output Format

### Summary

```
SKILL USED: [Name of skill/framework]

OVERALL SCORE: [X]/10

Dimensions (from skill):
- [Principle 1]: [X]/10
- [Principle 2]: [X]/10
- [Principle 3]: [X]/10
...
```

### What's Working

List 2-3 things the work does well according to the skill. Quote specific examples.

### What Needs Work

For each dimension below 8:

**[Principle Name]: [Score]/10**
- **Issue:** What's wrong
- **Example:** "[Quote from the work]"
- **Principle:** What the skill says about this
- **Fix:** How to improve it

### Priority Fixes

Rank the top 3 changes by impact.

### Rewrite (If Requested)

Apply all feedback to produce an improved version.

---

## Key Behaviors

1. **Don't invent criteria** — only score against what's in the loaded skill
2. **Be honest** — the goal is improvement, not validation
3. **Be specific** — vague feedback is useless; quote the work, show the fix
4. **Prioritize** — not all issues are equal; rank by impact
5. **Match depth to scope** — a headline gets a quick critique; a full page gets thorough analysis
