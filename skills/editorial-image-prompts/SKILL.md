---
name: editorial-image-prompts
description: Generates editorial-style image prompts that look like real content, not ads. Guides users through style selection and builds hyper-detailed prompts for Nano Banana Pro (Gemini). Use when the user mentions editorial images, editorial style images, native ad images, or wants to generate images that don't look like ads.
allowed-tools: Skill(gemini-imagegen)
---

# Editorial Image Prompt Generator

Generate image prompts that produce editorial-quality visuals — images that look like they belong in magazines, medical textbooks, scientific journals, or candid photojournalism. Never like ads.

## Core Principle

The reason native ad images fail is they look like ads. This skill produces prompts for images that look like authentic editorial content readers actually engage with.

## Why These Images Convert

Native ad readers are in a fundamentally different state than social media scrollers:

- **Social media:** anxious scrolling, swiping fast, dopamine-chasing. Your ad interrupts entertainment.
- **Native/editorial:** focused reading, leaning in, absorbing content. Your ad extends their experience.

Images must match the editorial environment. The images that convert best are the ones that feel like content — often the ones a designer would reject:

- A weird close-up of a toenail
- A cross-section of a knee
- A banana with spots

These work because they look like something a medical journal, science magazine, or editorial photographer produced — not a marketing team. They trigger curiosity, not ad blindness.

**When recommending styles, lean toward visceral and clinical over polished and pretty.** The uncomfortable, hyper-detailed, "I can't look away" images outperform clean stock-photo aesthetics every time. Guide the user toward what converts, not what looks nice in a mood board.

## How to Use This Skill

### Mode 1: Single Image

When the user needs one image, follow this flow:

1. Ask what the image is for (subject, context, where it will be used)
2. Suggest 2-3 editorial styles from the Style Menu that fit the subject
3. Let the user pick
4. Ask any clarifying questions about the specific scene
5. Build the full prompt using the Prompt Architecture
6. Hand off to `gemini-imagegen` for generation

### Mode 2: Multi-Image from Brief

When the user has a brief, listicle, advertorial, or ad set:

1. Read the brief and identify all image slots
2. Map each slot to the content section it supports (hero, problem, mechanism, solution, CTA)
3. For each slot, suggest 1-2 editorial styles from the Style Menu with a short rationale
4. Present all recommendations at once so the user can review and adjust
5. Ask clarifying questions for any image where you need more context
6. Build all prompts
7. Generate images sequentially using `gemini-imagegen`

Always present style recommendations as suggestions the user can override.

## Style Menu

Present these options when guiding the user. Use the description to help them understand what each style looks like.

### 1. Macro Clinical Photography

Extreme close-up, scientific documentation feel. Razor-sharp focus on a specific area with shallow or deep depth of field. Sterile lab bench or grey background. Reference scales, clinical lighting.

**Best for:** Product texture, biological processes, decay, before/after damage.

### 2. Flat Lay Lifestyle

Overhead top-down shot of a "lived-in" surface — kitchen counter, desk, bathroom shelf. Scattered objects, imperfections, natural morning light, film grain. Feels candid and unposed.

**Best for:** Supplement scenes, daily routine, kitchen/bathroom products, relatable lifestyle.

### 3. Medical Textbook Illustration

Professional anatomical cross-section (sagittal, coronal, or lateral). Clean white background, high-contrast anatomical colors (pink for muscle, tan for bone, white for ligaments). Modern textbook style.

**Best for:** Explaining a condition, showing internal anatomy, pathology, how a health issue works.

### 4. Vintage Engraving / Anatomical Atlas

19th-century copperplate engraving on aged parchment. Cross-hatching, stippling, Latin labels, sepia ink, foxing marks, water stains, frayed edges. Muted earth tones.

**Best for:** Authority, credibility, historical medical context, "old wisdom" feeling.

### 5. Neural / Brain Heat Map

Dark blue or charcoal background. Specific brain regions illuminated with glowing orange/red heat maps. Neural pathways shown as cyan/white electrical sparks. Scientific aesthetic.

**Best for:** Stress, anxiety, sleep, cognitive function, brain health, mood, focus.

### 6. Hyperrealistic Candid / Street

Cinematic street or lifestyle photography. Specific camera body and lens. Environmental storytelling — the subject exists in a real-world context. Bokeh backgrounds, long shadows, natural imperfections.

**Best for:** Relatable human moments, posture issues, fatigue, lifestyle conditions, "caught in the act" realism.

