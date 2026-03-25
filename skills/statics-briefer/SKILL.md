---
name: statics-briefer
description: Generates advertising creative briefs for direct-response marketing using three psychological frameworks (TEEP stages, Three Selves theory, Emotional Zones) with voice of customer integration. Use when the user asks for creative briefs, ad briefs, advertising concepts, static ads, or mentions TEEP, Trigger, Exploration, Evaluation, Purchase, self-targeting, Actual self, Ideal self, Ought self, emotional zones, valence, intensity, emotional journey, voice of customer, VoC, angle dumps, or distribution specs.
---

# Generating Creative Briefs for Static Ads

Generates advertising creative briefs that operate on three psychological dimensions simultaneously:

1. **TEEP Stages** (Trigger, Exploration, Evaluation, Purchase) — Where the customer is in their buying journey
2. **The Three Selves** (Actual, Ideal, Ought) — Which psychological self we're speaking to, based on Self-Discrepancy Theory
3. **Emotional Zones** (Valence × Intensity) — The emotional tone/temperature of the ad

**Quality bar**: Every brief must pass the "2-second zero-context clarity test" — if someone scrolling can't understand the complete ad (format + visual + headline) instantly, it fails. Clarity is assessed at the ad level, not just the headline alone.

## Interactive Workflow

This skill uses an **interactive workflow with 4 decision gates**. You approve each layer before the skill moves to the next step.

**The 4 Gates:**
1. **Stage + Emotional Journey** (Strategic framework decisions - where customer is and where we move them)
2. **Format + Elements** (Visual structure decisions - provides context for headlines)
3. **Headlines + Subheadings** (Copy - now 3 substeps: Self-strategy → Style selection → Final headlines)
4. **Designer Guidance** (Phase 1: Image Generation + Phase 2: Final Composition)

After Gate 4, briefs are output with:
- **Brief title + Strategy Notes** (outside copy block)
- **Execution details** (inside copy-able code block)

## Quick Start

**Minimal invocation:**

```
Angles:
- Bacon neck collar fail
- Alpha Fit design
- Zero PFAS/microplastics

Distribution: 1 Trigger, 2 Exploration, 1 Evaluation
```

**With voice of customer data (recommended):**

```
Angles:

Angle 1: Bacon neck collar fail
VoC: "bacon neck," "wavy collars," "shirts die after 3 washes"

Angle 2: Alpha Fit design
VoC: "want to look like I lift," "man boobs," "chest area is unflattering"

Distribution: 1 Trigger, 2 Exploration, 1 Evaluation
```

The skill will guide you through each decision gate.

---

## Core Workflow

### Step 1: Gather Inputs

**Required:**
- **Angle dump** — List of advertising angles/concepts to turn into briefs

**Brand context** (flexible handling):
1. First check Claude Project Knowledge for pre-loaded brand context
2. If not found, ask user to provide:
   - Brand name
   - Product description
   - Target customer
   - Primary pains
   - Primary promise
   - Brand tone

**Optional but recommended:**
- **Voice of Customer (VoC) data per angle** — How customers actually talk about the problem

**VoC format (flexible):**
You can provide VoC in any of these formats:
- Direct quotes from forums/reviews: "I hate my bacon neck collars"
- Key phrases customers use: man boobs, gyno, chest fat (not medical terms)
- Summarized language patterns: "They use casual, blunt language, not technical terms"
- Pain point terminology: What words they actually say vs. what we think they say

**Why VoC matters:** Ads that resonate with customer language perform better. VoC helps us write witty, authentic headlines that meet customers where they are emotionally.

**Other optional inputs:**
- **Distribution specs** — Stage distribution (e.g., "1 Trigger, 2 Exploration, 2 Evaluation, 1 Purchase")
- **Self-variant preferences** — Which selves to test (same self OR different selves per angle)

### Step 2: Load Framework

**Reference files total 2,650 lines.** To avoid context overload, use tiered loading:

**Standard workflow (routine brief generation):**
1. Read `references/creative_brief_system_v8.1_consolidated.md` (1,014 lines) — This is your synthesized execution system
2. Use this as the primary framework for generating briefs
3. Only reference source playbooks if specific questions arise

