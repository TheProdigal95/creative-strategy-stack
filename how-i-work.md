# How I Work — Process Overview for the Team

This document walks through the entire system I use to go from "new brand, zero creative" to a full pipeline of static ads, UGC video briefs, listicles, and ongoing test batches. Everything here uses one brand — Peck Purity (GrubTerra) — as the throughline example so you can see the process from start to finish.

---

## The System in One Sentence

**Customer research (reviews + Reddit + competitor reviews + customer calls) becomes structured VoC data, which becomes angle hypotheses ranked by evidence strength, which become creative briefs with strategic frameworks baked in, which become the ads you design.**

Nothing in this pipeline is based on vibes or assumptions. Every angle, headline, image direction, and emotional arc traces back to something a real customer said.

---

## Part 1: The Stack

| Layer | What | Why |
|-------|------|-----|
| **Obsidian vault** | One folder per brand. Date-first file naming. Everything in markdown. | Single source of truth. Every document for every brand lives here. |
| **Research Engine** | Custom 12-step Python pipeline that scrapes Reddit, extracts evidence, discovers themes, scores brand fit, mines language patterns. | Turns 7-25 minutes of compute into 20-40 structured insights + a language report showing how the audience actually talks. |
| **Ad Library scraper** | Batch scrapes Meta Ad Library for competitor creative, downloads media, optional visual analysis. | See what competitors are running before you start. |
| **Review scraping** | Custom scripts that pull reviews from brand sites AND competitor sites into structured data (.jsonl files). | Reviews are the #1 data source. Both the brand's reviews AND competitor reviews. |
| **Custom AI skills** | Statics briefer, listicle writer, native ad creative, editorial image prompts. Each is a structured workflow with gates and frameworks. | Consistent quality at volume. The skills encode the frameworks so every brief follows the same strategic structure. |
| **Claude project memory** | Persistent rules per brand. Compliance guardrails, positioning constraints, feedback from past mistakes. | I don't have to re-explain brand rules every session. The AI remembers "never position Peck Purity against egg withdrawal" or "always spell out diatomaceous earth." |

---

## Part 2: The Research-to-Brief Pipeline

This is the core of everything. Most creative strategists write copy from assumptions. This system grounds everything in evidence.

### Two types of customer language (and why both matter)

| Source | What you get | When you use it |
|--------|-------------|----------------|
| **Reviews** (brand + competitor) | **Result language.** What improved, how much, emotional relief. "My girls' feathers look amazing." "No more liquid droppings." "Wish I'd started sooner." | Evaluation-stage ads. Testimonial-style creative. Headlines that show the outcome. |
| **Reddit / Forums** | **Problem language.** How people describe suffering, the vocabulary of desperation, specific triggers. "My chickens just kept dropping dead." "I've tried everything." "It's like damn mommy groups." | Trigger-stage ads. Problem-awareness creative. Headlines that name what the buyer is going through. |

**Always scrape competitor reviews too.** Build a cross-brand pain point frequency table, not just your brand's own reviews. This shows you which pain points are universal to the category vs. unique to your brand.

### What the Research Engine actually produces

Here's a real example from a Peck Purity research sprint:

> **Insight:** Backyard chicken keepers experience flat, matter-of-fact devastation when they lose birds — not dramatic grief, but quiet helplessness expressed through casual language like "my chickens just kept dropping dead."
>
> **Theme:** The Post-Crisis Convert
> **Persona:** Post-Crisis Prevention Buyer
> **Evidence Count:** 12 separate Reddit threads
> **VoC:** "My chickens just kept dropping dead. I couldn't figure out what was going on. I left everything empty for three years."

That insight doesn't just tell you "people are sad when chickens die." It tells you the *emotional register* (flat, not dramatic), the *exact language* they use ("kept dropping dead" — casual, visceral, unsentimental), and how many independent sources confirm it (12 threads, not one outlier post).

### How VoC becomes copy

Here's the actual path from a real VoC finding to a real headline:

**1. Reddit thread:** A keeper writes, "There is no egg withdrawal period with elector :)" — The smiley face is the most honest emotional signal in the entire dataset. Pure relief.

**2. VoC pattern identified:** Egg withdrawal is the #1 quantitatively confirmed pain point across every on-target sprint. It's simultaneously the #1 reason they avoid chemical dewormers AND the #1 relief signal for natural alternatives.

**3. Angle hypothesis:** "Your breakfast shouldn't require a waiting period."

