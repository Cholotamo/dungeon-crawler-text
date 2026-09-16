/**
 * RetroTerminal - Modular Web Component (<retro-terminal>)
 * Strictly adheres to styleguide.md:
 * - 100% Shadow DOM encapsulation (no host CSS leak, no terminal CSS pollution)
 * - Dynamic ASCII Box-drawing Flexbox borders (┌, ─, ┐, │, └, ┘)
 * - Monospace typography & deep black #0a0a0a background
 * - Inverted button hover states, zero border-radius, no drop shadows
 * - Scoped CRT scanline overlay
 * - Draggable window with viewport bounds clamping
 * - Blinking retro cursor and interactive terminal buffer
 */

class RetroTerminal extends HTMLElement {
  static get observedAttributes() {
    return ['title', 'prompt', 'width', 'height', 'top', 'left', 'user', 'host'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });

    // Internal state
    this.commandHistory = [];
    this.historyIndex = -1;
    this.currentInput = '';
    this.isMinimized = false;

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
    if (name === 'title' && this.titleEl) {
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
    return this.getAttribute('title') || 'cholo@portfolio:~';
  }

  get promptSymbol() {
    return this.getAttribute('prompt') || 'cholo>';
  }

  get terminalWidth() {
    return this.getAttribute('width') || '560px';
  }

  get terminalHeight() {
    return this.getAttribute('height') || '360px';
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: fixed;
          z-index: 9999;
          font-family: 'Courier New', Courier, Consolas, 'Lucida Console', monospace;
          color: #c0c0c0;
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
        }

        /* Terminal Window Container */
        .terminal-window {
          position: fixed;
          background: #0a0a0a;
          color: #c0c0c0;
          display: flex;
          flex-direction: column;
          border-radius: 0;
          overflow: hidden;
          width: ${this.terminalWidth};
          height: ${this.terminalHeight};
          min-width: 300px;
          min-height: 180px;
          max-width: 98vw;
          max-height: 98vh;
        }

        /* Minimized state */
        .terminal-window.minimized {
          height: auto !important;
          min-height: 0 !important;
        }

        .terminal-window.minimized .box-row.middle,
        .terminal-window.minimized .box-row.bottom {
          display: none !important;
        }

        /* ── Dynamic ASCII Borders (Flexbox Architecture from styleguide.md) ── */
        .box-row {
          display: flex;
          width: 100%;
          align-items: stretch;
          flex-shrink: 0;
          background: #0a0a0a;
        }

        .box-row.middle {
          flex: 1;
          min-height: 0;
        }

        .box-corner {
          flex-shrink: 0;
          width: 1ch;
          text-align: center;
          color: #888888;
        }

        .box-h-line {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          white-space: nowrap;
          color: #888888;
        }

        .box-h-line::before {
          content: "────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────";
        }

        /* Vertical borders with repeating ASCII line characters */
        .box-v-line {
          flex-shrink: 0;
          width: 1ch;
          text-align: center;
          color: #888888;
          position: relative;
          overflow: hidden;
          line-height: 1.0;
        }

        .box-v-line::before {
          content: "│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A│\\A";
          white-space: pre;
          display: block;
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          text-align: center;
        }

        /* ── Header Row (Title bar & Window Controls) ── */
        .header-row {
          cursor: grab;
          user-select: none;
          background: #0a0a0a;
        }

        .header-row:active {
          cursor: grabbing;
        }

        .box-title-prefix,
        .box-title-suffix {
          color: #555555;
          flex-shrink: 0;
        }

        .box-title {
          color: #00ffff; /* Cyan accent */
          font-weight: bold;
          flex-shrink: 0;
          padding: 0 2px;
          letter-spacing: 0.5px;
        }

        .box-btn-group {
          display: flex;
          align-items: center;
          flex-shrink: 0;
        }

        /* Bracketed retro buttons from styleguide.md 4.1 */
        .box-btn {
          background: transparent;
          border: none;
          color: #c0c0c0;
          font-family: inherit;
          font-size: 13px;
          line-height: 1;
          cursor: pointer;
          padding: 0 3px;
          margin: 0;
          border-radius: 0;
          user-select: none;
          transition: none;
        }