**Deep analysis mode (when explicitly requested):**

If user requests "gap analysis" or "deep analysis":

1. Read source playbooks selectively:
   - `references/teep-model-course-playbook.md` (642 lines) — TEEP framework source
   - `references/valence_intensity_course_playbook.md` (434 lines) — Emotional zones source
   - `references/self_targeting_system_playbook.md` (560 lines) — Three selves source

2. Compare against consolidated system to identify gaps

**When to use deep analysis:**
- User explicitly asks for gap analysis
- Updating or improving the skill itself
- NOT for routine brief generation

### Step 3: Deduplicate Angles

- Review angle dump for overlapping concepts
- Merge similar angles or flag duplicates
- Ensure each angle is distinct and actionable

---

## THE 4 DECISION GATES

### GATE 1: Stage + Emotional Journey (Strategic Framework)

**What happens:**
- Skill assigns each angle to a TEEP stage (Trigger/Exploration/Evaluation/Purchase)
- For each angle, identifies the **emotional journey**:
  - **Customer's current emotional state** (starting zone) - based on insight/VoC
  - **Target emotional state** (where we need them for purchase)
  - **Ad's emotional positioning** (the bridge between the two)
- Shows complete framework table with emotional journey rationale

**The emotional journey model:**

Instead of just "assigning zones for variety," we identify the psychological transformation the ad creates:
- Where is the customer emotionally when they encounter this problem?
- Where do they need to be to take action?
- How does the ad bridge that gap?

**Example:**
- Customer current state: Zone 3 (frustrated about man boobs, embarrassed)
- Target state: Zone 2 (excited, confident solution exists)
- Ad positioning: Zone 1 (calm confidence - acknowledges problem with customer language, hints at powerful solution)
- Rationale: We meet them at Zone 3 with "Man Boob Destroyer" language, but don't dwell there. The confident tone moves them toward hope/excitement.

**TEEP Stage Jobs:**

**Trigger** — Stop-scroll recognition, "that's us" moment
- Goal: Hook rate, hold rate, engagement (NOT conversions)
- Job: Make them pause and pay attention

**Exploration** — Build curiosity and mechanism understanding
- Goal: Time on page, engagement depth, "learn more" clicks
- Job: Make them want to understand how it works

**Evaluation** — Address objections and build confidence
- Goal: Add-to-cart rate, time in consideration
- Job: Make them feel this is the right choice

**Purchase** — Remove friction and create urgency
- Goal: Conversion rate, checkout completion
- Job: Make them act now

**The 4 Emotional Zones:**

**Zone 1** — The Feel-Good Zone (Positive × Low Intensity)
**Zone 2** — The Hype Zone (Positive × High Intensity)
**Zone 3** — The Subtle Frustration Zone (Negative × Low Intensity)
**Zone 4** — The Fear & Urgency Zone (Negative × High Intensity)

**User decision:** Approve stage + emotional journey assignments or request changes

---

### GATE 2: Format + Elements (Visual Structure)

**What happens:**
- Skill recommends visual format for each angle
- Specifies elements to include in each creative
- If format involves columns/cards, specifies exactly what goes in each

**Important note:** The format you approve here affects headline creative freedom in Gate 3. Formats with strong product imagery allow wittier, more conceptual headlines. Formats that are educational/text-heavy require more explicit headlines.

**Format Options by Stage:**

**Trigger formats:**
- Problem creative (show the pain point visually)
- iPhone picture style (authentic, relatable imagery)
- Pattern interrupt (unexpected visual hooks)
- Identity call-out (speak to who they are)

**Exploration formats:**
- Side-by-side comparison (old way vs. new way)
- Mechanism reveal (how it works visually)
- Educational breakdown (explain the science/process)
- Before/after narrative

**Evaluation formats:**
- Us vs. Them (competitive comparison)
- Social proof grid (testimonials, reviews, ratings)
- Testimonial spotlight (single powerful story)
- Objection crusher (address concerns directly)

