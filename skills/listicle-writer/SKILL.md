---
name: listicle-writer
description: Writes research-driven listicle landing pages where each numbered point is a sales argument built from a unifying theme. Guides through 9 decision gates covering research, theme selection, headlines, feature/benefit mapping, argument building, drafting, review, and imagery. Use when creating listicles, writing conversion-focused numbered lists, or when the user mentions listicles, landing pages, ad landing pages, or numbered list articles.
---

# Listicle Writer

Each listicle point is a sales argument, not just education. A listicle gives you 6-10 chances to make the case for why someone should buy. Every point must serve the theme expressed in the main headline.

The theme is the gravitational center. Every feature, every argument, every point headline gets tested against: "does this serve the theme the headline promised?"

Types of sales arguments:
- **Mechanism** — "It works differently because..."
- **Competitive** — "It does what [competing approach] can't because..."
- **Social proof** — "X customers / X reviews / specific testimonials show..."
- **Evidence** — "Study/test/expert X proved..." (conditional, product-dependent)
- **Risk reversal** — "If it doesn't work, you get..."
- **Credibility** — "Certifications / patents / sourcing / manufacturing / awards..."

## Fast Track

If the user provides pre-completed gate outputs (research brief, theme, headline, etc.), validate what's provided and skip to the next incomplete gate. Don't force the user through gates they've already done.

For example:
- User arrives with a theme already decided. Validate it's specific enough (audience + desire/pain + constraint), then skip to Gate 3.
- User arrives with a research brief already written. Validate it has all four sections, then skip to Gate 2.
- User arrives with headline, arguments, and zone already decided. Validate the lineup has argument variety and theme coherence, then skip to Gate 6.
- User arrives with a full draft for critique. Skip to Gate 7.

When validating, flag any gaps (e.g., "Your research brief has no competitive landscape section, want to add that or proceed without it?") but don't block progress if the user chooses to proceed.

## Gate 0: Inputs

Gather from the user before anything else:

1. **Product** — name, key features, core benefit, key differentiators
2. **Pain point / topic** — the specific problem this listicle addresses
3. **Ad angles** — which ads/themes will drive traffic to this page
4. **Awareness level** — is the audience problem-aware, solution-aware, or product-aware?
5. **Evidence/proof flag** — does this product have citable studies, test results, expert endorsements, or measurable performance data? (Yes/No)
6. **Social proof assets** — review count, star rating, notable testimonials (check project knowledge)
7. **Theme** (optional) — if the user already knows the overarching theme, capture it here. If provided, Gate 2 is skipped.

Do not proceed until all required inputs are confirmed.

## Gate 1: Research

Four research tracks. Tracks run in parallel where possible.

### Track A: Customer Voice (USER-LED)

The user queries their scraped reviews via Claude Code or another tool, filtering for the specific pain point.

What to look for:
- How customers describe the problem in their own words
- How customers describe the results after using the product
- Recurring phrases, specific frustrations or desires mentioned
- Emotional language (frustration, relief, surprise, skepticism)

User returns with pasted review excerpts or a synthesized summary of customer language patterns.

### Track B: Competitive Landscape (CLAUDE-LED)

Claude runs web search and asks the user clarifying questions as needed.

Research questions:
- What products/approaches is this audience currently using for this problem?
- How do those products work (mechanism)?
- Why do they fall short? What's the common complaint?
- What do competitors claim vs. what's actually true?

Output: Summary of top 3-5 competing approaches, how each works, and why each falls short.

### Track C: Pain Point Experience (SPLIT)

Partly from Track A (customer voice), partly from Claude web search.

Claude searches for:
- Online discussions about this problem (Reddit, niche forums, community groups, etc.)
- How people describe living with this problem day to day
- What they experience, notice, or deal with regularly
- What triggers frustration or urgency

Output: The visceral daily experience of the problem in 3-5 bullet points, using real language from online discussions and reviews.

### Track D: Evidence and Proof (CONDITIONAL)

Only activates if the proof flag is Yes from Gate 0. Relevant for products with citable studies, data, test results, expert endorsements, or measurable performance claims.

Claude pulls from:
- Project knowledge docs (research files already in the project)
- Web search for additional evidence if needed

What to find:
- Evidence relevant to THIS specific problem (not all evidence about the product)
- One-line takeaway per source (what was tested or measured, what happened, where it was published or who said it)
- Any evidence that undermines competing approaches

Output: Top 3-5 citable proof points with one-line takeaways.

### Gate 1 Sequence