        /* Inverted hover style from styleguide.md */
        .box-btn:hover {
          background: #e0e0e0;
          color: #0a0a0a;
        }

        .box-btn:active {
          background: #38a169;
          color: #0a0a0a;
        }

        .box-btn.btn-close:hover {
          background: #ff3860;
          color: #000000;
        }

        /* ── Terminal Content Area ── */
        .box-content {
          flex: 1;
          padding: 6px 10px;
          min-width: 0;
          display: flex;
          flex-direction: column;
          position: relative;
          background: #0a0a0a;
          overflow: hidden;
        }

        .terminal-scroll-area {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
          display: flex;
          flex-direction: column;
          user-select: text;
          -webkit-user-select: text;
        }

        /* Retro scrollbars from styleguide.md 4.4 */
        .terminal-scroll-area::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        .terminal-scroll-area::-webkit-scrollbar-track {
          background: #0a0a0a;
          border-left: 1px solid #333333;
        }
        .terminal-scroll-area::-webkit-scrollbar-thumb {
          background: #444444;
        }
        .terminal-scroll-area::-webkit-scrollbar-thumb:hover {
          background: #888888;
        }

        /* Status & Welcome Banner */
        .banner-text {
          color: #888888;
          margin-bottom: 8px;
          line-height: 1.3;
        }

        .banner-accent {
          color: #ffd166; /* Amber accent */
        }

        .banner-green {
          color: #38a169;
        }

        .output-line {
          color: #e0e0e0;
          line-height: 1.35;
          margin-bottom: 2px;
          word-break: break-all;
          white-space: pre-wrap;
        }

        .output-line.system {
          color: #888888;
        }
        .output-line.success {
          color: #38a169;
        }
        .output-line.error {
          color: #ff3860;
        }
        .output-line.info {
          color: #00ffff;
        }
        .output-line.highlight {
          color: #ffd166;
        }

        /* Active Command Input Line */
        .input-row {
          display: flex;
          align-items: baseline;
          flex-wrap: wrap;
          margin-top: 4px;
          line-height: 1.3;
        }

        .prompt-label {
          color: #38a169; /* Retro terminal green */
          font-weight: bold;
          margin-right: 6px;
          flex-shrink: 0;
        }

        .cmd-text {
          color: #e0e0e0;
          white-space: pre-wrap;
          word-break: break-all;
        }

        /* Blinking text cursor */
        .cursor {
          display: inline-block;
          color: #00ffff; /* Cyan retro cursor */
          font-weight: 700;
          margin-left: 1px;
          animation: retro-cursor-blink 1s steps(1) infinite;
        }

        @keyframes retro-cursor-blink {
          0%, 49% {
            opacity: 1;
          }
          50%, 100% {
            opacity: 0;
          }
        }

        /* Invisible real input to capture keyboard events */
        .hidden-keyboard-sink {
          position: absolute;
          opacity: 0;
          width: 1px;
          height: 1px;
          top: 0;
          left: 0;
          pointer-events: none;
          border: none;
          outline: none;
        }

        /* Footer status bar */
        .bottom-status {
          color: #555555;
          flex-shrink: 0;
          font-size: 11px;
        }

        .bottom-status-text {
          color: #38a169;
          font-size: 11px;
        }

        /* ── Scoped CRT Scanline Overlay from styleguide.md 5 ── */
        .crt-overlay {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(
            to bottom,
            rgba(255, 255, 255, 0),
            rgba(255, 255, 255, 0) 50%,
            rgba(0, 0, 0, 0.28) 50%,
            rgba(0, 0, 0, 0.28)
          );
          background-size: 100% 4px;
          pointer-events: none;
          z-index: 100;
        }
      </style>

      <div class="terminal-window" id="window">
        <!-- Scoped CRT Scanline Layer -->
        <div class="crt-overlay" aria-hidden="true"></div>

        <!-- Hidden input for mobile keyboard and desktop focus -->
        <input type="text" class="hidden-keyboard-sink" id="keyboardSink" autocomplete="off" spellcheck="false" />