**4. Testing strategy ranking:** Test this FIRST because it appeared in multiple independent threads (not one source) and is the most product-ownable claim in the data.

**5. Final headline (from Brief 1):**

> "Egg Withdrawal: 5 days? 7 days? 14 days? Try zero."

That headline uses the exact conflicting numbers from forum discussions. It didn't come from brainstorming. It came from reading what people actually argue about.

---

## Part 3: The Three Frameworks (Working Together in Every Brief)

Every brief I write makes three simultaneous strategic decisions. These aren't separate tools — they work together to determine the tone, pressure, and arc of every ad.

### Framework 1: TEEP Stages

Where is this person in their buying journey?

| Stage | What they're doing | Ad goal | CTA energy |
|-------|-------------------|---------|------------|
| **Trigger** | Something just happened. Droppings changed. Lost a bird. Saw a forum post that made the threat real. | Stop-scroll recognition. Name the signal. | Low pressure. "Learn more." |
| **Exploration** | Searching. Reading threads. Comparing options. | Educational depth. Give her the information she's gathering. | Medium. "See how it works." |
| **Evaluation** | Comparing products. Narrowing choices. | Resolve the comparison. Win the side-by-side. | Direct. "Try Peck Purity." |
| **Purchase** | Ready to buy. Needs the last nudge. | Remove the final objection. | Confident. "Start today." |

### Framework 2: Three Selves (Self-Discrepancy Theory)

Which version of the buyer are we speaking to?

| Self | Language pattern | When to use | Peck Purity example |
|------|-----------------|-------------|-------------------|
| **Ought** | Imperative. Obligation. "You should." "Stop doing X." | When she needs a nudge to act on something she already believes. | "If it makes you throw eggs away, why are you still using it?" |
| **Actual** | Reflective. Validation. "You're not wrong." "This is happening." | When she needs recognition before she can act. | "Dewormers work for a month. Worms come back in two." |
| **Ideal** | Aspirational. Identity. "The keeper who..." "Your best..." | When she wants to see the version of herself the product creates. | "The keeper who has everything covered adds this to the feed." |

**The ratio is deliberate.** In Brief 1 (No Egg Withdrawal), the split is 4 Ought + 2 Actual, because the Proactive Flock Guardian already knows the trade-off is absurd — she just needs the nudge. In Brief 2 (Prevention After the Loss), it's 4 Actual + 2 Ought, because the Post-Crisis Keeper carries guilt and needs validation *first*.

Too much Ought with a buyer who needs validation = tone-deaf. Too much Ideal with a buyer in crisis = feels dismissive. The mix is a strategic decision, not a creative preference.

### Framework 3: Emotional Zones (Valence x Intensity)

What emotional state is the buyer in, and where does the ad take them?

| Zone | What it feels like | Example |
|------|-------------------|---------|
| **Zone 1** (Positive, Low Intensity) | Calm trust. Relief. Quiet confidence. | "I feel good about it because I know what's in it and I know how it works." |
| **Zone 2** (Positive, High Intensity) | Breakthrough. Proud confidence. "I found the answer." | "Your routine now covers the inside too." |
| **Zone 3** (Negative, Low Intensity) | Quiet frustration. Flat devastation. Resigned acceptance. | "My chickens just kept dropping dead. I couldn't figure out what was going on." |
| **Zone 4** (Negative, High Intensity) | Fear. Urgency. Panic. | "Is this safe to deworm chickens with?" (posted at 2am) |

**Every brief maps a journey.** Here's how it looks in practice:

> **Brief 1 (No Egg Withdrawal):**
> - Current state: Zone 3 — quiet frustration with conflicting withdrawal timelines
> - Target state: Zone 1 — relief, the trade-off is gone entirely
> - Ad positioning: Zone 1 — calm confidence, leads with the resolution
> - Journey rationale: She's been comparing numbers (5, 7, 10, 14 days) that nobody agrees on. The ad meets that math with one number: zero. Calm tone builds trust.

> **Brief 2 (Prevention After the Loss):**
> - Current state: Zone 3 — flat devastation. Not angry. Exhausted and quietly defeated.
> - Target state: Zone 1 — quiet confidence. "I can start again."
> - Ad positioning: Zone 3 moving to Zone 1 — reflects her experience back, then pivots to prevention
> - Journey rationale: She doesn't need to be scared or educated. She needs to see that chemical treatment -> withdrawal -> reinfection isn't bad luck — it's a structural failure.