**Purchase formats:**
- Offer stack (show everything they get)
- CTA-focused (minimal distraction, pure conversion)
- Urgency creative (limited time/quantity pressure)
- Simplified checkout flow (remove friction visually)

**Element Options:**

**Trust signals:**
- Badges (Free shipping, Money-back guarantee, Secure checkout)
- Press mentions/logos
- Certification marks
- Award badges

**Social proof:**
- Star ratings, review count
- Testimonial quotes
- Customer photos
- User-generated content screenshots

**Visual proof:**
- Before/after images
- Product in use
- Comparison shots
- Data visualization

**Urgency indicators:**
- Timer/countdown
- Stock counter
- Limited-time offer badge

**Information:**
- Price callout
- Guarantee details
- Key specs/features
- Value props

**User decision:** Approve format + elements or request changes

---

### GATE 3: Headlines + Subheadings (Copy)

**This gate has three steps:**

---

#### STEP 3A: Self-Strategy Assessment

**What happens:**
- Skill analyzes each brief based on stage, zone, angle, and format
- Determines which self (or selves) the angle naturally fits
- Recommends testing strategy: 1 self, 2 selves, or all 3 selves

**The philosophy:**
Some angles are pure Actual territory (validation). Some are pure Ideal (aspiration). Some are pure Ought (obligation). Some genuinely benefit from testing 2-3 selves. The goal: **best headlines possible for what we're trying to achieve in that brief.**

**Output format (concise, scannable):**

```
Brief Title
Self Name. "Motivating phrase." What it does psychologically.
All 3 headlines should serve [Self].

Brief Title
Test 2 selves:
- Actual Self. "Motivating phrase." What it does psychologically.
- Ought Self. "Motivating phrase." What it does psychologically.
2 Actual headlines, 1 Ought headline.

Brief Title
Test all 3 selves:
- Actual Self. "Motivating phrase." Validation move.
- Ought Self. "Motivating phrase." Obligation move.
- Ideal Self. "Motivating phrase." Aspiration move.
1 headline per self.
```

**Example:**

```
Equipment Graveyard
Actual Self. "You're not lazy—wrong equipment." Validating past failures.
All 3 headlines should serve Actual.

Lifetime Guarantee
Test 2 selves:
- Actual Self. "You've been burned before." Validates skepticism.
- Ought Self. "Stop replacing every year." Obligation to change wasteful pattern.
2 Actual headlines, 1 Ought headline.

Gold Bar Purchase
Ideal Self. "What if it's me?" Pure aspiration energy.
All 3 headlines should serve Ideal.
```

**User decision:** Approve self-strategy or override (e.g., "Brief 2 should be all Actual")

---

#### STEP 3B: Headline Style Selection

**What happens:**
- For each brief, skill shows relevant VoC data for that angle
- References the approved format from Gate 2 (visual strength affects headline freedom)
- Recommends headline style based on angle/zone/self/VoC/format
- Generates example headlines in 2-3 different styles
- User chooses preferred style direction

**The principle:**

Headlines can be MORE creative/witty when visual context is strong. Headlines should be MORE explicit when format is conceptual/educational.

**Headline style options:**
- **Direct/Clear** — Explicitly states product and benefit
- **Witty/Customer Language** — Uses VoC to show understanding with personality
- **Provocative** — Challenges assumptions or calls out problems directly
- **Educational** — Explains mechanism or value proposition

**Format strength guidelines:**

**If format includes prominent product imagery (hero shot, close-up, unboxing):**
- Headlines can be wittier, more conceptual
- Visual makes the product obvious
- Example: "The Man Boob Destroyer" (with t-shirt photo = clear)

**If format is educational/comparison (charts, diagrams, text-heavy):**
- Headlines should be more explicit
- Visual doesn't show product clearly
- Example: "Most Performance Tees Shed PFAS. Hemp Doesn't." (mentions product category)

**If product is universally recognizable (t-shirts, coffee, shoes):**
- Can rely more on visual, headline can be wittier

**If product is niche (specialized supplements, technical gear):**
- Headline should help clarify what it is

**Output format for each brief:**

