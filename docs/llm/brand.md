# The Open Harbor — Full Brand & Design Report

Nice name — *The Open Harbor* immediately communicates ease, accessibility, and a photographer-first brand. Below is a thorough, actionable brand and design guide you can hand to a designer or implement directly in your product. It covers visual identity, accessible color & type systems, UI patterns, developer tokens, motion, imagery, copy/voice, and a long list of common mistakes junior designers make — with fixes.

---

# 1 — Executive summary (one-paragraph)

**Positioning:** The Open Harbor is a simple, affordable file sharing platform built specifically for photographers and creative professionals. Focus on ease-of-use, beautiful galleries, and transparent pricing rather than complex security features. Visually: soft, modern, and nautical-but-abstract (no literal clip-art). Use deep teal as your anchor color plus a warm golden beacon color to differentiate from all-blue competitors. Prioritize accessible contrast, generous spacing, and human microcopy.

---

# 2 — Visual theme & mood

Core concepts to express visually:

* **Simplicity & ease** (clean layouts, intuitive navigation)
* **Creative showcase** (beautiful galleries, photo-focused design)
* **Affordability & accessibility** (friendly pricing, no barriers)
* **Professional quality** (clean grid, reliable performance)

Mood words to use when creating imagery & layout: calm, steady, warm, honest, clear, welcoming.

Moodboard cues:

* Abstract shapes inspired by waves and arcs (no literal boat/cargo photos)
* Close-up photos of photographers at work, client meetings, gallery showings, studio scenes
* Soft sand/off-white backgrounds rather than stark sterile white
* Light vignettes of golden-hour lighting

---

# 3 — Color system (tokens + usage & accessibility)

**Primary palette (use these exact hexes):**

* Harbor Trust (Primary): `--color-primary: #1E5F74`
* Beacon Light (Secondary / Accent): `--color-beacon: #F4A259`
* Anchor (Text / Dark): `--color-anchor: #2E2E2E`
* Sail Cloth (Page background neutral): `--color-bg: #F9F7F3`
* Horizon (Subtle highlight): `--color-horizon: #A3C9E2`
* White: `--color-white: #FFFFFF`

**Recommended usage percentages (rough):**

* Background / neutrals: 65–80% (`--color-bg`)
* Primary (trust color) for nav, headings, strong accents: 10–20%
* Secondary (beacon/golden) for CTAs & accents: 3–7% (use sparingly — it’s high-attention)
* Text and UI chrome (icons, body text): use `--color-anchor`

### Contrast & accessibility (WCAG)

WCAG thresholds:

* **Normal text (AA):** contrast ≥ 4.5:1
* **Large text (AA):** contrast ≥ 3:1
* **AAA normal:** ≥ 7:1

Key pairs (measured & tested):

* `#2E2E2E` on `#F9F7F3` (anchor on bg): **12.69:1** — excellent (AA & AAA). Use for body text.
* `#1E5F74` on `#F9F7F3` (primary on bg): **6.67:1** — good (AA); OK for headings & important UI.
* `#FFFFFF` on `#1E5F74` (white on primary): **7.13:1** — excellent (use white text on primary backgrounds).
* `#F4A259` on `#F9F7F3` (beacon on bg): **1.93:1** — **FAIL** (don’t use beacon for small body text on light bg).
* `#2E2E2E` on `#F4A259` (dark text on beacon): **6.57:1** — **GOOD** — use dark text when placing labels or CTAs on beacon background.

**Rule of thumb from the above:**

* Use `anchor` (`#2E2E2E`) for all body copy on `bg` (`#F9F7F3`).
* Use `white` text on `primary` backgrounds.
* Use `beacon` (`#F4A259`) primarily as **background** or accent with **dark text** `#2E2E2E`. Avoid using beacon as text color on light backgrounds.

---

# 4 — Typography

**Primary pairing (recommended, Google Fonts):**

* Headline: **Poppins** — geometric, friendly, works with heavier weights for presence.
* Body: **Inter** — highly legible, neutral, great for UI copy.

**Fallback stack:**