---

## Part 4: The Visual-Verbal Compliance Split

This is how we communicate things we legally can't say. Your designers need to understand this because **the image does the job the headline can't.**

### The rule

- **Visuals go aggressive.** Show the problem explicitly. X-ray hen with parasites visible. Worms near eggs. Folk remedy mess on the counter. Empty roost.
- **Copy stays compliant.** Ingredient facts only. Safe product language. "Supports a healthy gut." "Diatomaceous earth disrupts parasites physically."
- **The viewer connects the dots.** We never state the claim. They infer it.

### How it works in practice

The product bag says **"All-Natural Chicken Dewormer"** in large print. Our copy never says "dewormer." The viewer sees the bag, hears the safe language, and connects the two.

**From the compliance guidelines:**

> "Ingredient facts ≠ product claims. You can state what DE does as a factual mechanism. You cannot say Peck Purity 'kills' or 'treats' anything."

| What we CAN say | What we CANNOT say | Why |
|----------------|-------------------|-----|
| "Diatomaceous earth disrupts parasites physically" (ingredient fact, DE is the subject) | "Peck Purity disrupts parasites" (product claim) | Product isn't FDA-approved as a drug |
| "Supports a healthy gut" | "Prevents worms" | Prevention claim about the product |
| "Formulated with diatomaceous earth" | "All-natural dewormer" (the BAG says this, our copy doesn't) | The bag is the compliance workaround |

### Why this matters for designers

**The image and headline must not do the same job.** If the image shows the product, the headline names the problem or ingredients. If the image shows the problem, the headline names the solution.

From T003 Static Briefs, Concept C (The Signal):
> "Close-up of a hen with an overlay or cutaway showing her gut and digestive tract. Outside she looks normal. Inside, something's happening."

That image communicates "your chickens might have parasites" without anyone saying it. The headline that sits next to it says: "Liquid droppings? That's the gut talking. Diatomaceous earth supports it physically." Compliant. But the viewer sees the x-ray hen + the headline and understands exactly what this product does.

**The product bag is your co-star.** Every concept requires the bag visible, front-facing, large enough to read "All-Natural Chicken Dewormer" at phone size. The bag IS the claim. Make it legible.

---

## Part 5: How T-Batches Build on Each Other

This is not "make 4 rounds of ads." Each batch has a specific purpose and each one teaches us something that shapes the next.

### The testing loop

| Batch | Purpose | What we're learning | Peck Purity example |
|-------|---------|-------------------|-------------------|
| **T001** | Hypothesis testing | Which ANGLE resonates. Not optimizing creative — testing ideas. | 2 briefs, 2 angles: No Egg Withdrawal + Prevention After Loss. Both positioning against chemical dewormers. |
| **T002** | Refinement | What the data from T001 tells us to change. Gap analysis drives re-briefing. | Angles narrowed from forum composites to real buyer profiles from customer calls. Register shifted from aggressive to pragmatic to match actual buyer temperature. |
| **T003** | Format expansion | Winning angles get new formats (statics, listicles). More concepts per angle. | 3 briefs, 14 total concepts. Angles came from customer call transcripts, not assumptions. Chili mix replaced essential oils as positioning target (Chris's actual switch). |
| **T004+** | Channel expansion | UGC video, new campaigns, new creators. | 6 UGC concepts, 3 hooks each. Grounded in the same customer calls. Scripts are direction, not copy. |

### Tests are ranked by data strength, not creative preference

From the Peck Purity Testing Strategy:

> **Why test "No Egg Withdrawal" first:** Egg withdrawal is the single most quantitatively confirmed pain point across every on-target sprint — confirmed from multiple separate threads, not one source. It is simultaneously the #1 reason they avoid chemical dewormers AND the #1 relief signal for natural alternatives.

> **Why test "Never Leave the Coop Empty" second:** The narrative from a single thread gives a concrete, devastating picture of what inaction costs. But note — one highly resonant post, not dozens. It's placed second because the evidence base is narrower.

> **Why test "Not Another Essential Oils Remedy" fourth:** This requires more setup — it's a reframe, not a hook. Run it after Tests 1-3 give you conversion signal, so you know which buyer is responding before investing in the more nuanced credibility story.

### What actually shifted between batches (Peck Purity T002 → T003)

This is the kind of thing the process log captures — what the data corrected about our assumptions:

> - **Forum research suggested the buyer was in crisis.** Real buyers (from customer calls) were calmer and more pragmatic.
> - **Forum research suggested positioning against folk remedies broadly** (garlic, essential oils). Real buyer was switching from a specific product (chili mix).
> - **Forum research suggested aggressive emotional register.** Real buyer says "worth a try" and "preventive only."
> - **Real buyers name ingredients by name before purchasing.** Ingredients moved from subheadings to headlines.

This is why the batches exist. T001 assumptions get corrected by real data, and T003 reflects what we actually learned.

---

## Part 6: Anatomy of a Creative Brief

Every brief I hand to a designer follows the same structure. Here's what each part does and why it's there, using a real brief as the example.

### The strategy notes (above the code block — for context, not execution)

```
BRIEF 1: NO EGG WITHDRAWAL

STRATEGY NOTES
- ANGLE: Zero egg withdrawal — positioning against chemical dewormers
- STAGE: Evaluation
- STAGE GOAL: Resolve the comparison she's already making. Prove Peck
  Purity eliminates the trade-off chemical dewormers force.

EMOTIONAL JOURNEY:
- Customer current state: Zone 3 — quiet frustration with conflicting
  withdrawal timelines, resigned to throwing eggs away
- Target state: Zone 1 — relief, the trade-off is gone entirely
- Ad positioning: Zone 1 — calm confidence, leads with the resolution
- Journey rationale: She's been comparing numbers (5, 7, 10, 14 days)
  that nobody agrees on. The ad meets that math with one number: zero.

- SELF TARGET: Ought (4 headlines) + Actual (2 headlines)
- SELF RATIONALE: Ought dominates because she needs the nudge — she
  already knows the trade-off is absurd. Actual validates her frustration.
```

**Why this matters for designers:** It tells you WHY this ad exists and WHO it's for. When you're choosing between two visual directions and they both "look good," the strategy notes help you pick the one that matches the emotional journey.

### The execution section (inside the code block — what the designer actually uses)

**CONTEXT** — One paragraph about the exact buyer moment. Not a persona description. The specific mental state she's in when she sees this ad.

> "This buyer raises chickens for eggs her family eats daily. Chemical dewormers force 7-14 days of throwing those eggs away — and nobody agrees on how many days."

**FORMAT** — How the ad will be laid out.

> "Us vs. Them comparison (Directions 1 & 4). Hero image + headline overlay (Directions 2 & 3)."

**IMAGE DIRECTIONS (Phase 1: What the image shows)** — The narrative content. What should be photographed or generated. Each direction is a different visual approach to the same angle.

> "Direction 1 — Carton Comparison (Split format). Left: egg carton with several eggs missing or X'd out in red, generic unlabeled chemical dewormer bottle beside it. Right: full, perfect egg carton, warm morning light. Both on a kitchen counter."

**COMPOSITION (Phase 2: How the designer puts it together)** — Layout, hierarchy, product placement, trust badge, color guidance.

> "Chemical side: cooler tones, muted, clinical. Prevention side: warm, golden, abundant. Temperature contrast between sides should be immediately felt."

**Phase 1 and Phase 2 are separate on purpose.** Phase 1 is "what to show." Phase 2 is "how to arrange it." Mixing these up leads to confusion about whether a note is about the photograph or the layout.

**COPY** — Headlines grouped by Self type. Subheadings that pair with headlines (no redundancy between them). CTA.

> HEADLINES (Ought — chemical positioning):
> 1. Chemical dewormers: 14-day withdrawal. Peck Purity: zero.
> 2. Egg Withdrawal: 5 days? 7 days? 14 days? Try zero.
> 3. If it makes you throw eggs away, why are you still using it?
>
> HEADLINES (Actual — mechanism):
> 4. DE disrupts parasites mechanically. No chemicals enter the egg.
> 5. Physical Parasite Prevention For Your Flock. No Chemicals. Zero Egg Withdrawal.
> 6. DE + Yucca Schidigera. One scoop. Zero withdrawal days.

**WHAT TO AVOID** — Guardrails that prevent common mistakes.

> - Don't make the chemical side scary or dramatic — Zone 1 calm, not Zone 4 fear
> - Don't show sick or distressed chickens
> - Don't overcrowd with text — visual comparison does the work
> - Product shot present but never dominant

### The headline-subheading pairing rule

**Each ad = headline + subheading. Each part does one job. No redundancy.**

Whatever the headline covers, the subheading does NOT repeat. Whatever the headline leaves out, the subheading fills in.

| If headline does this... | Subheading does this |
|--------------------------|---------------------|
| Names ingredients | Mechanism + proof/guarantee/simplicity |
| Doesn't name ingredients | Ingredients + mechanism |
| Explains mechanism | Product bridge |
| Covers everything | Guarantee or citation |

Real example from T003:

> **A.** Diatomaceous earth + Yucca. The formulation your chili mix never had.
> *D.E. disrupts parasites physically. One scoop daily.*

Headline = ingredients + competitive positioning. Subheading = mechanism + simplicity. Zero overlap.

---

## Part 7: UGC/Video Briefs — How Hooks Differ from Headlines

UGC briefs follow the same strategic framework but the execution is fundamentally different. Headlines are written to be *read*. Hooks must sound *spoken*.

### What makes a good UGC hook (criteria)

1. **Must sound like something a real chicken keeper would say out loud to a friend.** Read it out loud. If it sounds like a headline, rewrite it.
2. **Must include ICP language.** "My flock," "my girls," "chickens," "hens." Every hook, no exceptions.
3. **Must create an expectation gap.** Names a problem or situation AND hints the creator has the answer. The viewer stays for the payoff.
4. **At least one matter-of-fact hook per concept.** Not everything needs to be emotional.
5. **Past tense for resolved problems.** "I lost two of my girls" (past) implies she now knows what to do. Present tense doesn't give the viewer a reason to stay.
6. **Use VoC language patterns.** "Worth a try," "preventive only," "the best food, the best everything."

### Bad vs. good hooks (real examples from the iteration process)

| Before (sounds like ad copy) | After (sounds like a person) |
|-----|------|
| "Most chicken supplements use chili or garlic. Neither has a physical mechanism." | "Please stop giving your chickens those chili and garlic gut supplements. They don't have a physical mechanism." |
| "When my chickens' droppings changed, I knew something was going on in the gut." | "My chickens' droppings changed. I knew their gut was not okay. I'll admit it took some trial and error, but I found the solution." |
| "I lost two of my girls and I didn't know why. Here's what I changed." | "I lost two of my girls recently because of unwanted guests in their gut. Let me tell you what I changed so you don't go through the same thing." |

The difference: the "after" versions have specific cause, expectation gaps ("I'll admit it took trial and error"), and a reason for the viewer to stay ("so you don't go through the same thing").

### UGC brief structure (what the creator gets vs. what we keep internal)

Every UGC concept has two versions:

**Working doc (internal)** — Full strategy context:
- Call source (which customer's real story this is based on)
- Emotional arc (entry -> body -> payoff)
- Congruence check (does the video stay in one emotional lane)
- Planning script (strategic direction)
- Process notes and iteration history

**Creator package (what they actually receive):**
- "What to Talk About" (direction, key points, where to land)
- "Hooks to Test" (3 hooks with "Where to be" visual setup)
- "B-Roll to Record" (shot list — non-negotiable)
- "Example Script" (with "don't follow word for word" disclaimer)

**Why scripts are direction, not copy:** Script-reading kills authenticity. The example script shows the general flow. The creator says it in their own voice. Natural transitions, no clean breaks between problem and solution.

### The emotional arc check

Every UGC concept has a documented emotional arc and a congruence note. This prevents the video from starting in one emotional register and accidentally shifting to another.

Real example:
> **Concept 1 (Formulation Upgrade):**
> - Emotional arc: Calm evaluation -> ingredient comparison -> confident upgrade
> - Congruence: Opens evaluative, stays evaluative, resolves in confident choice. **Never dips into fear.**

We checked every concept against the actual customer call transcripts. The original assumption for Concept 1 was that Chris was frustrated with folk remedies. Reading the transcript again: Chris wasn't frustrated. She calmly compared formulations and found better ingredients. The entry emotion had to be corrected.

---

## Part 8: The Process Log (How We Compound Learning)

Every major deliverable includes a process log at the bottom. This isn't just documentation — it's a training manual for reproducing the quality bar.

### What a process log captures

1. **How we built the angles** — Where they came from (calls, reviews, forums), what the data showed, what it corrected about our prior assumptions
2. **How we wrote the copy** — The pairing rules, the compliance structure, the headline style variety
3. **What went wrong and what we fixed** — Specific mistakes and their corrections, so they don't repeat
4. **What shifted from the last batch** — What we learned and what changed as a result

### Real example: What went wrong in T003 and how we fixed it

From the Peck Purity T003 process log:

> **Universal subheading across all ads.** First draft used the same subheading on 12 of 14 ads. This created redundancy whenever the headline already named the ingredients. Fix: each ad gets its own paired subheading.
>
> **Naming ingredients without mechanism.** 8 of 14 ads named diatomaceous earth without ever explaining what it does. An ingredient name with no mechanism is an empty name-drop. Fix: every ad that names D.E. must also state the mechanism somewhere in the pair.
>
> **Floating mechanism verb = compliance risk.** "Disrupts parasites physically" with no subject reads as a product claim because the reader attaches it to whatever was just named (the product). Fix: always use "Diatomaceous earth disrupts parasites physically" with the ingredient as subject.

These lessons get applied to every future brief. The process log is how we avoid making the same mistake twice.

---

## Part 9: The Testing Strategy (How We Decide What to Test and When)

This is where the research meets the ad account. The Testing Strategy doc is written BEFORE briefs and defines the order, rationale, and targeting for each test.

### What a testing strategy contains

For each test:
- **The angle hypothesis** — One sentence.
- **Why test this first/second/third** — Based on data strength (evidence count, source diversity), not creative preference.
- **Target persona** — Which ICP this angle speaks to, and why her specifically.
- **What triggers her** — The specific external event that makes the abstract threat real.
- **Why this test matters to her** — The emotional need this angle resolves.
- **Hook territory** — 2-3 hook directions to test.
- **Source threads** — Reddit links proving the angle is grounded in real data.

### Real example: Peck Purity's first five tests, ranked

| Test | Angle | Why this rank | Target | Data strength |
|------|-------|--------------|--------|---------------|
| 1 | No Egg Withdrawal | Most confirmed pain point. Multiple independent threads. Most product-ownable. | Proactive Flock Guardian | Highest — confirmed across every sprint |
| 2 | Never Leave the Coop Empty | Single most viscerally persuasive quote. But traces to fewer sources. | Post-Crisis Convert | High — but narrower evidence base |
| 3 | One Scoop, That's the Routine | Exhaustion with information overload is documented. TikTok-native format. | Overwhelmed Natural-Leaning Keeper | Medium — traces to one highly resonant post |
| 4 | Not Another Essential Oils Remedy | Requires more setup (reframe). Run after conversion signal from 1-3. | Skeptical Experienced Keeper | Medium — requires nuanced execution |
| 5 | DE That Never Hits the Air | Specific solved objection for an already-motivated buyer. | DE-curious but scared of dust | Narrow but specific |

**The bottom line from the Peck Purity testing strategy:**

> "Lead with egg safety. It's the most confirmed, most specific, and most product-ownable claim in the data. If Peck Purity owns 'no egg withdrawal, ever' in this market, that's a defensible position that competitors who use chemical dewormers structurally cannot match."

---

## Part 10: The AI Tools in Practice

These are the tools that let one strategist + a design team produce the volume of a much larger operation.

### Research Engine

**What it does:** Takes a brand brief + research direction, automatically discovers relevant subreddits, scrapes conversations, extracts and scores evidence, discovers themes, normalizes personas, writes structured insights, and mines language patterns.

**Output:** `insights_final.csv` (20-40 insights with evidence counts, VoC quotes, persona assignments) + `language_report.json` (how the audience actually talks).

**Run time:** 7-25 minutes per sprint.

**When I use it:** At the start of every new brand or campaign. Multiple sprints per brand, each targeting a different research direction. Petsmont had 6 gut health sprints alone.

### /statics-briefer

**What it does:** 4-gate workflow that produces static ad briefs using all three frameworks (TEEP + Three Selves + Emotional Zones).

- Gate 1: Stage + Emotional Journey
- Gate 2: Format + Elements
- Gate 3: Headlines + Subheadings (with Self-strategy assessment and style selection)
- Gate 4: Designer Guidance (Phase 1: image generation, Phase 2: composition)

**Key principle:** Every ad must pass the 2-second zero-context clarity test on the COMPLETE ad (format + visual + headline), not headline alone.

### /listicle-writer

**What it does:** 9-gate system where each numbered point is a sales argument, not just education. Built around a unifying theme.

- Gate 1: Research (4 parallel tracks: customer voice, competitive landscape, pain point, evidence)
- Gate 2: Theme selection (specific lens: audience + desire/pain + constraint)
- Gates 3-9: Headlines, feature/benefit mapping, argument building, draft, review, imagery

**Sales argument types:** Mechanism, competitive, social proof, evidence, risk reversal, credibility.

### /native-ad-creative

**What it does:** Generates native ad headlines + image direction using direct response psychology. Core principle: "Copy sells. Design gets in the way."

**Psychological angles:** Curiosity gap, enemy framing, authority, social proof, contrarian, fear + discovery, identity filtering.

### /ad-library

**What it does:** Batch scrapes Meta Ad Library for competitor creative. Downloads video/image media. Optional Gemini visual analysis for messaging angle categorization.

### /transcribe

**What it does:** Routes video/audio to either local MLX (speech-to-text, free) or Gemini API (visual context, captions, structured script breakdowns).

---

## Part 11: Folder Structure

Every brand follows this structure:

```
Brand Name/
├── 00 Context/
│   ├── Brand Context - [Brand].md      <- Who they are, positioning, tone
│   ├── Product Context - [Product].md  <- Specs, ingredients, pricing, claims
│   ├── Compliance Guidelines.md        <- Safe/unsafe language (if regulated)
│   ├── Reviews.jsonl                   <- Scraped customer reviews
│   ├── Raw Research files              <- VoC, competitor analysis, ICP
│   └── From Client/                    <- PDFs, call transcripts, docs
│
├── 01 REF Images/                      <- Visual direction references
├── 02 Product Images/                  <- Product photos, mockups
│
├── YYYY-MM-DD T001 Testing Strategy    <- What to test first and why
├── YYYY-MM-DD T001 Creative Briefs     <- First test batch
├── YYYY-MM-DD T002 Creative Briefs     <- Refinement based on T001 data
├── YYYY-MM-DD T003 Static Briefs       <- Format expansion
├── YYYY-MM-DD T004 UGC Creator Briefs  <- Channel expansion
├── YYYY-MM-DD Listicle Draft           <- Long-form educational content
└── YYYY-MM-DD Video Direction Brief    <- Video-specific strategy
```

**File naming convention:** Date first, always. `YYYY-MM-DD [Type] [Batch] - [Brand/Product].md`

---

## Part 12: Internal vs. External Documents

Every deliverable has two audiences. Keeping them separate is how we maintain strategic control while giving creatives clean direction.

| | Working doc (internal) | Creator/Client package (external) |
|---|---|---|
| **Contains** | Full strategy rationale, process log, iteration history, compliance reasoning, call sources, emotional arc descriptions | Only what execution needs |
| **Tone** | Strategic, analytical | Directive, clean |
| **References** | "Gary said X," "T001 data showed Y," "ad account top spenders" | None of this |
| **Length** | 400-500 lines (Peck Purity T004 working doc: 463 lines) | <150 lines per concept |
| **Section names** | "Creator Blurb," "B-Roll Shot List," "Setup" | "What to Talk About," "B-Roll to Record," "Where to be" (plain language) |

**Rule:** Briefs must not reference internal processes or assume the reader has context. No "we tested," "we found," "based on the ad account." The creator gets direction. The strategy stays internal.

---

## Quick Reference: The Complete Workflow

1. **Research** — Scrape reviews (brand + competitors). Run Research Engine sprints on Reddit. Extract VoC, language patterns, emotional registers.
2. **Context docs** — Write Brand Context + Product Context + Compliance Guidelines. This is the foundation everything else builds on.
3. **Angle development** — Generate angle hypotheses grounded in VoC. Rank by evidence strength. Write headlines per angle, grouped by Self type.
4. **Testing strategy** — Define which angles to test, in what order, and why. Each test has a target persona, trigger, and source threads.
5. **T001 briefs** — First test batch. Hypothesis testing. Learning which angle resonates.
6. **Read the data** — What's spending? What's clicking? What's converting?
7. **T002 briefs** — Refinement. Gap analysis. Correct assumptions based on real performance.
8. **T003 briefs** — Format expansion. Winning angles in new formats (statics, listicles).
9. **T004+ briefs** — Channel expansion. UGC video, new creators, new campaigns.
10. **Process log** — Document what worked, what didn't, and what shifted. This compounds learning across brands.

---

*Written March 2026. Based on the Peck Purity (GrubTerra) workflow from research through T004.*
