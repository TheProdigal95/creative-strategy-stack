# Art Direction and Image Prompt Crafting

## Image Slots

Every listicle has these image slots to art-direct:

1. **Hero image** — sets the visual tone for the entire page, appears above the headline
2. **Point images** — one per numbered point, supports the point's message
3. **CTA image** — product-focused, appears in the final call-to-action section

## Art Direction Process

This process has three steps. Complete them in order.

### Step 1: Set the Visual Direction (Entire Listicle)

Choose one visual style and one mood/lighting approach for the entire listicle. All images should feel like they belong on the same page. The zone and mode inform this choice.

Use the style table and zone-to-lighting table below to propose a visual direction. Explain why the recommended style fits the zone, mode, and audience. Confirm with the user before moving on.

If the user provides a reference image, describe its key visual qualities (lighting, color palette, composition style, texture) and carry those qualities into every prompt as explicit descriptors.

### Step 2: Propose Image Concepts (All Slots at Once)

For each image slot, propose 2-3 options describing what is literally in the frame. Include a brief rationale for each option explaining why it works for that specific point and zone.

Present all slots in a single message using this format:

```
**Hero Image**
- Option A: [subject, action, setting] — [why this works]
- Option B: [subject, action, setting] — [why this works]

**Point 1: [point headline]**
- Option A: [subject, action, setting] — [why this works]
- Option B: [subject, action, setting] — [why this works]
- Option C: [subject, action, setting] — [why this works]

**Point 2: [point headline]**
- Option A: [subject, action, setting] — [why this works]
- Option B: [subject, action, setting] — [why this works]

[...remaining slots...]

**CTA Product Image**
- Option A: [subject, action, setting] — [why this works]
- Option B: [subject, action, setting] — [why this works]
```

Wait for the user to select one option per slot or request adjustments. Do not craft prompts until all concepts are approved.

### Step 3: Generate Prompts

After all concepts are approved, craft a Nano Banana Pro prompt for each slot using the approved concept, the visual style set in Step 1, and the prompt structure detailed below. Present all prompts together in the output format at the bottom of this file.

---

## Subject and Action Guidelines

When proposing what to show in each image, be specific about what the camera sees.

- **Person**: who (age range, gender if relevant), what they are doing, their expression
- **Product**: the product in use, in context, or isolated
- **Scene**: environment, setting, background elements
- **Combination**: person + product in a real scenario

Good: "Woman in her 40s mid-plank on a living room floor, slight grimace of effort, morning light"
Bad: "Someone exercising"

## Visual Style Options

| Style | Description | Best For |
|-------|-------------|----------|
| **UGC / iPhone** | Looks like a real person took it on their phone. Slightly imperfect framing, natural lighting, casual setting. No studio feel. | Direct mode, Zone 3-4. Audiences skeptical of polished ads. |
| **Lifestyle editorial** | Magazine-quality but not sterile. Styled but feels real. Shallow depth of field, intentional composition. | Educational mode, Zone 1-2. Premium products. |
| **Studio product** | Clean background, controlled lighting, product as hero. Minimal context. | Fix section, CTA section. Product detail shots. |
| **Raw/documentary** | Candid, unposed, mid-action. Grain is OK. Feels like a still from real life. | Zone 3 (frustration). Before/during struggle moments. |
| **Metaphorical/conceptual** | Abstract or symbolic representation of the point's message. Not literal. | Educational mode. Points about invisible benefits (stress, energy, posture). |
| **Before/after** | Split or sequential showing transformation. Clear contrast. | Zone 2 (breakthrough). Results-focused points. |

## Mood and Lighting by Zone

The emotional zone determines the visual mood. Stay consistent.

| Zone | Lighting | Color Temperature | Feel |
|------|----------|-------------------|------|
| Zone 1 (Calm trust) | Soft, even, natural. Golden hour or overcast. | Warm | Inviting, peaceful, approachable |
| Zone 2 (Breakthrough) | Bright, clean, energetic. Morning sun or studio key light. | Neutral to warm | Optimistic, vibrant, forward |
| Zone 3 (Frustration) | Muted, flat, slightly underexposed. Overcast or dim indoor. | Cool to neutral | Tired, relatable, honest |
| Zone 4 (Urgency) | High contrast, dramatic shadows. Harsh or directional light. | Cool | Tense, stark, uncomfortable |

