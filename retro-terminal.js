/**
 * RetroTerminal - Modular Web Component (<retro-terminal>)
 * Features:
 * - 100% Shadow DOM encapsulation (no host CSS leak, no terminal CSS pollution)
 * - Clean CSS borders matching the viewer grid style (1px solid #444444)
 * - Monospace typography matching the viewer ("Cascadia Code", "Consolas", etc.)
 * - Muted monochrome palette (#050505 bg, #b0b0b0 fg, #ffffff bright)
 * - Square window dimensions (equal width and height)
 * - Unhighlightable text (user-select: none)
 * - Positioned absolutely so it scrolls naturally with document flow (users can scroll past it)
 * - Draggable header with page-scroll aware pointer math
 * - Static prompt display (user input disabled) with retro blinking cursor
 */

class RetroTerminal extends HTMLElement {
  static get observedAttributes() {
    return ['window-title', 'prompt', 'width', 'height', 'top', 'left'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });

    // Drag & window state
    this.isDragging = false;
    this.isMinimized = false;
    this.dragStartClientX = 0;
    this.dragStartClientY = 0;
    this.lastClientX = 0;
    this.lastClientY = 0;
    this.initialScrollX = 0;
    this.initialScrollY = 0;
    this.initialLeft = 0;
    this.initialTop = 0;
    this.maxDragLeft = Infinity;
    this.maxDragTop = Infinity;
    this.autoScrollRAF = null;
    this._onScroll = this.handleScroll.bind(this);