        <!-- 1. Top Header Row with ASCII Box Border -->
        <div class="box-row header-row" id="dragHandle">
          <span class="box-corner">┌</span>
          <span class="box-title-prefix">─[</span>
          <span class="box-title" id="title">${this.terminalTitle}</span>
          <span class="box-title-suffix">]─</span>
          <span class="box-h-line"></span>
          <div class="box-btn-group">
            <button class="box-btn btn-min" id="btnMin" aria-label="Minimize">[_]</button>
            <button class="box-btn btn-close" id="btnClose" aria-label="Close">[X]</button>
          </div>
          <span class="box-corner">┐</span>
        </div>

        <!-- 2. Middle Content Row with ASCII Vertical Borders -->
        <div class="box-row middle">
          <span class="box-v-line">│</span>
          <div class="box-content" id="contentArea">
            <div class="terminal-scroll-area" id="scrollArea">
              <!-- Initial Welcome Banner -->
              <div class="banner-text">
                <div>CHOLO-OS v1.0.4 (tty-retro)</div>
                <div>Type <span class="banner-accent">'help'</span> for simulated commands, or click and start typing.</div>
                <div class="banner-green">System status: ONLINE [READY]</div>
                <div>--------------------------------------------------</div>
              </div>

              <!-- Output History Container -->
              <div id="historyLog"></div>

              <!-- Active Prompt Row -->
              <div class="input-row">
                <span class="prompt-label" id="promptLabel">${this.promptSymbol}&nbsp;</span>
                <span class="cmd-text" id="cmdText"></span>
                <span class="cursor">|</span>
              </div>
            </div>
          </div>
          <span class="box-v-line">│</span>
        </div>