## Nano Banana Pro Prompt Structure

Craft each prompt using this structure. Order matters — Nano Banana Pro weights earlier elements more heavily.

```
[Subject and action], [setting/environment], [lighting and mood], [visual style], [camera/lens details], [aspect ratio guidance]
```

### Prompt Components

**Subject and action** — The most important element. Lead with it.
- Be specific about pose, expression, and what the person is doing
- Name the product if it appears in frame
- Describe the moment, not the concept

**Setting/environment** — Where the scene takes place.
- Interior vs exterior, specific room type, background elements
- Keep it simple. 2-3 details max.

**Lighting and mood** — Controls the emotional register.
- Name the light source (window light, overhead sun, studio softbox)
- Describe quality (soft, harsh, diffused, directional)
- Include color temperature if important (warm golden, cool blue)

**Visual style** — How the image should feel as a photograph.
- Reference the style chosen from the table above
- Add photographic qualifiers: "shot on iPhone", "editorial photography", "product photography"
- For UGC: "candid, slightly imperfect framing, natural"
- For editorial: "shallow depth of field, intentional composition, editorial quality"

**Camera/lens details** — Optional but improves realism for photographic styles.
- Portrait/product: "85mm lens, f/1.8, shallow depth of field"
- Lifestyle wide: "35mm lens, f/2.8"
- UGC/iPhone: "shot on iPhone, wide angle, no professional lighting"
- Product detail: "macro lens, close-up, sharp focus"

**Aspect ratio** — Match the layout needs.
- Hero image: 16:9 or 3:2 (landscape, wide)
- Point images: 4:3 or 3:2 (landscape, standard)
- CTA product image: 1:1 or 4:5 (square or near-square)

### Example Prompts by Style

**UGC / iPhone (Zone 3, Direct):**
```
Woman in her 40s pausing mid-plank on a yoga mat, rubbing her lower back with one hand, pained expression, living room floor with morning clutter visible, flat overcast light from a window, muted colors, shot on iPhone, candid framing, slightly off-center, no professional lighting
```

**Lifestyle editorial (Zone 2, Educational):**
```
Fit man in his 30s holding a strong plank position on a cushioned plank board, focused expression, bright modern home gym, morning sunlight streaming through large windows, warm golden tones, editorial fitness photography, 35mm lens, shallow depth of field, clean composition
```

**Studio product (Fix section / CTA):**
```
Plank board with ergonomic handles photographed from a 45-degree angle on a clean white surface, three-point softbox lighting, soft shadows, product photography, sharp focus throughout, 85mm macro lens, neutral white background, 1:1 aspect ratio
```

**Raw/documentary (Zone 3):**
```
Close-up of hands gripping a hard floor during a plank, knuckles white, forearms trembling, concrete floor texture visible, dim overhead fluorescent lighting, cool desaturated tones, documentary photography, candid, grain visible, 4:3 aspect ratio
```

**Metaphorical/conceptual (Zone 1, Educational):**
```
Overhead view of a spine model made of wooden blocks perfectly aligned on a warm wooden table, soft diffused natural light, warm tones, minimalist composition, conceptual still life photography, 50mm lens, clean and calming, 3:2 aspect ratio
```

## Prompt Quality Rules

1. **No abstract language.** Describe what the camera sees, not what the viewer should feel. "Morning light through curtains" not "peaceful atmosphere."
2. **No brand slogans or text overlays in prompts.** Nano Banana Pro handles text poorly. If text is needed on the image, add it in post-production.
3. **One clear subject per image.** Do not ask for complex multi-person scenes.
4. **Specify what NOT to include** if needed. "No text, no watermarks, no logos."
5. **Keep prompts under 75 words.** Longer prompts dilute the model's focus.
6. **Style consistency across all prompts.** If the first prompt says "shot on iPhone, candid," every point image should maintain that style.

## Prompt Output Format

Present all prompts together in a clean format the user can copy directly:

```
## Listicle Image Prompts

Style reference: [description of reference qualities, if provided]
Consistent style: [chosen style from art direction]
Aspect ratios: Hero 16:9 | Points 4:3 | CTA 1:1

---

### Hero Image
[prompt]

### Point 1: [point headline]
[prompt]

### Point 2: [point headline]
[prompt]

[...remaining points...]

### CTA Product Image
[prompt]
```