    this.render();
  }

  connectedCallback() {
    this.setupEventListeners();
    this.setupInitialPosition();
  }

  disconnectedCallback() {
    this.removeEventListeners();
    if (this.autoScrollRAF) {
      cancelAnimationFrame(this.autoScrollRAF);
      this.autoScrollRAF = null;
    }
    window.removeEventListener('scroll', this._onScroll);
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;
    if (name === 'window-title' && this.titleEl) {
      this.titleEl.textContent = newValue;
    }
    if (name === 'prompt' && this.promptEl) {
      this.promptEl.textContent = newValue;
    }
    if (name === 'width' && this.windowEl) {
      this.windowEl.style.width = newValue;
    }
    if (name === 'height' && this.windowEl) {
      this.windowEl.style.height = newValue;
    }
  }

  get terminalTitle() {
    return this.getAttribute('window-title') || 'dungeon-crawler-text';
  }

  get promptSymbol() {
    return this.getAttribute('prompt') || 'loremaster >';
  }

  get terminalWidth() {
    return this.getAttribute('width') || '450px';
  }

  get terminalHeight() {
    return this.getAttribute('height') || '450px';
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: absolute;
          z-index: 1000;
          font-family: "Cascadia Code", "Consolas", "IBM Plex Mono", "Courier New", monospace;
          color: #b0b0b0;
          font-size: 13px;
          line-height: 1.2;
          user-select: none;
          -webkit-user-select: none;
        }

        *, *::before, *::after {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
          border-radius: 0 !important;
          box-shadow: none !important;
          user-select: none !important;
          -webkit-user-select: none !important;
        }

        /* Terminal Window Container */
        .terminal-window {
          position: relative;
          background: #050505;
          color: #b0b0b0;
          display: flex;
          flex-direction: column;
          border: 1px solid #444444;
          overflow: hidden;
          width: ${this.terminalWidth};
          height: ${this.terminalHeight};
          min-width: 260px;
          min-height: 260px;
          max-width: 98vw;
          box-shadow: 0 0 12px rgba(0,0,0,0.8) !important;
        }

        /* Minimized state */
        .terminal-window.minimized {
          height: auto !important;
          min-height: 0 !important;
        }

        .terminal-window.minimized .content-area {
          display: none !important;
        }

        /* ── Header Row (Title bar & Decorative Window Controls) ── */
        .header-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: #0e0e0e;
          border-bottom: 1px solid #444444;
          padding: 4px 12px;
          cursor: default;
          user-select: none;
          flex-shrink: 0;
        }

        .box-title {
          color: #ffffff;
          font-weight: 700;
          letter-spacing: 1px;
          font-size: 0.78rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .box-btn-group {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-shrink: 0;
        }

        /* Bracketed retro buttons */
        .box-btn {
          background: transparent;
          border: none;
          color: #b0b0b0;
          font-family: inherit;
          font-size: 13px;
          line-height: 1;
          cursor: default;
          padding: 0 2px;
          margin: 0;
          user-select: none;
        }

        .box-btn:hover {
          background: #e0e0e0;
          color: #0a0a0a;
        }

        .box-btn:active {
          background: #ffffff;
          color: #000000;
        }

        /* ── Terminal Content Area ── */
        .content-area {
          flex: 1;
          padding: 8px 12px;
          min-width: 0;
          display: flex;
          flex-direction: column;
          position: relative;
          background: #050505;
          overflow: hidden;
        }

        .terminal-scroll-area {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
          display: flex;
          flex-direction: column;
          user-select: none !important;
          -webkit-user-select: none !important;
        }

        /* Retro scrollbars */
        .terminal-scroll-area::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        .terminal-scroll-area::-webkit-scrollbar-track {
          background: #050505;
          border-left: 1px solid #222222;
        }
        .terminal-scroll-area::-webkit-scrollbar-thumb {
          background: #444444;
        }
        .terminal-scroll-area::-webkit-scrollbar-thumb:hover {
          background: #606060;
        }

        /* Active Prompt Row (Static - no user typing) */
        .input-row {
          display: flex;
          align-items: baseline;
          flex-wrap: wrap;
          margin-top: 2px;
          line-height: 1.3;
          user-select: none !important;
          -webkit-user-select: none !important;
        }

        .prompt-label {
          color: #ffffff;
          font-weight: 700;
          margin-right: 6px;
          flex-shrink: 0;
          user-select: none !important;
        }

        /* Blinking text cursor */
        .cursor {
          display: inline-block;
          color: #ffffff;
          font-weight: 700;
          margin-left: 1px;
          animation: retro-cursor-blink 1s steps(1) infinite;
          user-select: none !important;
        }

        @keyframes retro-cursor-blink {
          0%, 49% {
            opacity: 1;
          }
          50%, 100% {
            opacity: 0;
          }
        }
      </style>

      <div class="terminal-window" id="window">
        <!-- 1. Top Header Row -->
        <div class="header-row" id="dragHandle">
          <div class="box-title" id="title">${this.terminalTitle}</div>
          <div class="box-btn-group">
            <button class="box-btn btn-min" id="btnMin" aria-label="Minimize">[_]</button>
            <button class="box-btn btn-close" id="btnClose" aria-label="Close">[X]</button>
          </div>
        </div>

        <!-- 2. Middle Content Row (Static prompt display) -->
        <div class="content-area" id="contentArea">
          <div class="terminal-scroll-area">
            <div class="input-row">
              <span class="prompt-label" id="promptLabel">${this.promptSymbol}&nbsp;</span>
              <span class="cursor">|</span>
            </div>
          </div>
        </div>
      </div>
    `;

    // Cache elements
    this.windowEl = this.shadowRoot.getElementById('window');
    this.dragHandle = this.shadowRoot.getElementById('dragHandle');
    this.titleEl = this.shadowRoot.getElementById('title');
    this.promptEl = this.shadowRoot.getElementById('promptLabel');
    this.btnMin = this.shadowRoot.getElementById('btnMin');
    this.btnClose = this.shadowRoot.getElementById('btnClose');
  }

  setupInitialPosition() {
    const customTop = this.getAttribute('top') || '60px';
    const customLeft = this.getAttribute('left') || '60px';
    this.style.top = customTop;
    this.style.left = customLeft;
  }

  setupEventListeners() {
    // Window dragging with Pointer Events (document scroll aware)
    this._onPointerDown = this.handlePointerDown.bind(this);
    this._onPointerMove = this.handlePointerMove.bind(this);
    this._onPointerUp = this.handlePointerUp.bind(this);

    this.dragHandle.addEventListener('pointerdown', this._onPointerDown);
    this.dragHandle.addEventListener('pointermove', this._onPointerMove);
    this.dragHandle.addEventListener('pointerup', this._onPointerUp);
    this.dragHandle.addEventListener('pointercancel', this._onPointerUp);

    // Minimize & Close button controls
    this.btnMin.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMinimize();
    });

    this.btnClose.addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeTerminal();
    });
  }

  removeEventListeners() {
    if (this.dragHandle) {
      this.dragHandle.removeEventListener('pointerdown', this._onPointerDown);
      this.dragHandle.removeEventListener('pointermove', this._onPointerMove);
      this.dragHandle.removeEventListener('pointerup', this._onPointerUp);
      this.dragHandle.removeEventListener('pointercancel', this._onPointerUp);
    }
  }

  /* ── Drag & Reposition Logic (Scroll-aware & Auto-scroll) ── */
  handlePointerDown(e) {
    if (e.target.closest('.box-btn')) return;

    this.isDragging = true;
    this.dragHandle.setPointerCapture(e.pointerId);

    // Track viewport client coordinates
    this.dragStartClientX = e.clientX;
    this.dragStartClientY = e.clientY;
    this.lastClientX = e.clientX;
    this.lastClientY = e.clientY;

    // Track scroll positions at drag start
    this.initialScrollX = window.scrollX;
    this.initialScrollY = window.scrollY;

    this.initialLeft = parseFloat(this.style.left) || this.offsetLeft;
    this.initialTop = parseFloat(this.style.top) || this.offsetTop;

    // Calculate document limits at start of drag to prevent infinite page expansion
    const termWidth = this.windowEl ? this.windowEl.offsetWidth : (this.offsetWidth || 450);
    const termHeight = this.windowEl ? this.windowEl.offsetHeight : (this.offsetHeight || 450);
    const docWidth = Math.max(
      document.body.scrollWidth, document.documentElement.scrollWidth,
      document.body.offsetWidth, document.documentElement.offsetWidth
    );
    const docHeight = Math.max(
      document.body.scrollHeight, document.documentElement.scrollHeight,
      document.body.offsetHeight, document.documentElement.offsetHeight
    );

    this.maxDragLeft = Math.max(0, docWidth - termWidth);
    this.maxDragTop = Math.max(0, docHeight - termHeight);

    window.addEventListener('scroll', this._onScroll, { passive: true });
    this.startAutoScroll();

    e.preventDefault();
  }

  handlePointerMove(e) {
    if (!this.isDragging) return;

    this.lastClientX = e.clientX;
    this.lastClientY = e.clientY;

    this.updateDragPosition();
  }

  handleScroll() {
    if (!this.isDragging) return;
    this.updateDragPosition();
  }

  updateDragPosition() {
    const dx = this.lastClientX - this.dragStartClientX;
    const dy = this.lastClientY - this.dragStartClientY;
    const scrollDeltaX = window.scrollX - this.initialScrollX;
    const scrollDeltaY = window.scrollY - this.initialScrollY;

    let nextLeft = this.initialLeft + dx + scrollDeltaX;
    let nextTop = this.initialTop + dy + scrollDeltaY;

    // Boundary protection: clamp to document limits so terminal cannot stretch page infinitely
    nextLeft = Math.max(0, Math.min(nextLeft, this.maxDragLeft));
    nextTop = Math.max(0, Math.min(nextTop, this.maxDragTop));

    this.style.left = `${nextLeft}px`;
    this.style.top = `${nextTop}px`;
  }

  startAutoScroll() {
    if (this.autoScrollRAF) {
      cancelAnimationFrame(this.autoScrollRAF);
    }

    const checkScroll = () => {
      if (!this.isDragging) return;

      const edgeThreshold = 60;
      const scrollSpeed = 14;
      const maxScrollY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      const maxScrollX = Math.max(0, document.documentElement.scrollWidth - window.innerWidth);

      if (this.lastClientY < edgeThreshold) {
        // Dragging near top edge: scroll screen up
        if (window.scrollY > 0) {
          window.scrollBy(0, -scrollSpeed);
          this.updateDragPosition();
        }
      } else if (this.lastClientY > window.innerHeight - edgeThreshold) {
        // Dragging near bottom edge: scroll screen down only if not at the bottom of the document
        if (window.scrollY < maxScrollY) {
          window.scrollBy(0, scrollSpeed);
          this.updateDragPosition();
        }
      }

      if (this.lastClientX < edgeThreshold) {
        // Dragging near left edge: scroll screen left
        if (window.scrollX > 0) {
          window.scrollBy(-scrollSpeed, 0);
          this.updateDragPosition();
        }
      } else if (this.lastClientX > window.innerWidth - edgeThreshold) {
        // Dragging near right edge: scroll screen right
        if (window.scrollX < maxScrollX) {
          window.scrollBy(scrollSpeed, 0);
          this.updateDragPosition();
        }
      }

      this.autoScrollRAF = requestAnimationFrame(checkScroll);
    };

    this.autoScrollRAF = requestAnimationFrame(checkScroll);
  }

  handlePointerUp(e) {
    if (this.isDragging) {
      this.isDragging = false;
      if (this.autoScrollRAF) {
        cancelAnimationFrame(this.autoScrollRAF);
        this.autoScrollRAF = null;
      }
      window.removeEventListener('scroll', this._onScroll);
      try {
        this.dragHandle.releasePointerCapture(e.pointerId);
      } catch (_) {}
    }
  }

  /* ── Window Controls ── */
  toggleMinimize() {
    this.isMinimized = !this.isMinimized;
    if (this.isMinimized) {
      this.windowEl.classList.add('minimized');
      this.btnMin.textContent = '[+]';
      this.btnMin.setAttribute('aria-label', 'Restore');
    } else {
      this.windowEl.classList.remove('minimized');
      this.btnMin.textContent = '[_]';
      this.btnMin.setAttribute('aria-label', 'Minimize');
    }
  }

  closeTerminal() {
    // Completely teardown and remove element from DOM
    this.remove();
  }
}

// Register Custom Element
if (!customElements.get('retro-terminal')) {
  customElements.define('retro-terminal', RetroTerminal);
}

// Optional export for module-based bundlers
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RetroTerminal };
}

/* ==============================================================================
   HOW TO SPAWN THIS TERMINAL IN OTHER PROJECTS (Agent Implementation Guide)
   ==============================================================================
   The <retro-terminal> is a zero-dependency, self-contained native Web Component.
   
   1. SCRIPT INCLUSION:
      Include this script in your HTML:
      <script src="path/to/retro-terminal.js"></script>

   2. HTML DECLARATIVE USAGE:
      <retro-terminal 
        window-title="dungeon-crawler-text" 
        prompt="loremaster >" 
        width="450px" 
        height="450px" 
        top="100px" 
        left="100px">
      </retro-terminal>

   3. PROGRAMMATIC JAVASCRIPT SPAWNING (Single Instance / Anti-Duplicate):
      Use this helper function to dynamically spawn the terminal anywhere:

      function spawnTerminal(config = {}) {
        // Enforce singleton: prevent duplicate terminal instances
        if (document.querySelector('retro-terminal')) {
          console.warn('[RetroTerminal] Instance already exists on page.');
          return null;
        }

        const term = document.createElement('retro-terminal');

        // Optional attributes & defaults
        term.setAttribute('window-title', config.title || 'dungeon-crawler-text');
        term.setAttribute('prompt', config.prompt || 'loremaster >');
        term.setAttribute('width', config.width || '450px');
        term.setAttribute('height', config.height || '450px');
        term.setAttribute('left', config.left || '60px');
        // If top is omitted, spawn 60px below current viewport scroll
        term.setAttribute('top', config.top || `${window.scrollY + 60}px`);

        document.body.appendChild(term);
        return term;
      }

   4. TEARDOWN / KILL:
      The terminal's [X] button automatically calls `this.remove()` to destroy itself.
      To programmatically close it from outside code:
      const existing = document.querySelector('retro-terminal');
      if (existing) existing.remove();
   ============================================================================== */