```css
font-family: "Poppins", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Suggested scale (desktop):**

* h1: 44px / 2.75rem — 700 / line-height 1.05
* h2: 34px / 2.125rem — 600 / lh 1.1
* h3: 26px / 1.625rem — 600 / lh 1.2
* h4: 20px / 1.25rem — 600 / lh 1.3
* body (base): 16px / 1rem — 400 / lh 1.5
* small: 14px / 0.875rem — 400 / lh 1.4

**Mobile adjustments:** reduce headings by ~10–15% or use responsive REM scaling.

**Line-length & spacing:** keep measure (characters per line) around 60–75 for comfortable reading. Use `line-height` 1.4–1.6 for body text.

---

# 5 — Logo & mark guidelines

**Primary logo idea:** a simple wordmark “TheSafeHarbor” with a compact abstract symbol to the left. Symbol ideas: stylized lighthouse beam (abstract arc), simplified anchor form built from two curved strokes, or an arc that suggests a harbor or sheltered curve. Keep it geometric and single-color friendly.

**Variations to prepare:**

* Full color horizontal lockup (symbol + wordmark)
* Stacked (symbol above wordmark)
* Symbol-only (square / circular avatar for social)
* Monochrome (black / white) variants

**Clearspace & minimum sizes**

* Clearspace = the height of the “T” in the wordmark (or the symbol’s bounding box × 0.6). Don’t place other elements inside this area.
* Min sizes: horizontal wordmark (web) = 120px wide; symbol-only = 40px.

**File formats to deliver**

* Vector (SVG) for all web use.
* EPS / PDF for print.
* PNG (1x, 2x) for legacy uses and favicons.
* Favicon sizes: 16×16, 32×32, and Apple Touch (180×180).

**Do not**

* Stretch, rotate, change proportions, or add shadows to the symbol.
* Use low-contrast versions for small UI elements.

---

# 6 — UI components & patterns (recommendations & example CSS)

**Spacing & grid**

* Base spacing unit: **8px** (scale: 4, 8, 12, 16, 24, 32, 48, 64).
* Grid: 12-column responsive grid with max content width 1200–1400px.

**Border radius**

* Buttons: `8px`
* Cards: `12px`
* Pills / tags: `999px` (fully rounded for chips)

**Elevation**

* Subtle shadows: `box-shadow: 0 6px 16px rgba(30,95,116,0.06)` for modals/cards.

**Buttons**

* Primary CTA (use primary): background `#1E5F74`, color `#FFFFFF`, padding `12px 20px`, border-radius `8px`.
* Secondary CTA (beacon as background): background `#F4A259`, color `#2E2E2E`, same padding.
* Ghost CTA: border `1px solid #1E5F74`, color `#1E5F74`, background transparent.

**Sample CSS variables + button styles**

```css
:root{
  --color-primary: #1E5F74;
  --color-beacon:  #F4A259;
  --color-anchor:  #2E2E2E;
  --color-bg:      #F9F7F3;
  --radius-btn: 8px;
  --btn-padding: 12px 20px;
}

/* Primary CTA */
.btn-primary {
  background: var(--color-primary);
  color: #fff;
  padding: var(--btn-padding);
  border-radius: var(--radius-btn);
  border: none;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:focus { outline: 3px solid rgba(244,162,89,0.18); }

/* Secondary CTA (beacon) */
.btn-secondary {
  background: var(--color-beacon);
  color: var(--color-anchor);
  padding: var(--btn-padding);
  border-radius: var(--radius-btn);
  border: none;
  font-weight: 600;
}
```

**Forms & inputs**

* Use `--color-anchor` for labels; inputs with `bg: #fff` and `border: 1px solid #E6E6E6`.
* Provide clear error states (red with icon + short message). Don’t rely on color alone — include icons or text.

---

# 7 — Iconography & imagery

**Icons**

* Style: rounded line icons, 2px stroke typical, export as SVG.
* Size tokens: 16, 20, 24 px in UI; ensure clickable areas are at least 44×44 px.

**Photography**

* Use warm, human-centered photos: creators in studios, small teams, hands at work, soft focus backgrounds.
* Avoid literal stock boats/harbors unless stylized & subtle.
* Lighting: golden-hour / warm reflect to match beacon accent.

**Illustration**

