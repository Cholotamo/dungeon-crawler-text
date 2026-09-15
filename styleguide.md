# Retro CLI & Terminal UI Styleguide

**Purpose:** This document defines the strict "Retro CLI / ASCII Terminal" visual aesthetic. Provide this styleguide to AI agents in future projects to ensure they generate frontends that perfectly replicate this immersive, text-based UI/UX.

---

## 1. Core Philosophy & Vibe
- **Immersion First:** The interface must feel like a legacy mainframe, an MS-DOS prompt, or a classic MUD/roguelike. 
- **No Modern OS UI:** Absolutely no native HTML tooltips, standard browser scrollbars, rounded corners (border-radius: 0), or drop shadows.
- **Text as UI:** UI elements (buttons, tabs, dividers) are constructed using text characters, brackets, and ASCII line-drawing glyphs.

## 2. Typography & Colors
- **Font Family:** Strictly Monospace. `font-family: 'Courier New', Courier, monospace;` (or 'Fira Code', 'Consolas').
- **Line Height:** Tight and controlled. `1.0` to `1.2` for grids, up to `1.5` for reading text (lore/logs).
- **Base Palette:**
  - **Background:** Deep black (`#0a0a0a` or `#000000`).
  - **Foreground (Text):** Off-white, silver, or amber (`#c0c0c0`, `#e0e0e0`, `#ffd166`).
- **Highlights & Accents:**
  - Use high-contrast terminal colors for accents: Cyan (`#00ffff`), Green (`#38a169`), Red (`#ff3860`), Gold (`#ff9f1c`).
  - **Active/Hover States:** Instead of subtle color shifts, use **inverse styling** (e.g., swap background and foreground colors: `bg: white, fg: black`) or wrap text in indicator glyphs (e.g., `> TEXT <`).

## 3. Dynamic ASCII Borders (The Flexbox Method)
Never use fixed string lengths (e.g., `"-".repeat(50)`) for ASCII borders, as they break on window resize. Instead, use a fluid CSS Flexbox architecture for perfect, responsive ASCII box-drawing.

**HTML Structure:**
```html
<div class="cli-panel">
  <!-- Top Border -->
  <div class="box-row">
    <span class="box-corner">┌</span>
    <span class="box-h-line"></span>
    <span class="box-corner">┐</span>
  </div>
  <!-- Middle Content -->
  <div class="box-row middle">
    <span class="box-v-line">│</span>
    <div class="box-content"> Your content here </div>
    <span class="box-v-line">│</span>
  </div>
  <!-- Bottom Border -->
  <div class="box-row">
    <span class="box-corner">└</span>
    <span class="box-h-line"></span>
    <span class="box-corner">┘</span>
  </div>
</div>
```

**Required CSS:**
```css
.box-row { display: flex; width: 100%; align-items: stretch; }
.box-corner, .box-v-line { flex-shrink: 0; width: 1ch; text-align: center; }
/* The magic: stretches to fill space, hides overflow of repeated dashes */
.box-h-line { flex: 1; min-width: 0; overflow: hidden; white-space: nowrap; }
.box-h-line::before { content: "────────────────────────────────────────────────────────────────────────────────────────────────────"; }
.box-content { flex: 1; padding: 0 8px; min-width: 0; }
```

## 4. UI Components & Patterns

### 4.1. Buttons & Tabs
- Format clickable elements with brackets: `[WORLD MAP]` or `< SUBMIT >`.
- **Hover:** Inverse the colors or change text color to a bright accent.
- **Active Tab:** Denoted by a visual shift, such as asterisks `[ * WORLD MAP * ]` or high-contrast inverse colors.

### 4.2. Tooltips
- **CRITICAL RULE:** Never use the native HTML `title="..."` attribute. It ruins the terminal immersion with a white OS-level popup.
- **Custom Tooltips:** Use a hidden `<div>` with `position: fixed`, strict monochrome borders (e.g., `border: 1px solid #555`), and update its `left`/`top` properties via JavaScript `mousemove` events to follow the cursor tightly.

### 4.3. Grids & Matrices (Maps/Data)
- Ensure a perfect 1:1 aspect ratio for grid cells using CSS (e.g., `width: 12px; height: 12px; text-align: center; line-height: 12px; display: inline-block;`).
- Layer backgrounds and foregrounds explicitly to create colorful terminal graphics.

### 4.4. Scrollbars
- Hide default scrollbars to maintain the illusion of a terminal buffer.
```css
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0a0a; border-left: 1px solid #333; }
::-webkit-scrollbar-thumb { background: #444; }
::-webkit-scrollbar-thumb:hover { background: #888; }
```

## 5. The CRT Effect
To complete the aesthetic, apply a subtle CSS scanline overlay to the entire body. It should be pointer-event transparent so it doesn't block clicks.

```css
body::after {
  content: "";
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0),
    rgba(255, 255, 255, 0) 50%,
    rgba(0, 0, 0, 0.1) 50%,
    rgba(0, 0, 0, 0.1)
  );
  background-size: 100% 4px; /* Adjust thickness of scanlines */
  pointer-events: none; /* Let clicks pass through */
  z-index: 9999;
}
```

## 6. Prompting Future Agents
When requesting a frontend in future projects, include the following in your prompt:
> *"Please read \`styleguide.md\` before generating the UI. Build the frontend strictly adhering to the Retro CLI/Terminal aesthetic described there. Ensure you use the Flexbox ASCII border technique for panels, strip all native HTML \`title\` tooltips in favor of custom cursor-following divs, and apply the CRT scanline effect."*