### 7. Medical Imaging (X-ray / CT / Venogram)

Radiographic aesthetic — blue-on-black or charcoal background. Translucent bone layers, glowing contrast fluid, clinical focus. Mimics actual diagnostic imaging.

**Best for:** Internal visualization, vein/artery issues, bone density, organ scans, body composition.

### 8. Comic / Editorial Illustration

Bold ink outlines, flat cell shading, bright primary colors. Uses visual metaphors (head as pressure cooker, feet as screaming faces). Comic conventions like emanata (plewds, agitrons, motion lines, impact stars).

**Best for:** Humor, relatability, making complex conditions approachable, social media engagement, lighter tone.

### 9. Multi-Panel Comparative Grid

Grid layout (2-panel or 4-panel). Consistent style across all panels. Side-by-side comparison of different body areas, stages of a condition, or healthy vs. damaged states.

**Best for:** Showing a condition across multiple joints/organs, progression, before/after comparison.

## Composition Techniques

These are not styles — they are structural techniques that can be applied across any style.

### Before/After Split

A single image divided left-to-right: damaged/unhealthy state on the left, improved/healthy state on the right. Works with medical illustration, 3D rendering, comic, or infographic styles.

Key elements:
- Left side shows the problem (inflamed tissue, fat nodules, frayed fibers, visible damage)
- Right side shows the result (smooth tissue, tightened structure, improved flow)
- A visual indicator bridges the two (glowing lines, gradient transition, timeline label)
- Optional: a single text label like "After 60 Days" on the improved side

Use this when the user is showing a transformation, product efficacy, or treatment outcome.

### Product Integration

Place the actual product within an editorial scene rather than as a separate packshot. The product should feel like it belongs in the environment — a cream jar on a bathroom shelf in a flat lay, a supplement bottle among scattered pills on a kitchen counter.

- Include a readable product label when the user wants brand visibility
- Keep the product secondary to the editorial scene — it should be discovered, not spotlighted
- Works best with Flat Lay Lifestyle and Comic/Editorial Illustration styles

## Prompt Architecture

Every prompt follows this layered structure. Build each layer in order.

### Layer 1: Style and Medium Declaration

Always open the prompt by declaring what kind of image this is. Be specific.

```
Hyperrealistic macro photography...
A professional medical grade anatomical illustration...
A vibrant comic-strip illustration...
A high-resolution lateral radiographic (X-ray) view...
Overhead top-down flat lay photograph...
```

### Layer 2: Subject with Hyper-Specific Detail

Never describe things generically. Use precise anatomical, material, or environmental language.

- NOT "a knee" — "a swollen human knee joint in cross-section with severely inflamed, reddened, and frayed articular cartilage"
- NOT "a messy desk" — "a worn wooden butcher block with visible scratches, crumbs, and dried coffee cup rings"
- NOT "a tired person" — "a woman mid-blink, struggling against a micro-sleep episode, her head slightly tilted, deep purple-toned dark circles under her eyes"

### Layer 3: Labeled Scene Sections

For complex scenes, organize with labeled sections. This tells the model exactly what to render and where.

```
The Pathology: [what's wrong — the focal point]
The Mechanics: [how it functions or fails]
Fluid Dynamics / Blood Flow: [movement within the scene]
Comparison: [healthy vs. damaged contrast]
The Action: [what the subject is doing]
Expression: [facial/body language details]
```

Use whichever labels fit the image. Not all are needed for every prompt.

### Layer 4: Authenticity Markers

Add imperfections that make it feel real and unproduced:

**For photography:** worn surfaces, scratches, coffee rings, crumbs, dust motes, film grain, wrinkled clothing, smudged handwriting, half-spilled objects

**For medical illustration:** frayed tissue, glistening wet textures, realistic color variation in tissue

**For vintage styles:** foxing marks, water stains, yellowed edges, deep creases, faded ink

**For comic illustration:** emanata (plewds/sweat drops, agitrons/vibration lines, motion lines, impact stars), onomatopoeia, exaggerated expressions

### Layer 5: Technical Camera Specs

Even for illustrations, camera language influences output quality. Include when appropriate:

- **Camera body:** Canon EOS R5, Sony A7R IV
- **Lens:** 85mm, 100mm macro
- **Aperture:** f/2.8 (shallow, dreamy blur), f/8 (deep, everything sharp)
- **Lighting:** softbox overhead, clinical fluorescent, directional morning light from window, late afternoon urban light with long shadows