* If using illustrations, stick to a limited palette: use `primary`, `beacon`, and neutrals; make them semi-flat and friendly.

---

# 8 — Motion & micro-interaction

* **Timing:** use short durations: 120–180ms for most microinteractions; 250–350ms for larger transitions (modals).
* **Easing:** `cubic-bezier(.2,.9,.2,1)` or `ease-out` for lift/hover, `ease-in` for exits.
* **Micro-interactions:** hover lift (translateY(-2px), slight shadow), subtle scale on press. Avoid large parallax or disorienting motion. Provide an option to reduce motion for accessibility.

---

# 9 — Voice & microcopy

**Tone:** Friendly, encouraging, photographer-focused. Speak their language.
**Examples:**

* Headline (home): *"Easy file sharing for photographers"*
* Subhead: *"Store and share your photos with clients and teams — simple, affordable, and built for creatives."*
* CTA: *"Try it free"* or *"See how it works"*
* Empty state: *"Ready to share your first gallery? Drag photos here to get started."*
* Error (upload fail): *"Upload didn't work. Check your connection and try again."*

**Photography messaging** — focus on their workflow:

* "Perfect for high-res photos and client galleries"
* "Beautiful galleries that make your work shine"
* "Share entire shoots with a single link"

---

# 10 — Nonprofit messaging & monetization notes

If you go nonprofit:

* Messaging: emphasize stewardship, community, and trust. Example: “TheSafeHarbor is a 501(c)(3) non-profit — support secure, community-run file sharing.”
* Monetization: memberships, optional paid tiers, enterprise contracts, donations, grant funding, sponsorships.
* Salaries: nonprofits can pay reasonable salaries — ensure compensation is documented and approved by the board.

---

# 11 — Developer handoff (tokens + JSON example)

**Design tokens (JSON)**

```json
{
  "color": {
    "primary": "#1E5F74",
    "beacon": "#F4A259",
    "anchor": "#2E2E2E",
    "bg": "#F9F7F3",
    "horizon": "#A3C9E2",
    "white": "#FFFFFF"
  },
  "radius": {
    "button": "8px",
    "card": "12px"
  },
  "spacing": {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px"
  }
}
```

Use these tokens in code (CSS variables, theme provider in React, etc.). Provide Figma tokens file.

---

# 12 — SEO, metadata & quick copy

**Suggested meta description:**
*Simple, affordable file sharing for photographers. Beautiful galleries, easy client sharing, and transparent pricing designed for creative professionals.*

**Keywords to seed:** photographer file sharing, photo gallery hosting, client photo delivery, photography workflow tools, photo sharing for photographers.

---

# 13 — Brand applications checklist

* Website: hero, features, security, pricing/donate, docs, community.
* Social avatars: symbol-only SVG in white on primary, and white on beacon for variation.
* Email signature: wordmark + short tagline + link to privacy page.
* Favicons & app icons: export 16/32/48/180 px and an adaptive icon set.
* Print: provide PDF and EPS for t-shirts, banners; include Pantone match if needed.

---

# 14 — Handoff & file organization (for design tool like Figma)

* Create a **single source of truth** file containing: color tokens, typography tokens, spacing/grid tokens, components (buttons, inputs, cards).
* Name components: `Button/Primary/Default`, `Button/Primary/Hover`, etc.
* Include responsive variants and exportable assets (SVGs) per breakpoint.
* Provide an accessibility checklist in the Figma file for devs to test.

---

# 15 — Common mistakes junior designers make — with fixes (important)

1. **Using low-contrast color combinations**

   * Fix: check WCAG contrast early. Default body text must be ≥ 4.5:1 on chosen background.

2. **Overusing accent color (beacon) for large swathes of UI**

   * Fix: use beacon sparingly for CTAs or small decorative elements; keep backgrounds neutral.

3. **Designing at only one breakpoint**

   * Fix: create mobile-first components and test multiple widths. Include long-string/hard-language tests.

4. **Relying only on color to convey meaning (e.g., error vs success)**

   * Fix: pair color with icons and text. Use ARIA-live regions for dynamic updates.