1. Claude begins Tracks B, C, and D (competitive landscape, pain point experience, evidence/proof) while the user mines customer reviews separately.
2. Claude presents its findings from Tracks B, C, and D as interim notes (not the final brief).
3. User returns with review excerpts or synthesized customer language from Track A.
4. Claude synthesizes ALL tracks (including user-provided reviews) into the research brief below.
5. If user-provided research contradicts or expands Claude's findings, Claude updates the brief accordingly.

### Gate 1 Output: Research Brief

Claude synthesizes all tracks into one structured brief AFTER receiving the user's customer voice research:

```
RESEARCH BRIEF

Customer Voice:
- [Top 5 phrases/descriptions customers use for this problem]
- [Top 3 phrases/descriptions customers use for results]

Competitive Landscape:
- [Competing approach 1]: How it works → Why it falls short
- [Competing approach 2]: How it works → Why it falls short
- [Competing approach 3]: How it works → Why it falls short

Pain Point Experience:
- [3-5 visceral bullet points describing daily life with this problem]

Evidence/Proof (if applicable):
- [Source 1]: [One-line takeaway] ([Publication/Expert, Year])
- [Source 2]: [One-line takeaway] ([Publication/Expert, Year])
- [Source 3]: [One-line takeaway] ([Publication/Expert, Year])
```

Present the research brief to the user for review. User may add, cut, or reframe before proceeding.

Do not proceed to Gate 2 until the research brief is approved.

## Gate 2: Theme

Skip this gate if the user provided a theme in Gate 0.

The theme is the specific lens through which the entire listicle will be read. It combines an audience, a desire or pain, and usually a constraint or context that makes the argument specific.

### Process

1. Based on the research brief, propose 3-4 candidate themes. Each theme should be expressed as a one-line statement that captures: who this is for, what they want or what's hurting them, and what makes their situation specific.

Example candidates for a planking board:
- "Busy dads over 40 who want to look the way they used to but can't commit to the gym" (desire + time constraint)
- "People with chronic back pain who are afraid exercise will make it worse" (pain + fear)
- "Gym-skeptics who want visible results without the gym culture or commute" (identity + avoidance)

2. User picks one or refines it.
3. Confirm the theme before proceeding.

### Theme Quality Check

A good theme is specific enough that it filters what belongs in the listicle and what doesn't. If a feature or argument doesn't serve the theme (or at least serve the persona), it gets cut or deprioritized.

Test: Can you read the theme and immediately know what kind of person would care, what outcome they're after, and why their situation makes the usual solutions inadequate?

Do not proceed to Gate 3 until the theme is approved.

## Gate 3: Zone, Mode and Headline

Load [headline-formulas.md](references/headline-formulas.md) for zone-specific formulas and subheadline patterns.

### Zone Selection

The zone is the emotional register of the theme. Pick the zone that matches how the theme should *feel* to the reader.

| Zone | Feel | Tone | Core Message |
|------|------|------|-------------|
| Zone 1 | Calm trust | Warm, reassuring | "Here's something that works." |
| Zone 2 | Breakthrough | Energetic, forward | "Here's what you gain." |
| Zone 3 | Quiet frustration | Empathetic, tired | "Here's why it hasn't worked." |
| Zone 4 | Urgency/shame | Visceral, dramatic | "This can't wait." |

Present a zone recommendation based on the theme. The theme implies an emotional register. For example, "busy dads who want to look how they used to" leans Zone 2 (breakthrough) or Zone 3 (frustration), not Zone 4 (urgency).

### Mode Selection

- **Direct:** Each point is a sales argument that closes with the product. The product is present throughout.
- **Educational:** Each point teaches an insight, then connects to the product. The insight leads, the product follows.

### Headline

The headline expresses the theme through the chosen zone. It makes the theme concrete and scroll-stopping.

#### Headline Requirements

- **Problem callout** — name the problem the audience actually experiences (from Gate 1 customer voice)
- **Listicle format** — include the number of points
- **Competitive framing** — reference what they're switching from or what isn't working
- **Product reference** — optional but encouraged (can be indirect: "this [product category]")
- Must pass the scroll-stop test
- Must NOT read like ad copy
- No hard word limit, but every word must earn its place

#### Subheadline

Bridges the headline to Point 1. Gives the reader a reason to keep scrolling.

### Process

1. Present zone and mode recommendations based on the theme. User confirms.
2. Propose 3-5 headline candidates written through the approved zone.
3. Propose 2-3 subheadline candidates.
4. User selects or refines.

Do not proceed to Gate 4 until zone, mode, headline, and subheadline are all approved.

## Gate 4: Features, Benefits and Sales Arguments

This gate maps product features and benefits to the theme, then builds sales arguments from the ones that serve it.

### Step 1: Feature/Benefit-to-Theme Mapping

