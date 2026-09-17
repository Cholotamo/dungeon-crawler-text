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

    // Game & Interactive state
    this.gameState = 'BOOT'; // 'BOOT' | 'PRINTING' | 'FINISHED'
    this.isActive = false;
    this.typewriterActive = false;
    this.typewriterTimeout = null;
    this.proseText = `Before the first tongue shaped a name for the earth, and before the tread of mortal feet bruised a single stem of wild clover, the land lay in unbroken communion with its own deep breath. It was an unmeasured expanse of stone, loam, and water, born of ancient cataclysms that had cooled into an immense, rhythmic solitude.

To the high north and east, the world was bound by a jagged wall of mountains—an upheaval of grey gneiss, dark basalt, and folded slate that tore the lower sky into ragged ribbons of cloud. These were not mere hills, but the world’s colossal ribs, thrown up when the crust was yet hot and supple. Their summits were crowned with eternal snowpacks that gleamed with the pale, cold fire of dawn, flanked by ancient paleoglaciers whose blue-veined tongues ground inexorably down through the cirques, chewing granite to flour. Here, above the treeline, the air had the thin, iron taste of newly struck flint. Wind, older than memory, scoured the scree slopes and howled through cyclopean cols, driving plumes of powdered ice across chasms so profound the sun could only ever strike their western rims at midsummer.

From the frozen heart of these heights sprang the realm’s great arterial life. In the warmer months of the temperate cycle, the glaciers wept. Ten thousand rivulets, clear as lens-glass, seeped from beneath the ice-tongues, gathering in high, shale-bottomed tarns that mirrored the empty vault of heaven. From these reservoirs, the water found its fury. It spilled over lip and ledge in roaring ribbons of foam, plunging down tiered precipices into the darkness of colossal gorges split by the planet's cooling.

As these torrents descended, they met, coalesced, and deepened, swollen by the rains that clung to the mountain flanks, until they formed two great sister-rivers—mighty surges of water that functioned as the pulse and pulmonary channels of the entire continent.

The eastern artery was the swifter, cutting a violently direct path through a plateau of layered red sandstone. It had gnawed a canyon a mile deep into the earth’s crust—a dizzying chasm where mist rose perpetually from the thresh of rapids. Down in the canyon bed, the water was a surging jade-green, thick with crushed silt and cold enough to numb the bone. Along its sheer walls, hanging gardens of primordial ferns and liverworts clung to seeps in the rock, fed by the eternal vapor. Great boulders the size of hillocks tumbled through the gorge with underwater thuds like muffled drums, slowly ground to roundness by the river’s merciless muscle.

The western artery was broader, heavier, and more deliberate. Spilling from the mountain roots through a fractured piedmont of rolling, wind-swept hills, it broadened into a majestic, silver-plated channel half a league across. It carried the marrow of the mountains into a primeval basin. Here flourished an unbroken canopy of temperate wilderness: forests of colossal, moss-cloaked hemlocks, deep-barked oaks with boughs broad as alleys, and pale, lichen-streaked birches that shivered at the water’s edge. Beneath this vaulted roof of leaf and needle, the forest floor was a thick, soft mattress of rot and resurrection, where shelf-fungi sprouted like pale moons from the flanks of fallen giants, and the soil was rich and black with the unhurried decay of ten thousand unharvested autumns.

Between the two main watercourses lay a sprawling network of tributaries—lesser capillaries that snaked through the greenwood, carving oxbow lakes, feeding dark, reed-choked marshes, and pooling in wide, glassy sheets of freshwater where the land leveled toward the lowlands. In these drowned clearings, water-lilies spread pads large enough to bear the weight of nesting herons, and the surface was broken only by the dimpling rise of ancient, armored fish or the sudden plunge of an osprey from the grey sky.

To the west, where the plateau sloped gently toward the prevailing winds, the forest gave way to vast, undulating downs—rolling hills of wild rye and fescue that rippled like an inland sea beneath the passage of cloud-shadows. Craggy limestone bluffs erupted through the turf at intervals, resembling the drowned bones of sea-beasts cast ashore when the world was brine. In the hollows of these hills lay misty bogs, smelling of sulfur and damp moss, where peat-water the color of dark ale stood stagnant among cotton-grass and gnarled dwarf willows.

Eventually, leagues south of the mountain wall, the sister-rivers converged. Their coming together was a silent, monstrous meeting of waters, forming a single flood that cleaved the lowland forests before spilling toward the maritime margin.

Here, the realm met the ocean in an untamed, violent drama. The continent did not slip meekly into the sea; it fought it. The coast was a battered barrier of black shale cliffs, basalt sea-stacks, and long, claw-like peninsulas that reached out into the churning foam. Where the great river met the tides, it shattered into a labyrinthine delta—a colossal web of mud-bars, braided channels, and tidal flats where freshwater fought the salt. Storms born in the deep sea swept in unhindered, throwing towers of grey brine against the cliffs and filling the estuarial air with the tang of kelp, ozone, and wet sand.

Above it all, there was no sound but the primordial liturgy of the wild: the grinding groan of the ice in the high cirques, the liquid roar of cataracts, the wind soughing through leagues of nameless branches, and the crash of the surf against unmapped stone. The land waited, vast and complete in its own silence, pregnant with a history that had not yet begun.`;

    this.render();
  }

  connectedCallback() {
    this.setupEventListeners();
    this.setupInitialPosition();
    this.initBootScreen();
  }

  disconnectedCallback() {
    this.removeEventListeners();
    if (this.autoScrollRAF) {
      cancelAnimationFrame(this.autoScrollRAF);
      this.autoScrollRAF = null;
    }
    if (this.typewriterTimeout) {
      clearTimeout(this.typewriterTimeout);
      this.typewriterTimeout = null;
    }
    this.typewriterActive = false;
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
          color: #777777;
          font-weight: 700;
          letter-spacing: 1px;
          font-size: 0.78rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          transition: color 0.15s ease;
        }

        .terminal-window.active .box-title {
          color: #ffffff;
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

        /* Hidden command input to capture keyboard events & mobile typing */
        .hidden-cmd-input {
          position: absolute;
          top: 0;
          left: 0;
          width: 0;
          height: 0;
          opacity: 0;
          padding: 0;
          margin: 0;
          border: none;
          outline: none;
          pointer-events: none;
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

        /* Output container for ASCII art, prose, and log history */
        .output-container {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .ascii-box {
          font-family: inherit;
          white-space: pre;
          color: #b0b0b0;
          margin: 4px 0 12px 0;
          line-height: 1.2;
          user-select: none !important;
          -webkit-user-select: none !important;
        }

        /* Slow, sharp step-blink without gradient/fade */
        .boot-prompt {
          color: #b0b0b0;
          font-size: 13px;
          margin-bottom: 8px;
          user-select: none !important;
          animation: boot-blink 1.4s steps(1) infinite;
        }

        @keyframes boot-blink {
          0%, 49% {
            opacity: 1;
          }
          50%, 100% {
            opacity: 0;
          }
        }

        .prose-block {
          margin: 4px 0 12px 0;
          line-height: 1.5;
          color: #b0b0b0;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .prose-speaker {
          color: #ffffff;
          font-weight: 700;
          margin-right: 6px;
        }

        .prose-text {
          color: #cccccc;
          white-space: pre-wrap;
        }

        .log-row {
          display: flex;
          align-items: baseline;
          margin-bottom: 4px;
          line-height: 1.3;
        }

        .input-text {
          color: #ffffff;
          white-space: pre-wrap;
          word-break: break-all;
        }

        /* Active Prompt Row */
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

        /* Text cursor - blinks only when active */
        .cursor {
          display: inline-block;
          color: #ffffff;
          font-weight: 700;
          margin-left: 1px;
          opacity: 0;
          user-select: none !important;
        }

        .terminal-window.active .cursor {
          opacity: 1;
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
      </style>

      <div class="terminal-window" id="window">
        <!-- Hidden input to capture focus & keystrokes -->
        <input type="text" class="hidden-cmd-input" id="cmdInput" autocomplete="off" spellcheck="false" aria-label="Terminal Input">

        <!-- 1. Top Header Row -->
        <div class="header-row" id="dragHandle">
          <div class="box-title" id="title">${this.terminalTitle}</div>
          <div class="box-btn-group">
            <button class="box-btn btn-min" id="btnMin" aria-label="Minimize">[_]</button>
            <button class="box-btn btn-close" id="btnClose" aria-label="Close">[X]</button>
          </div>
        </div>

        <!-- 2. Middle Content Row -->
        <div class="content-area" id="contentArea">
          <div class="terminal-scroll-area" id="scrollArea">
            <div class="output-container" id="outputContainer"></div>
            <div class="input-row" id="inputRow" style="display: none;">
              <span class="prompt-label" id="promptLabel">${this.promptSymbol}&nbsp;</span>
              <span class="input-text" id="inputText"></span>
              <span class="cursor">|</span>
            </div>
          </div>
        </div>
      </div>
    `;

    // Cache elements
    this.windowEl = this.shadowRoot.getElementById('window');
    this.cmdInput = this.shadowRoot.getElementById('cmdInput');
    this.dragHandle = this.shadowRoot.getElementById('dragHandle');
    this.titleEl = this.shadowRoot.getElementById('title');
    this.contentArea = this.shadowRoot.getElementById('contentArea');
    this.scrollArea = this.shadowRoot.getElementById('scrollArea');
    this.outputContainer = this.shadowRoot.getElementById('outputContainer');
    this.inputRow = this.shadowRoot.getElementById('inputRow');
    this.promptEl = this.shadowRoot.getElementById('promptLabel');
    this.inputText = this.shadowRoot.getElementById('inputText');
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

    // Window Activation / Focus on click
    this._onWindowPointerDown = (e) => {
      if (e.target.closest('.box-btn')) return;
      // Prevent browser from stealing focus away from cmdInput on non-input clicks
      if (!e.target.closest('#dragHandle')) {
        e.preventDefault();
      }
      this.activate();
    };
    this.windowEl.addEventListener('pointerdown', this._onWindowPointerDown);

    this._onWindowClick = (e) => {
      if (e.target.closest('.box-btn')) return;
      this.activate();
    };
    this.windowEl.addEventListener('click', this._onWindowClick);

    // Hidden input focus & blur
    this._onCmdFocus = () => {
      this.windowEl.classList.add('active');
      this.isActive = true;
    };
    this._onCmdBlur = () => {
      this.windowEl.classList.remove('active');
      this.isActive = false;
    };
    this.cmdInput.addEventListener('focus', this._onCmdFocus);
    this.cmdInput.addEventListener('blur', this._onCmdBlur);

    // Enter key handling (Starts boot sequence & skips typewriter)
    this._onCmdKeydown = (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.handleEnterKey();
      }
    };
    this.cmdInput.addEventListener('keydown', this._onCmdKeydown);
  }

  removeEventListeners() {
    if (this.dragHandle) {
      this.dragHandle.removeEventListener('pointerdown', this._onPointerDown);
      this.dragHandle.removeEventListener('pointermove', this._onPointerMove);
      this.dragHandle.removeEventListener('pointerup', this._onPointerUp);
      this.dragHandle.removeEventListener('pointercancel', this._onPointerUp);
    }
    if (this.windowEl) {
      if (this._onWindowPointerDown) {
        this.windowEl.removeEventListener('pointerdown', this._onWindowPointerDown);
      }
      if (this._onWindowClick) {
        this.windowEl.removeEventListener('click', this._onWindowClick);
      }
    }
    if (this.cmdInput) {
      this.cmdInput.removeEventListener('focus', this._onCmdFocus);
      this.cmdInput.removeEventListener('blur', this._onCmdBlur);
      this.cmdInput.removeEventListener('keydown', this._onCmdKeydown);
    }
  }

  /* ── Drag & Reposition Logic (Scroll-aware & Auto-scroll) ── */
  handlePointerDown(e) {
    if (e.target.closest('.box-btn')) return;
    this.activate();

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

  /* ── Interactive & Game Flow Methods ── */
  activate() {
    this.cmdInput.focus({ preventScroll: true });
    this.windowEl.classList.add('active');
    this.isActive = true;
  }

  initBootScreen() {
    this.gameState = 'BOOT';
    this.outputContainer.innerHTML = `
      <pre class="ascii-box">
+-----------------------------------+
|                                   |
|         dungeon_crawler_t         |
|                                   |
+-----------------------------------+</pre>
      <div class="boot-prompt">[ press enter to simulate world ]</div>
    `;
    this.inputRow.style.display = 'none';
    this.cmdInput.value = '';
    this.inputText.textContent = '';
  }

  handleEnterKey() {
    if (this.gameState === 'BOOT') {
      this.startLoremasterProse();
    } else if (this.gameState === 'PRINTING') {
      // Skipping disabled: Enter key does nothing during typewriter
    } else if (this.gameState === 'FINISHED') {
      // Resting state - ready for next phase
    }
  }

  startLoremasterProse() {
    this.gameState = 'PRINTING';
    this.outputContainer.innerHTML = '';
    this.inputRow.style.display = 'none';

    // Split prose into distinct paragraphs
    const paragraphs = this.proseText
      .split(/\n\s*\n/)
      .map(p => p.trim())
      .filter(Boolean);

    let paraIndex = 0;
    let charIndex = 0;
    let currentProseSpan = null;
    let currentCursor = null;

    this.typewriterActive = true;

    const startParagraph = (index) => {
      if (!this.typewriterActive) return;

      const pText = paragraphs[index];
      charIndex = 0;

      // Spawn a new paragraph row with loremaster > prompt (zero extraneous whitespace in innerHTML)
      const proseBlock = document.createElement('div');
      proseBlock.className = 'prose-block';
      proseBlock.innerHTML = `<span class="prose-speaker">${this.promptSymbol}&nbsp;</span><span class="prose-text"></span><span class="cursor" style="opacity: 1;">|</span>`;
      this.outputContainer.appendChild(proseBlock);

      currentProseSpan = proseBlock.querySelector('.prose-text');
      currentCursor = proseBlock.querySelector('.cursor');
      this.scrollArea.scrollTop = this.scrollArea.scrollHeight;

      typeNextChar(pText);
    };

    const typeNextChar = (pText) => {
      if (!this.typewriterActive) return;

      if (charIndex < pText.length) {
        currentProseSpan.textContent += pText[charIndex];
        charIndex++;
        this.scrollArea.scrollTop = this.scrollArea.scrollHeight;

        // Vintage typewriter rhythm
        const char = pText[charIndex - 1];
        let delay = 12;
        if (char === '.' || char === '!' || char === '?') {
          delay = 130;
        } else if (char === ',' || char === '—') {
          delay = 60;
        }

        this.typewriterTimeout = setTimeout(() => typeNextChar(pText), delay);
      } else {
        // Current paragraph complete - remove its blinking cursor
        if (currentCursor) {
          currentCursor.remove();
          currentCursor = null;
        }

        paraIndex++;
        if (paraIndex < paragraphs.length) {
          // Pause briefly between paragraphs before starting next loremaster prompt
          this.typewriterTimeout = setTimeout(() => startParagraph(paraIndex), 220);
        } else {
          this.finishLoremasterProse();
        }
      }
    };

    startParagraph(0);
  }

  finishLoremasterProse(cursorEl) {
    this.typewriterActive = false;
    if (cursorEl) cursorEl.remove();
    if (this.typewriterTimeout) {
      clearTimeout(this.typewriterTimeout);
      this.typewriterTimeout = null;
    }

    this.gameState = 'FINISHED';
    this.inputRow.style.display = 'none';
    this.cmdInput.value = '';
    this.inputText.textContent = '';
    this.scrollArea.scrollTop = this.scrollArea.scrollHeight;
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