5. **Exporting logos as raster images for web**

   * Fix: export SVG for logos and use PNG only for legacy or raster photos. Provide 2x PNGs for any raster needs.

6. **Ignoring type metrics (tracking / line-height / measure)**

   * Fix: set consistent line-height (1.4–1.6) and limit measure to ~60–75 characters.

7. **Not providing clear interaction states (hover/focus/active)**

   * Fix: design and document focus outlines, hover lifts, active states, and disabled states.

8. **Inconsistent spacing and token usage**

   * Fix: adopt an 8px system and enforce it via tokens/components.

9. **Creating logos that don’t scale**

   * Fix: test logo at 16×16, 32×32, 48×48 — if it’s indecipherable, simplify.

10. **Forgetting accessibility for forms & keyboard users**

    * Fix: ensure labels, focus management, aria attributes, and 44×44 tap targets.

11. **Too many typefaces**

    * Fix: limit to 2 complementary families for brand coherence.

12. **Using trendy UI color palettes that age poorly**

    * Fix: choose timeless neutrals with one memorable accent.

13. **Not testing with real users or failing to test copy in context**

    * Fix: show live copy to users; measure comprehension and tone.

---

# 16 — Implementation examples & snippets

**CSS variables (starter)**

```css
:root{
  --color-primary: #1E5F74;
  --color-beacon:  #F4A259;
  --color-anchor:  #2E2E2E;
  --color-bg:      #F9F7F3;
  --color-white:   #FFFFFF;
  --radius-card: 12px;
  --radius-btn: 8px;
  --space-1: 8px;
  --space-2: 16px;
  --space-3: 24px;
  --max-width: 1200px;
}
body {
  background: var(--color-bg);
  color: var(--color-anchor);
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
}
```

**Primary CTA (complete)**

```css
.btn-primary {
  background: var(--color-primary);
  color: var(--color-white);
  border-radius: var(--radius-btn);
  padding: 12px 20px;
  border: none;
  box-shadow: 0 6px 16px rgba(30,95,116,0.06);
  transition: transform .12s ease, box-shadow .12s ease;
}
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 22px rgba(30,95,116,0.08); }
.btn-primary:focus { outline: 3px solid rgba(244,162,89,0.18); }
```

---

# 17 — Accessibility checklist (must-haves before launch)

* Body text contrast ≥ 4.5:1 against page background.
* Headings tested at responsive sizes.
* All interactive elements keyboard-focusable with visible focus styles.
* Form fields have labels and useful error messages, with aria-attributes.
* Images have descriptive alt text.
* Motion can be reduced (prefers-reduced-motion).
* All CTA buttons use descriptive text (no “Click here”).

---

# 18 — Legal & ops notes

* **Trademark & domain:** check trademark availability for “TheSafeHarbor” and register your domain and social handles asap.
* **Security claims:** only publish statements like “encrypted in transit & at rest” if your implementation provides them. For audits or compliance claims (SOC2, ISO), explicitly document plans.

---

# 19 — Next steps & prioritized checklist

1. Create a Figma file with tokens + components and export a design token JSON.
2. Build a small style guide page (colors, type, buttons, forms) and keep it synced to code.
3. Implement an accessible header & hero on the marketing site. A/B test the tagline.
4. Prepare logo variants and export SVG & PNG 1x/2x.
5. Run an accessibility pass (axe/lighthouse) and manual keyboard testing.
6. Register domain/socials and confirm trademark checks.
7. If nonprofit: draft a short “mission & funding” page to explain your model.

---

# 20 — Quick “Do / Don’t” cheat-sheet

Do:

* Build tokens first (colors, type, spacing).
* Test contrast early.
* Use SVG logos.
* Keep copy short & warm.
* Use spacing consistently.

Don’t:

* Use beacon (`#F4A259`) as body text on light bg.
* Rely only on color to convey info.
* Place logo on busy/low-contrast backgrounds.
* Let microcopy be long and technical.

---

If you want, I can:

* Export the color/typography tokens as a ready-to-use JSON or SCSS file.
* Produce a one-page brand guideline PDF you can hand to contractors.
* Mock up a 1-screen homepage (hero + 3 features + CTA) in HTML/CSS using the tokens above.

Which would you like next?
