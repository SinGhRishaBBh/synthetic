# Design System Documentation: The Luminal Logic

## 1. Overview & Creative North Star
This design system is built to transform complex synthetic data workflows into a high-end, editorial experience. We are moving away from the cluttered, "dashboard-heavy" aesthetic of traditional SaaS and moving toward a philosophy we call **"The Luminal Logic."**

**The Creative North Star: Neural Precision**
The interface should feel like a high-precision instrument emerging from the shadows. By utilizing a deep, monochromatic foundation of charcoal and navy, we allow data and primary actions to "glow" with neon-infused vibrancy. We break the "template" look through:
*   **Intentional Asymmetry:** Using unbalanced whitespace to guide the eye toward a single, primary path.
*   **Tonal Depth:** Replacing rigid lines with shifts in surface luminosity.
*   **Typographic Gravity:** Leveraging the geometric authority of Manrope to create a hierarchy that feels curated, not just functional.

---

## 2. Colors & Surface Philosophy
The palette is rooted in the dark-space aesthetic, utilizing a "Synthetic Navy" base to provide a more sophisticated depth than pure black.

### The "No-Line" Rule
**Borders are a last resort.** To achieve a premium editorial feel, designers are prohibited from using 1px solid lines to separate major sections (e.g., sidebars, headers). Boundaries must be defined solely through background color shifts.
*   **Sidebar/Navigation:** Use `surface-container-low` (#0e1419) against the main `background` (#0a0f14).
*   **Main Content Area:** Use the base `surface` (#0a0f14) to create a sense of infinite "dark space."

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of semi-translucent layers. 
1.  **Level 0 (Base):** `surface` (#0a0f14) - The infinite canvas.
2.  **Level 1 (Sections):** `surface-container-low` (#0e1419) - Used for sidebars or secondary drawers.
3.  **Level 2 (Cards/Modules):** `surface-container` (#141a20) - The standard container for data visualization.
4.  **Level 3 (Interactive Elements):** `surface-container-highest` (#1f262e) - Use this for elements that need to feel closest to the user.

### The Glass & Gradient Rule
To prevent the UI from feeling "flat," main CTAs and floating modals should utilize:
*   **Gradients:** Transition from `primary` (#81ecff) to `primary-container` (#00e3fd) at a 135-degree angle. This adds "visual soul" and a liquid-tech feel.
*   **Glassmorphism:** For floating tooltips or overlays, use `surface-bright` (#252d35) at 60% opacity with a `20px` backdrop-blur.

---

## 3. Typography
We utilize a dual-font strategy to balance technical precision with premium editorial flair.

*   **Display & Headlines (Manrope):** Use Manrope for all `display` and `headline` scales. Its geometric construction feels engineered and modern. For `display-lg`, use a tight letter-spacing (-0.02em) to create a high-impact, "masthead" look.
*   **UI & Body (Inter):** Use Inter for all functional text, titles, and labels. Inter’s high x-height ensures legibility against high-contrast backgrounds.
*   **Hierarchy as Brand:** Use `label-sm` with all-caps and increased tracking (+0.1em) for category headers (e.g., "DATA INGESTION") to evoke a sense of professional authority.

---

## 4. Elevation & Depth
Depth in this system is achieved through **Tonal Layering** rather than traditional structural shadows.

*   **The Layering Principle:** Place a `surface-container-lowest` (#000000) card on a `surface-container-low` (#0e1419) section to create a "recessed" effect. This is more sophisticated than a drop shadow.
*   **Ambient Shadows:** If an element must float (e.g., a modal), use a shadow with a blur of `40px` and an opacity of `8%`. The shadow color should be derived from `on-background` (#eaeef6) to simulate natural light dispersion.
*   **The "Ghost Border" Fallback:** If accessibility requirements demand a border, use the `outline-variant` (#43484e) at **15% opacity**. This creates a "whisper" of a container without breaking the minimal aesthetic.

---

## 5. Components

### Buttons
*   **Primary:** Gradient fill (`primary` to `primary-container`), black text (`on-primary-fixed` #003840). Radius: `md` (0.375rem).
*   **Secondary:** Ghost style. No fill. `Ghost Border` (outline-variant at 20%). Text: `primary` (#81ecff).
*   **Tertiary:** No border, no fill. Text: `secondary` (#c4dcfd). Use for low-priority actions like "Cancel."

### Input Fields
*   **Background:** `surface-container-highest` (#1f262e).
*   **Border:** Use the "Ghost Border" rule. On focus, transition the border to 100% opacity `primary` (#81ecff).
*   **Label:** Use `label-md` (Inter) positioned strictly above the field, never inside.

### Cards & Data Modules
*   **Constraint:** Absolutely no divider lines. 
*   **Spacing:** Use `spacing.8` (2.75rem) to separate internal content blocks.
*   **Header:** Use a subtle background shift to `surface-bright` (#252d35) for the card header to distinguish it from the card body.

### Status Chips
*   **Neon Accents:** For "Active" or "Success," use `primary` text on a `primary-container` background at 10% opacity. This creates a "glow" effect without overpowering the data.

---

## 6. Do's and Don'ts

### Do
*   **Do** embrace "Dark Space." Use `spacing.16` or `spacing.20` between major functional groups to allow the user to focus on a single path.
*   **Do** use Manrope `headline-sm` for section titles to maintain a premium editorial feel.
*   **Do** use subtle backdrop blurs on any element that overlaps another.

### Don't
*   **Don't** use 100% opaque, high-contrast borders. It shatters the "Luminal" aesthetic.
*   **Don't** use standard "drop shadows" (e.g., 0px 4px 10px black). Use the Ambient Shadow guidelines.
*   **Don't** clutter the screen with multiple primary CTAs. This system is designed for a single, clear path. If two buttons are needed, one *must* be Tertiary.
*   **Don't** use pure white text for body copy. Use `on-surface-variant` (#a7abb2) to reduce eye strain and maintain the sophisticated tonal range.