Go through the product's features (what it has) and benefits (what the user gets) from Gate 0 and Gate 1 research. For each, articulate why it matters for this specific theme and persona.

Categorize each as:

- **Core** — directly serves the theme. These become listicle points.
- **Adjacent** — relevant to the persona but not central to the theme. These get sprinkled into body copy, FAQ, or the product introduction. Not headlines.

Example with theme "Busy dads over 40 who want to look how they used to but can't commit to the gym":

**Core:**
- 3-minute sessions → "When you're 40 with kids, an hour at the gym isn't happening. 3 minutes fits between breakfast and the school run."
- Full core activation → "Targets the muscles that actually pull your stomach flat, the ones sit-ups miss."
- No setup required → "Unfolds in 10 seconds. No driving to a gym, no changing, no waiting for equipment."

**Adjacent (persona-relevant):**
- Reduces back pain → "Back pain is common for men over 40. Planking strengthens the muscles that support the spine. Not the headline theme, but a real benefit for this person."
- Portable → "Can use it anywhere. Nice add-on but not core to the 'look how you used to' theme."

### Step 2: Build Sales Arguments from Core Features/Benefits

For each core feature/benefit, build a sales argument. Categorize by type:

- **Mechanism** — "It works differently because..."
- **Competitive** — "It does what [competing approach] can't because..."
- **Social proof** — "X owners switched / X-star reviews / specific quote"
- **Evidence** — "Study/test/expert X proved..." (only if Gate 0 flag = Yes)
- **Risk reversal** — "If it doesn't work, you get..."
- **Credibility** — certifications, patents, sourcing, manufacturing, awards

#### Competitive Arguments Are Feature-Specific

When building a competitive argument, the competing solution must be one that is worse at the SPECIFIC feature or benefit being highlighted. The competitor changes per argument.