        <!-- 3. Bottom Row with ASCII Box Border -->
        <div class="box-row bottom">
          <span class="box-corner">└</span>
          <span class="box-h-line"></span>
          <span class="bottom-status">─[ <span class="bottom-status-text">PORTFOLIO DEMO</span> ]─</span>
          <span class="box-corner">┘</span>
        </div>
      </div>
    `;

    // Cache elements
    this.windowEl = this.shadowRoot.getElementById('window');
    this.dragHandle = this.shadowRoot.getElementById('dragHandle');
    this.titleEl = this.shadowRoot.getElementById('title');
    this.promptEl = this.shadowRoot.getElementById('promptLabel');
    this.cmdText = this.shadowRoot.getElementById('cmdText');
    this.historyLog = this.shadowRoot.getElementById('historyLog');
    this.scrollArea = this.shadowRoot.getElementById('scrollArea');
    this.contentArea = this.shadowRoot.getElementById('contentArea');
    this.keyboardSink = this.shadowRoot.getElementById('keyboardSink');
    this.btnMin = this.shadowRoot.getElementById('btnMin');
    this.btnClose = this.shadowRoot.getElementById('btnClose');
  }

  setupInitialPosition() {
    const customTop = this.getAttribute('top') || '60px';
    const customLeft = this.getAttribute('left') || '60px';
    this.windowEl.style.top = customTop;
    this.windowEl.style.left = customLeft;
  }

  setupEventListeners() {
    // Window dragging with Pointer Events
    this._onPointerDown = this.handlePointerDown.bind(this);
    this._onPointerMove = this.handlePointerMove.bind(this);
    this._onPointerUp = this.handlePointerUp.bind(this);

    this.dragHandle.addEventListener('pointerdown', this._onPointerDown);
    this.dragHandle.addEventListener('pointermove', this._onPointerMove);
    this.dragHandle.addEventListener('pointerup', this._onPointerUp);
    this.dragHandle.addEventListener('pointercancel', this._onPointerUp);

    // Minimize & Close buttons
    this.btnMin.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleMinimize();
    });

    this.btnClose.addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeOrReset();
    });

    // Content focus
    this.contentArea.addEventListener('click', () => {
      this.focusInput();
    });

    // Keyboard handling
    this._onKeyDown = this.handleKeyDown.bind(this);
    window.addEventListener('keydown', this._onKeyDown);

    // Sync from mobile keyboard sink if needed
    this.keyboardSink.addEventListener('input', () => {
      this.currentInput = this.keyboardSink.value;
      this.updateInputDisplay();
    });
  }

  removeEventListeners() {
    if (this.dragHandle) {
      this.dragHandle.removeEventListener('pointerdown', this._onPointerDown);
      this.dragHandle.removeEventListener('pointermove', this._onPointerMove);
      this.dragHandle.removeEventListener('pointerup', this._onPointerUp);
      this.dragHandle.removeEventListener('pointercancel', this._onPointerUp);
    }
    window.removeEventListener('keydown', this._onKeyDown);
  }

  focusInput() {
    this.keyboardSink.value = this.currentInput;
    this.keyboardSink.focus();
  }

  /* ── Drag & Reposition Logic ── */
  handlePointerDown(e) {
    if (e.target.closest('.box-btn')) return;

    this.isDragging = true;
    this.dragHandle.setPointerCapture(e.pointerId);

    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;

    const rect = this.windowEl.getBoundingClientRect();
    this.initialLeft = rect.left;
    this.initialTop = rect.top;

    e.preventDefault();
  }

  handlePointerMove(e) {
    if (!this.isDragging) return;

    const dx = e.clientX - this.dragStartX;
    const dy = e.clientY - this.dragStartY;

    let nextLeft = this.initialLeft + dx;
    let nextTop = this.initialTop + dy;

    // Viewport clamping
    const winWidth = this.windowEl.offsetWidth;
    const winHeight = this.windowEl.offsetHeight;
    const maxLeft = Math.max(0, window.innerWidth - winWidth);
    const maxTop = Math.max(0, window.innerHeight - winHeight);

    nextLeft = Math.max(0, Math.min(nextLeft, maxLeft));
    nextTop = Math.max(0, Math.min(nextTop, maxTop));

    this.windowEl.style.left = `${nextLeft}px`;
    this.windowEl.style.top = `${nextTop}px`;
  }

  handlePointerUp(e) {
    if (this.isDragging) {
      this.isDragging = false;
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
      this.scrollToBottom();
    }
  }

  closeOrReset() {
    // When closed in demo, show closed message and allow restore
    if (confirm("Reset terminal session?")) {
      this.clearScreen();
      this.appendOutput("system", "Session reset. Welcome back.");
    }
  }

  /* ── Keyboard & CLI Buffer ── */
  handleKeyDown(e) {
    // Check if terminal is minimized
    if (this.isMinimized) return;

    // Allow standard browser key combos (Ctrl+R, F12, Ctrl+C to copy text if text is selected)
    if (e.ctrlKey || e.metaKey || e.altKey) {
      if (e.key === 'c' && window.getSelection().toString()) {
        return; // Allow copy
      }
      if (e.key === 'l' && e.ctrlKey) {
        e.preventDefault();
        this.clearScreen();
        return;
      }
      return;
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      this.executeCommand(this.currentInput.trim());
      this.currentInput = '';
      this.keyboardSink.value = '';
      this.historyIndex = -1;
      this.updateInputDisplay();
      return;
    }

    if (e.key === 'Backspace') {
      e.preventDefault();
      this.currentInput = this.currentInput.slice(0, -1);
      this.keyboardSink.value = this.currentInput;
      this.updateInputDisplay();
      return;
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (this.commandHistory.length > 0) {
        if (this.historyIndex === -1) {
          this.historyIndex = this.commandHistory.length - 1;
        } else if (this.historyIndex > 0) {
          this.historyIndex--;
        }
        this.currentInput = this.commandHistory[this.historyIndex] || '';
        this.keyboardSink.value = this.currentInput;
        this.updateInputDisplay();
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (this.historyIndex !== -1) {
        if (this.historyIndex < this.commandHistory.length - 1) {
          this.historyIndex++;
          this.currentInput = this.commandHistory[this.historyIndex];
        } else {
          this.historyIndex = -1;
          this.currentInput = '';
        }
        this.keyboardSink.value = this.currentInput;
        this.updateInputDisplay();
      }
      return;
    }

    // Single printable character
    if (e.key.length === 1) {
      e.preventDefault();
      this.currentInput += e.key;
      this.keyboardSink.value = this.currentInput;
      this.updateInputDisplay();
    }
  }

  updateInputDisplay() {
    this.cmdText.textContent = this.currentInput;
    this.scrollToBottom();
  }

  scrollToBottom() {
    requestAnimationFrame(() => {
      if (this.scrollArea) {
        this.scrollArea.scrollTop = this.scrollArea.scrollHeight;
      }
    });
  }

  clearScreen() {
    this.historyLog.innerHTML = '';
    this.currentInput = '';
    this.keyboardSink.value = '';
    this.updateInputDisplay();
  }

  appendOutput(type, text) {
    const line = document.createElement('div');
    line.className = `output-line ${type}`;
    line.textContent = text;
    this.historyLog.appendChild(line);
    this.scrollToBottom();
  }

  appendRawHtml(html) {
    const line = document.createElement('div');
    line.className = 'output-line';
    line.innerHTML = html;
    this.historyLog.appendChild(line);
    this.scrollToBottom();
  }

  executeCommand(rawCmd) {
    // Echo prompt and entered command
    const promptEcho = document.createElement('div');
    promptEcho.className = 'output-line';
    promptEcho.innerHTML = `<span style="color:#38a169;font-weight:bold;">${this.promptSymbol} </span><span>${escapeHtml(rawCmd)}</span>`;
    this.historyLog.appendChild(promptEcho);

    if (!rawCmd) {
      this.scrollToBottom();
      return;
    }

    this.commandHistory.push(rawCmd);
    const cmd = rawCmd.toLowerCase();

    // Built-in commands simulation
    switch (cmd) {
      case 'help':
        this.appendRawHtml(`
          <div style="color: #ffd166; margin-bottom: 2px;">AVAILABLE COMMANDS:</div>
          <div>  <span style="color:#00ffff;">help</span>     - Display available commands</div>
          <div>  <span style="color:#00ffff;">about</span>    - Brief intro for portfolio</div>
          <div>  <span style="color:#00ffff;">skills</span>   - List core competencies</div>
          <div>  <span style="color:#00ffff;">clear</span>    - Clear the terminal screen (or Ctrl+L)</div>
          <div>  <span style="color:#00ffff;">date</span>     - Show current system timestamp</div>
          <div>  <span style="color:#00ffff;">echo [msg]</span>- Print text to screen</div>
        `);
        break;

      case 'about':
        this.appendRawHtml(`
          <div style="color:#00ffff; font-weight:bold;">[ ABOUT THE DEVELOPER ]</div>
          <div>Crafting high-immersion retro CLI interfaces & full-stack web applications.</div>
          <div>Specialized in modular components, clean architectures, and custom UI/UX.</div>
        `);
        break;

      case 'skills':
        this.appendRawHtml(`
          <div style="color:#38a169; font-weight:bold;">[ TECHNICAL SKILLS ]</div>
          <div>* Languages: JavaScript, TypeScript, Python, HTML5/CSS3</div>
          <div>* Architecture: Web Components, Shadow DOM, Micro-frontends</div>
          <div>* Aesthetic: Retro Terminal, ASCII Box Drawing, CRT Simulation</div>
        `);
        break;

      case 'clear':
        this.clearScreen();
        return;

      case 'date':
        this.appendOutput('highlight', new Date().toString());
        break;

      default:
        if (cmd.startsWith('echo ')) {
          this.appendOutput('default', rawCmd.slice(5));
        } else {
          this.appendOutput('error', `bash: ${rawCmd}: command not found. Type 'help' for commands.`);
        }
        break;
    }

    this.scrollToBottom();
  }
}

// Utility HTML escape
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Register Custom Element
if (!customElements.get('retro-terminal')) {
  customElements.define('retro-terminal', RetroTerminal);
}

// Optional export for module-based bundlers
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RetroTerminal };
}