```
Brief 1: Man Boob Destroyer
Format from Gate 2: Product hero shot - t-shirt on person, close-up
VoC for this angle: "man boobs," "chest fat," "gyno," "can't wear fitted shirts"

RECOMMENDATION: Since format includes prominent product imagery and t-shirts are universally recognizable, we can use wittier, more conceptual headlines that leverage VoC.

Style Examples:

WITTY/CUSTOMER LANGUAGE:
- "The Man Boob Destroyer"
- "Kill Chest Fat With Any Shirt"

PROVOCATIVE:
- "Your Shirt's Lying About Your Chest"
- "Stop Hiding. Start Fitting."

DIRECT/CLEAR:
- "Hide Man Boobs Instantly. Any Shirt."
- "Chest-Flattening T-Shirt Design"

All work because the visual makes "this is a shirt" obvious. Choose your preferred direction.
```

**User decision:** Choose preferred headline style for each brief

---

#### STEP 3C: Generate Final Headlines + Subheadings

**What happens:**
- Based on approved style from 3B, skill generates final headlines
- Headlines follow the **Clarity + Brevity principle** while matching chosen style
- Uses VoC language patterns from Step 1
- After headlines approved, generates supporting subheadings

**CRITICAL: Ad-Level Clarity Principle**

Clarity is achieved by the combination of **Format + Visual Elements + Headlines**, not headlines alone.

**The 2-second zero-context test applies to the complete ad:**
- Can someone understand what I'm selling from format + visual + headline in 2 seconds?
- NOT just: "Does the headline alone mention the product?"

**This means:**
- Headlines can be wittier when format provides strong product imagery
- Headlines should be more explicit when format is conceptual/abstract
- VoC language improves resonance, but visual context provides clarity

**Examples:**

**Scenario 1: Strong visual context**
- Visual: Photo of fitted t-shirt on person
- Headline: "The Man Boob Destroyer"
- Result: ✅ CLEAR (t-shirt photo makes product obvious, headline can be witty)

**Scenario 2: Same headline, weak visual**
- Visual: Generic gym background
- Headline: "The Man Boob Destroyer"
- Result: ❌ UNCLEAR (Could be workout program, surgery, supplement...)

