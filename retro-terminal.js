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

    // Drag state
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.initialLeft = 0;
    this.initialTop = 0;

    this.render();
  }

  connectedCallback() {
    this.setupEventListeners();
    this.setupInitialPosition();
  }

  disconnectedCallback() {
    this.removeEventListeners();
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

        /* Bracketed retro buttons (purely visual flair) */
        .box-btn {
          background: transparent;
          border: none;
          color: #606060;
          font-family: inherit;
          font-size: 13px;
          line-height: 1;
          cursor: default;
          padding: 0 2px;
          margin: 0;
          user-select: none;
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
            <span class="box-btn" aria-hidden="true">[_]</span>
            <span class="box-btn" aria-hidden="true">[X]</span>
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
  }

  removeEventListeners() {
    if (this.dragHandle) {
      this.dragHandle.removeEventListener('pointerdown', this._onPointerDown);
      this.dragHandle.removeEventListener('pointermove', this._onPointerMove);
      this.dragHandle.removeEventListener('pointerup', this._onPointerUp);
      this.dragHandle.removeEventListener('pointercancel', this._onPointerUp);
    }
  }

  /* ── Drag & Reposition Logic (Page-scroll aware) ── */
  handlePointerDown(e) {
    this.isDragging = true;
    this.dragHandle.setPointerCapture(e.pointerId);

    // Use page coordinates to handle page scrolling smoothly
    this.dragStartX = e.pageX;
    this.dragStartY = e.pageY;

    this.initialLeft = parseFloat(this.style.left) || this.offsetLeft;
    this.initialTop = parseFloat(this.style.top) || this.offsetTop;

    e.preventDefault();
  }

  handlePointerMove(e) {
    if (!this.isDragging) return;

    const dx = e.pageX - this.dragStartX;
    const dy = e.pageY - this.dragStartY;

    let nextLeft = this.initialLeft + dx;
    let nextTop = this.initialTop + dy;

    // Boundary protection: prevent dragging above top or off left of canvas
    nextLeft = Math.max(0, nextLeft);
    nextTop = Math.max(0, nextTop);

    this.style.left = `${nextLeft}px`;
    this.style.top = `${nextTop}px`;
  }

  handlePointerUp(e) {
    if (this.isDragging) {
      this.isDragging = false;
      try {
        this.dragHandle.releasePointerCapture(e.pointerId);
      } catch (_) {}
    }
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