For non-photographic styles, replace with render specs:
- **3D renders:** Octane render, global illumination, translucent layers
- **Medical imaging:** blue-on-black radiographic aesthetic, sharp clinical contrast
- **Comic:** bold ink outlines, flat cell shading

### Layer 6: Color Palette

Define the palette precisely, not with vague terms.

- "muted earth tones: sepia ink, faded oxidized blood-red washes, dull ochre and burnt umber"
- "clinical blue-and-amber lighting"
- "high-contrast anatomical colors: pinks for muscle, tan for bone, white for ligaments"
- "bright flat colors, bold ink outlines, white background"
- "monochromatic blue-scale, translucent bone layers"

### Layer 7: Quality Closers and Directives

End with resolution, quality tags, and negative directives:

```
8k resolution, extraordinarily detailed, award-winning scientific visualization
Ultra-detailed, photorealistic, cinematic clinical photography
Hyper-detailed, no text, scientific aesthetic
High-end CGI medical render, Octane render, extremely detailed, no text
```

**When to use "no text":** Include `no text` for pure medical/scientific styles where labels would look AI-generated or distracting.

**When to allow text:** For before/after comparisons, product-focused images, or infographic-style compositions, strategic text labels improve clarity. Specify the exact text and placement in the prompt (e.g., "An English label 'After 60 Days' appears on the healed side"). Keep labels minimal — one or two short phrases maximum.

## Comic Illustration: Visual Metaphor Guide

When building comic-style prompts, the key creative decision is the visual metaphor. Help the user brainstorm by mapping conditions to metaphors:

| Condition | Visual Metaphor |
|-----------|----------------|
| Brain fog / forgetfulness | Head as transparent glass dome with filing cabinet, drawers flung open, papers flying |
| Stress / burnout | Head as vintage pressure cooker, glowing cherry-red, steam shooting from ears |
| Anxiety / overwhelm | Thought tornado above head, worry bubbles with tiny disaster scenes, constriction bands around chest |
| Eye strain | Pinprick dot eyes, strain lines, phone screen showing glitchy unreadable squiggles |
| Foot pain | Feet replaced by screaming cartoon faces, lightning bolts from heels, pain stars trailing behind |
| Yo-yo dieting / stuck in a cycle | Person trapped in a literal hamster wheel surrounded by diet books, exercise equipment, and failed attempts |
| Information overload / distraction | 50 open browser tabs floating around person's head, spinning thought spirals, half-finished tasks everywhere |

When the user describes a condition, suggest 2-3 metaphor ideas for them to choose from.

## Aspect Ratio Guidance

Recommend aspect ratios based on image placement:

| Placement | Ratio | Notes |
|-----------|-------|-------|
| Hero / banner | 16:9 or 21:9 | Wide, attention-grabbing |
| In-article | 3:2 or 4:3 | Standard editorial proportion |
| Social media feed | 1:1 or 4:5 | Square or near-square |
| Story / vertical | 9:16 | Full-screen mobile |
| Medical diagram | 1:1 or 3:4 | Clean, focused |

## Quick Mode

For simple images (dental x-ray, basic scan, animal anatomy), a shorter prompt works:

```
[Style declaration], [subject], [key pathology or focus], [2-3 visual details], [aesthetic directive], no text
```

Example: "Dental x-ray style image showing full mouth, hidden cavities glowing, gum line issues highlighted, bone loss areas visible, authentic dental radiograph aesthetic, problem zones subtly emphasized"

Use quick mode when the user needs something fast or the subject is straightforward.

## Workflow Checklist

For each image prompt you build, verify:

- [ ] Opens with specific style/medium declaration
- [ ] Subject described with precise, not generic, language
- [ ] Labeled sections used for complex scenes
- [ ] Authenticity markers included (imperfections, textures)
- [ ] Technical specs present (camera/lens/lighting OR render style)
- [ ] Color palette explicitly defined
- [ ] Quality closers and resolution tags at the end
- [ ] "no text" included where appropriate
- [ ] Aspect ratio recommended based on placement

## Guidelines

- Always present style options before building the prompt — never assume a style without asking
- When the user picks a style, ask if they have specific scene details in mind before filling in defaults
- For comic illustrations, always brainstorm the visual metaphor with the user first
- Match the prompt length to the complexity: quick mode for simple images, full architecture for detailed scenes
- Recommend aspect ratio based on where the image will be placed
- After building the prompt, hand off to `gemini-imagegen` for generation
- If the user wants to refine, use `gemini-imagegen` multi-turn chat for iterative adjustment