**Scenario 3: Educational format**
- Visual: Comparison chart or diagram
- Headline: "Most Performance Tees Shed PFAS. Hemp Doesn't."
- Result: ✅ CLEAR (Headline explicitly mentions product category because visual doesn't)

**VoC + Clarity Balance:**

Using customer language is critical for resonance, BUT it must be combined with ad-level clarity:

**VoC without clarity:**
- "Does he lift?" (Their words, but what am I buying?)
- "Man boob problems?" (Calls out issue, no solution mentioned)

**VoC with clarity (ad-level):**
- "Get The 'Does He Lift?' T-Shirt" (VoC + explicit product) ✅
- "The Man Boob Destroyer" + t-shirt photo (VoC + visual clarity) ✅
- "Man Boobs? This Shirt Hides Them" (VoC + product + benefit) ✅

**Headline length:** 3-8 words (shorter is better, but never sacrifice clarity)

**The Three Selves (for reference):**

**ACTUAL SELF** (who they are now)
- Function: Validation of current experience
- Tone: "You're not wrong/broken/alone"

**OUGHT SELF** (who they should be by external standards)
- Function: Social pressure, responsibility, duty
- Tone: Authoritative, imperative

**IDEAL SELF** (who they want to become)
- Function: Aspiration without pressure
- Tone: Possibility, invitation

**Subheading purpose:**
- Support the headline claim
- Add credibility/proof
- Remove friction/objections
- Drive to next action

**User decision:** Approve headlines + subheadings or request revisions

---

### GATE 4: Designer Guidance (Execution Direction)

**What happens:**
- Skill generates **Phase 1: Image Generation** guidance (3 concrete image ideas)
- Skill generates **Phase 2: Final Composition** guidance (layout, color, what to avoid)
- Also generates **Context** (2-3 sentences explaining customer mindset)

**Phase 1: Image Generation**

Purpose: Prompt-ready concepts for AI image generation tools.

What belongs here:
- 3 concrete image ideas
- Each idea includes: what the image depicts + why it works
- Ready to adapt into AI prompts

What does NOT belong:
- Composition/layout guidance (that's Phase 2)
- Color palettes (AI will determine based on concept)

Example:
```
IMAGE IDEAS:

Option A: Pure typography
The key number/offer as bold, dimensional text. No supporting imagery.
Lets the number do all the work. Maximum clarity.

Option B: Motion cues
Motion blur or speed streaks behind the text.
Reinforces urgency without adding clutter.

Option C: Confident business moment
Tight crop on hands signing a document or receiving something.
Implies success, deal closed. Human element without feeling stocky.
```

**Phase 2: Final Composition**

Purpose: Guidance for the human designer assembling the final ad after image generation.

What belongs here:

COMPOSITION:
- Layout hierarchy (what's most prominent, what's secondary)
- Spacing and breathing room
- Visual weight distribution
- Element arrangement

COLOR GUIDANCE:
- Palette direction (soft blues, bold saturated tones, muted warmth, etc.)
- Guides overall ad composition, not the AI-generated image

WHAT TO AVOID:
- Specific pitfalls for this brief
- Common mistakes that would undermine the ad's goal

What does NOT belong:
- "High contrast," "saturated colors," or other AI-output-dependent instructions
- Emotional zone principles (these are strategic, not executional)

**Context Section:**

2-3 sentences explaining:
- The customer's mindset when they see this ad
- What the ad communicates

Critical for brands without physical products—gives designer essential context.

**User decision:** Final approval before output

---

## Step 4: Output Briefs

After all gates are approved, **output all briefs directly in the chat conversation**.

**CRITICAL: Do NOT write briefs to a file. Output them directly in chat so the user can see and copy them immediately.**

**Output Structure:**

**OUTSIDE the copy-able block (for strategists/reviewers):**
```
BRIEF [NUMBER]: [BRIEF TITLE]

STRATEGY NOTES
- ANGLE: [Core concept being tested]
- STAGE: [TEEP stage]
- STAGE GOAL: [What this stage accomplishes]

EMOTIONAL JOURNEY:
- Customer current state: [Zone X - emotional description]
- Target state: [Zone Y - where we need them]
- Ad positioning: [Zone Z - the bridge]
- Journey rationale: [How the ad moves them from current to target]

- SELF TARGET: [Actual/Ideal/Ought]
- SELF RATIONALE: [Why this self fits the angle]
- EMOTIONAL MOVE: [From state → To state]

---
```

**INSIDE the copy-able block (for designer execution):**
````markdown
```
CONTEXT
[2-3 sentences: customer mindset + what ad communicates]


FORMAT
[Visual structure name]

[If format involves columns/cards, specify exactly what goes in each]

Example (side-by-side):
LEFT COLUMN (Problem):
- Element 1
- Element 2

RIGHT COLUMN (Solution):
- Element 1
- Element 2


ELEMENTS
- Element 1
- Element 2
- Element 3
- CTA


FOR DESIGNER: PHASE 1 (Image Generation)

IMAGE IDEAS:

Option A: [Image concept]
[What it depicts + why it works]

Option B: [Image concept]
[What it depicts + why it works]

Option C: [Image concept]
[What it depicts + why it works]


FOR DESIGNER: PHASE 2 (Final Composition)

COMPOSITION:
- [Layout hierarchy]
- [Spacing notes]
- [Visual weight distribution]

COLOR GUIDANCE:
- [Palette direction for overall ad composition]

WHAT TO AVOID:
- [Specific pitfall 1]
- [Specific pitfall 2]
- [Specific pitfall 3]


COPY

HEADLINES:
- [Headline option 1]
- [Headline option 2]
- [Headline option 3]

SUBHEADING:
[Supporting line]

CTA:
[Button text]
```
````

**Critical formatting rules:**
- Each brief's execution details (Context through Copy) in a SINGLE code block with copy button
- Plain text only inside code block, no markdown formatting
- Use blank lines to separate sections, NOT separator lines like "====" or "---"
- Clear section headers in ALL CAPS

**Output location:**
- **Default: Display directly in chat** — User can see and copy each brief immediately
- **Only write to file if user explicitly requests it** — e.g., "save these to a file"

---

## Key Principles

1. **4-gate workflow** — Strategic framework → Visual structure → Copy → Execution

2. **Ad-level clarity over cleverness** — The complete ad (format + visual + headline) must make the offering clear in 2 seconds

3. **Emotional journey precision** — Identify where customer is emotionally, where they need to be, and how the ad bridges that gap

4. **VoC drives resonance** — Customer language makes ads feel authentic and relatable

5. **Format drives headline freedom** — Strong product imagery allows wittier headlines; conceptual formats require explicit headlines

6. **Separate image generation from composition** — Phase 1 is AI prompts, Phase 2 is human designer work

7. **Psychological functions over templates** — Self-variants must serve distinct purposes

8. **Stage jobs are sacred** — Don't ask Trigger ads to convert, don't make Exploration ads address objections

9. **Progressive loading** — Use consolidated system for routine work; reference source playbooks only when needed

---

## Reference Materials

**Primary source (1,014 lines):**
- [Creative Brief System v8.1](references/creative_brief_system_v8.1_consolidated.md) — Your synthesized execution guide with tactical tools. Use this for all routine brief generation.

**Source frameworks (1,636 lines total - load selectively):**
- [TEEP Model Playbook](references/teep-model-course-playbook.md) — 642 lines. Funnel stage framework source.
- [Self-Targeting System Playbook](references/self_targeting_system_playbook.md) — 560 lines. Three selves framework source.
- [Valence & Intensity Playbook](references/valence_intensity_course_playbook.md) — 434 lines. Emotional zones framework source.

**Loading strategy:**
- **Routine brief generation:** Load only v8.1 consolidated system
- **Gap analysis or deep research:** Load source playbooks selectively as needed
- **Total context:** 2,650 lines across all 4 files (use progressive disclosure)

---

## Examples

See [example-briefs.md](examples/example-briefs.md) for complete sample outputs showing:
- Full brief structure for each TEEP stage
- Self-variant execution across all three selves
- Emotional journey rationale
- Format and elements choices
- Gate 3B headline style selection examples
- Phase 1 and Phase 2 separation
- VoC integration in headlines

---

## Troubleshooting

**"Briefs feel generic"**
- Check if you're using templates instead of psychological functions for self-variants
- Verify emotional journey has clear rationale tied to the angle's emotional nature
- Ensure the complete ad (format + visual + headline) makes the offering clear
- Review VoC usage - are we using customer language?

**"Headlines are too vague"**
- Check if format provides enough visual context - if not, headline needs to be more explicit
- Apply ad-level clarity test: format + visual + headline = 2-second clarity?
- Include product name, specific numbers, or clear offer when visual is weak
- Test: "Can someone with zero context understand what I'm selling from the complete ad?"

**"Briefs don't pass 2-second test"**
- Remember: Test applies to the complete ad, not just headline
- Check if format + visual combination provides enough context
- Remove jargon and assumed context
- Make visual cues more concrete
- Simplify context narrative

**"Self-variants sound the same"**
- Review psychological functions: validation (Actual) vs. pressure (Ought) vs. aspiration (Ideal)
- Ensure each variant serves a DIFFERENT psychological purpose
- Don't just rephrase — change the psychological mechanism

**"Headlines aren't using VoC"**
- Review VoC data provided in Step 1 for that angle
- Reference Gate 3B style examples that incorporated VoC
- Balance VoC authenticity with ad-level clarity

**"Emotional journey feels forced"**
- Make sure you're identifying customer's actual current state based on insight/VoC
- Check that target state is realistic for what one ad can achieve
- Verify ad positioning is the authentic bridge, not aspirational thinking

**"Phase 1 and Phase 2 are mixed up"**
- Phase 1 = AI image generation prompts (what the image depicts)
- Phase 2 = Human designer composition work (how to arrange the final ad)
- Don't put composition guidance in Phase 1
- Don't put AI styling instructions in Phase 2