Examples:
- Arguing "3 minutes" → compare against the gym (an hour plus commute, at least twice a week)
- Arguing "painless exercise" → compare against crunches/sit-ups (which worsen back pain) or against floor planking (which wrecks your wrists and you'll quit)
- Arguing "better padding" → compare against other planking boards (inferior padding) or against planking on the floor (uncomfortable, painful, unsustainable)

Do not use a generic competitor for all points. Each competitive argument should name the specific alternative that loses at that specific feature/benefit.

#### Awareness Calibration

Consider the audience awareness level from Gate 0:

- **Problem-aware** — Include 2-3 problem validation arguments early, then competitive + mechanism arguments
- **Solution-aware** — Include 1 problem validation argument max, then heavy competitive comparison + product differentiation
- **Product-aware** — Skip problem validation, lead with proof + social proof + risk reversal

### Process

1. Present the feature/benefit mapping (core vs. adjacent) for approval
2. Generate 10-15 candidate sales arguments from core features/benefits, with type labels
3. Present all to user, with a recommended selection and order based on awareness level
4. User selects 6-10 for the listicle and approves the order
5. Unselected arguments and adjacent benefits may inform post-listicle sections (FAQ, Product Intro, body copy) but do not become point headlines
6. Confirm the argument lineup before proceeding

### Argument Variety Check

The final lineup must include at least:
- 1 competitive argument
- 1 proof argument (evidence or social proof)
- 1 risk reversal or credibility argument

If the lineup is all mechanism arguments, flag it and ask the user to diversify.

Do not proceed to Gate 5 until the argument lineup is approved.

## Gate 5: Point Headlines

Load [point-structure.md](references/point-structure.md) for zone-specific point framing and argument type examples.

Each point headline must:
1. **Name the feature or benefit** it's built from
2. **Connect to the theme** expressed in the main headline
3. **Position against competition** where the argument type is competitive (the specific alternative that loses at this feature)
4. Be tagged with its argument type (from Gate 4)

A reader who skims only the headlines should get the full picture: what the product does, why it serves their specific situation, and why alternatives fall short.

### Process

1. For each point in the approved argument lineup, propose 2-3 headline options
2. Present all with argument type labels
3. User selects one per point

### Validation Checkpoint

Before approving the headline set, run every selected headline through these checks:

1. **Theme alignment** — Does this headline connect back to the theme expressed in the main headline? Would it feel at home under that headline, or does it feel like it wandered in from a different listicle?
2. **Feature/benefit presence** — Does this headline name a specific feature or benefit? (Not a vague claim, but something concrete the product has or the user gets.)
3. **Skim test** — Read all headlines in sequence, top to bottom. Does someone who reads ONLY the headlines, no body copy, get the full picture of why they should buy this product for their specific situation?
4. **Competitive specificity** — For competitive headlines: is the competitor specific to the feature being argued? (Not a generic "other products" but the actual alternative that loses at this thing.)
5. **Adjacent benefit check** — Are any adjacent/persona-relevant benefits surfaced in the headlines? If so, consider moving them to body copy instead. Headlines should be reserved for core theme arguments.

If any headline fails, rework it before approving the set.

Do not proceed to Gate 6 until all point headlines pass the validation checkpoint.

## Gate 6: Full Draft

Load [point-structure.md](references/point-structure.md) and [page-structure.md](references/page-structure.md) for structural rules, post-listicle sections, and formatting rules.

Write the complete listicle using all approved selections.

### Adjacent Benefits

Adjacent benefits flagged in Gate 4 should be sprinkled naturally into:
- Body copy of relevant points (where they add value without distracting from the core argument)
- The product introduction section
- FAQ answers

They should not appear in point headlines or become their own points.

### Output Format

```
[ HERO IMG HERE ]

# [Approved Headline]

[Approved Subheadline]

---

[ IMG HERE ]

**#1: [Point Headline]**

[Body: 2-5 sentences, one sentence per line]

---

[...remaining points...]

---

## [Product Name]

[What is it, what's in it, who makes it. Key differentiators. 50-100 words.]

---

## Frequently Asked Questions

**[Question 1]**
[Answer, 1-3 sentences]

**[Question 2]**
[Answer, 1-3 sentences]

[...3-6 questions total...]

---

## [Action-Oriented CTA Headline]

[ IMG HERE ]

[Price]. [Warranty/guarantee].

✓ [Feature 1]
✓ [Feature 2]
✓ [Feature 3]

**[CTA BUTTON: Action Text]**
```

**Note:** Argument type labels (Mechanism, Competitive, etc.) are for planning only. Do not include them in the final copy.

### Key Draft Rules

- One sentence per line within points
- 30-70 words per point (mechanism and proof points may need the upper range)
- Each point makes ONE distinct argument
- Don't assume the reader knows jargon. If they wouldn't say it to their friend, explain it.
- Comparison tables encouraged for competitive arguments (see page-structure.md for table rules)
- Real testimonial quotes encouraged for social proof arguments
- FAQ questions sourced from Gate 1: customer reviews, forum discussions, common objections
- No em-dashes. Use periods or commas.
- No dense text blocks. If it looks like a paragraph on mobile, add line breaks.

## Gate 7: Review and Critique

Before imagery, run the draft against these checklists:

### Theme Coherence Check

- [ ] Does every point headline connect back to the theme expressed in the main headline?
- [ ] Do the point headlines, read in sequence, tell a story that serves the theme?
- [ ] Are adjacent benefits sprinkled into body copy, not competing with core theme arguments in headlines?
- [ ] Would someone who read only the main headline and point headlines understand what this listicle is about and why they should buy?

### Sales Argument Check

- [ ] Does each point make a distinct sales argument?
- [ ] Is there argument variety (not all mechanism points)?
- [ ] Does at least one point include concrete social proof (real reviews, real numbers)?
- [ ] Does at least one point address risk (guarantee, safety, ease of trying)?
- [ ] Are competitive arguments specific to the feature being argued (not generic "other products")?

### Clarity Check

- [ ] Is every mechanism explained simply enough for someone with zero context?
- [ ] Would the reader's 60-year-old parent understand every sentence?
- [ ] Are there concrete proof points (named studies, specific numbers, real testimonials)?
- [ ] Does the headline name the problem the audience actually experiences?

### Structural Check

- [ ] Zone is consistent throughout
- [ ] Mode is consistent throughout
- [ ] Point count is 6-10
- [ ] Each point is 30-70 words
- [ ] One sentence per line
- [ ] Post-listicle sections present (Product Intro, FAQ, CTA)
- [ ] No em-dashes
- [ ] Scannable in under 90 seconds on mobile

Flag any issues and revise before proceeding to imagery.

## Gate 8: Imagery

Load [imagery.md](references/imagery.md) for the art direction framework, style options, and prompt crafting guide.

Three steps:
1. Set visual direction (style, mood, lighting for the full listicle)
2. Propose image concepts (all slots at once, 2-3 options per slot)
3. Generate Nano Banana Pro prompts after concepts are approved

## Reference Files

Loaded during specific gates for detailed structural guidance:

- [headline-formulas.md](references/headline-formulas.md) — Headline and subheadline formulas by zone
- [point-structure.md](references/point-structure.md) — Point structure by zone, mode, and argument type
- [page-structure.md](references/page-structure.md) — Post-listicle sections, comparison tables, CTA structure, formatting rules
- [imagery.md](references/imagery.md) — Art direction framework and Nano Banana Pro prompt crafting guide
