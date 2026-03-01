/** Full-map thumbnail minimap with heatmap, articles, domain outlines, and draggable viewport.
 *
 * All pointer interactions use setPointerCapture to prevent events from
 * reaching the sibling renderer canvas during drag / resize / reposition. */

export class Minimap {
  constructor() {
    this.container = null;
    this.canvas = null;
    this.ctx = null;
    this.domains = [];
    this.activeDomainId = null;
    this.currentViewport = null;
    this.clickHandler = null;
    this.navigateHandler = null;
    this.panHandler = null;
    this.width = 0;
    this.height = 0;
    this.estimates = null;
    this.heatmapRegion = null;
    this.articles = [];

    // Viewport-rect drag inside the minimap canvas
    this._isDragging = false;
    this._dragOffset = null;
    this._didDrag = false;  // suppress click after drag

    // Selection rectangle inside the minimap canvas
    this._isSelecting = false;
    this._selectionStart = null;
    this._selectionEnd = null;

    // Resize handle
    this._isResizing = false;
    this._resizeStart = null;
    this._resizeHandle = null;

    // Container reposition (drag bar)
    this._isContainerDragging = false;
    this._containerDragOffset = null;
    this._dragBar = null;

    // Bound handlers — pointer events throughout
    this._onCanvasPointerDown = this._handleCanvasPointerDown.bind(this);
    this._onCanvasPointerMove = this._handleCanvasPointerMove.bind(this);
    this._onCanvasPointerUp = this._handleCanvasPointerUp.bind(this);
    this._onCanvasClick = this._handleCanvasClick.bind(this);

    this._onResizePointerDown = this._handleResizePointerDown.bind(this);
    this._onResizePointerMove = this._handleResizePointerMove.bind(this);
    this._onResizePointerUp = this._handleResizePointerUp.bind(this);

    this._onDragBarPointerDown = this._handleDragBarPointerDown.bind(this);
    this._onDragBarPointerMove = this._handleDragBarPointerMove.bind(this);
    this._onDragBarPointerUp = this._handleDragBarPointerUp.bind(this);
  }

  // ======== Public API ========

  init(container, domains) {
    this.container = container;
    this.domains = domains;

    // Ensure container can hold absolutely-positioned children
    const currentPos = window.getComputedStyle(container).position;
    if (currentPos === 'static') container.style.position = 'relative';

    // Canvas fills the container
    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'display:block;width:100%;height:100%;cursor:pointer;';
    container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');
    this._resize();

    // Resize handle — 20×20 for comfortable grab, inset 2px so overflow:hidden can't clip it
    this._resizeHandle = document.createElement('div');
    this._resizeHandle.style.cssText =
      'position:absolute;bottom:2px;right:2px;width:20px;height:20px;' +
      'cursor:nwse-resize;z-index:4;touch-action:none;';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '14');
    svg.setAttribute('height', '14');
    svg.setAttribute('viewBox', '0 0 14 14');
    svg.style.cssText = 'position:absolute;bottom:0;right:0;pointer-events:none;';
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M12 2L2 12M12 6L6 12M12 10L10 12');
    path.setAttribute('stroke', '#00693e');
    path.setAttribute('stroke-width', '1.5');
    path.setAttribute('opacity', '0.5');
    svg.appendChild(path);
    this._resizeHandle.appendChild(svg);
    container.appendChild(this._resizeHandle);

    // Drag bar at top for repositioning the container
    this._dragBar = document.createElement('div');
    this._dragBar.style.cssText =
      'position:absolute;top:0;left:0;right:0;height:18px;cursor:grab;z-index:4;' +
      'background:linear-gradient(to bottom, rgba(0,105,62,0.12), transparent);touch-action:none;';
    const grip = document.createElement('div');
    grip.style.cssText =
      'width:32px;height:4px;margin:7px auto 0;border-radius:2px;' +
      'background:rgba(0,105,62,0.35);pointer-events:none;';
    this._dragBar.appendChild(grip);
    container.appendChild(this._dragBar);

    // ---- Wire up pointer events ----

    // Canvas: viewport drag, selection, click-to-navigate
    this.canvas.addEventListener('pointerdown', this._onCanvasPointerDown);
    this.canvas.addEventListener('pointermove', this._onCanvasPointerMove);
    this.canvas.addEventListener('pointerup', this._onCanvasPointerUp);
    this.canvas.addEventListener('click', this._onCanvasClick);

    // Resize handle
    this._resizeHandle.addEventListener('pointerdown', this._onResizePointerDown);

    // Drag bar
    this._dragBar.addEventListener('pointerdown', this._onDragBarPointerDown);

    // Block wheel events from reaching the map canvas underneath (siblings,
    // so we need to prevent the default and stop immediate propagation on the
    // container itself — wheel doesn't need pointer capture).
    container.addEventListener('wheel', (e) => { e.preventDefault(); e.stopPropagation(); }, { passive: false });

    this.render();
  }

  _resize() {
    if (!this.container || !this.canvas) return;
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.width = rect.width;
    this.height = rect.height;
  }

  setActive(domainId) { this.activeDomainId = domainId; this.render(); }
  setViewport(viewport) { this.currentViewport = viewport; this.render(); }
  setEstimates(estimates, region) { this.estimates = estimates; if (region) this.heatmapRegion = region; this.render(); }
  setArticles(articles) { this.articles = articles || []; this.render(); }
  onClick(handler) { this.clickHandler = handler; }
  onNavigate(handler) { this.navigateHandler = handler; }
  onPan(handler) { this.panHandler = handler; }

  // ======== Canvas pointer events (viewport drag + selection + click) ========

  _isInsideViewport(mx, my) {
    if (!this.currentViewport) return false;
    const { x_min, x_max, y_min, y_max } = this.currentViewport;
    // 3px padding makes the viewport rectangle easier to grab
    const pad = 3 / Math.max(1, this.width);
    return (mx / this.width) >= (x_min - pad) && (mx / this.width) <= (x_max + pad) &&
           (my / this.height) >= (y_min - pad) && (my / this.height) <= (y_max + pad);
  }

  _handleCanvasPointerDown(e) {
    e.preventDefault();
    // Capture: all subsequent pointer events go to this canvas, not to any sibling
    this.canvas.setPointerCapture(e.pointerId);

    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    this._didDrag = false;

    if (this._isInsideViewport(mx, my) && this.currentViewport) {
      this._isDragging = true;
      const vp = this.currentViewport;
      const vpCx = ((vp.x_min + vp.x_max) / 2) * this.width;
      const vpCy = ((vp.y_min + vp.y_max) / 2) * this.height;
      this._dragOffset = { x: mx - vpCx, y: my - vpCy };
      this.canvas.style.cursor = 'grabbing';
    } else {
      this._isSelecting = true;
      this._selectionStart = { x: mx, y: my };
      this._selectionEnd = { x: mx, y: my };
      this.canvas.style.cursor = 'crosshair';
    }
  }

  _handleCanvasPointerMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (this._isSelecting && this._selectionStart) {
      this._selectionEnd = {
        x: Math.max(0, Math.min(this.width, mx)),
        y: Math.max(0, Math.min(this.height, my)),
      };
      this.render();
      this._drawSelectionRect();
      return;
    }

    if (!this._isDragging || !this.panHandler || !this.currentViewport) return;

    const vp = this.currentViewport;
    const vpW = vp.x_max - vp.x_min;
    const vpH = vp.y_max - vp.y_min;
    const cx = (mx - this._dragOffset.x) / this.width;
    const cy = (my - this._dragOffset.y) / this.height;
    // Clamp center so viewport stays in bounds
    const clampedCx = Math.max(vpW / 2, Math.min(1 - vpW / 2, cx));
    const clampedCy = Math.max(vpH / 2, Math.min(1 - vpH / 2, cy));

    this.panHandler(clampedCx, clampedCy, false);
  }

  _handleCanvasPointerUp(e) {
    try { this.canvas.releasePointerCapture(e.pointerId); } catch (_) { /* ok */ }

    if (this._isSelecting && this._selectionStart && this._selectionEnd && this.navigateHandler) {
      const sx = Math.min(this._selectionStart.x, this._selectionEnd.x);
      const sy = Math.min(this._selectionStart.y, this._selectionEnd.y);
      const sw = Math.abs(this._selectionEnd.x - this._selectionStart.x);
      const sh = Math.abs(this._selectionEnd.y - this._selectionStart.y);

      if (sw > 5 && sh > 5) {
        this.navigateHandler({
          x_min: sx / this.width, x_max: (sx + sw) / this.width,
          y_min: sy / this.height, y_max: (sy + sh) / this.height,
        }, true);
        this._didDrag = true;  // suppress click after selection
      }
      this._isSelecting = false;
      this._selectionStart = null;
      this._selectionEnd = null;
      this.canvas.style.cursor = 'pointer';
      this.render();
      return;
    }

    if (this._isDragging) {
      this._isDragging = false;
      this._didDrag = true;  // suppress the click event that fires right after pointerup
      this._dragOffset = null;
      this.canvas.style.cursor = 'pointer';
    }
  }

  _handleCanvasClick(e) {
    if (this._isDragging || this._isSelecting) return;
    if (this._didDrag) { this._didDrag = false; return; }
    if (!this.panHandler || !this.width || !this.height) return;

    // If fully zoomed out (viewport covers nearly everything), do nothing
    const vp = this.currentViewport || { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
    const vpW = vp.x_max - vp.x_min;
    const vpH = vp.y_max - vp.y_min;
    if (vpW >= 0.95 && vpH >= 0.95) return;

    const rect = this.canvas.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / this.width;
    const ny = (e.clientY - rect.top) / this.height;

    this.panHandler(nx, ny, true);
  }

  // ======== Resize handle ========

  _handleResizePointerDown(e) {
    e.preventDefault();
    e.stopPropagation();
    this._resizeHandle.setPointerCapture(e.pointerId);

    const rect = this.container.getBoundingClientRect();
    this._isResizing = true;
    this._resizeStart = { mouseX: e.clientX, mouseY: e.clientY, width: rect.width, height: rect.height };

    // Bind move/up on the handle itself (captured pointer delivers events here)
    this._resizeHandle.addEventListener('pointermove', this._onResizePointerMove);
    this._resizeHandle.addEventListener('pointerup', this._onResizePointerUp);
  }

  _handleResizePointerMove(e) {
    if (!this._isResizing || !this._resizeStart) return;

    const dx = e.clientX - this._resizeStart.mouseX;
    const dy = e.clientY - this._resizeStart.mouseY;
    // Use the larger of dx/dy to feel responsive for diagonal drags
    const delta = Math.abs(dx) > Math.abs(dy) ? dx : dy;

    const aspect = 4 / 3;
    let newW = Math.max(120, Math.min(400, this._resizeStart.width + delta));
    let newH = Math.round(newW / aspect);
    if (newH < 90) { newH = 90; newW = Math.round(newH * aspect); }
    if (newH > 300) { newH = 300; newW = Math.round(newH * aspect); }

    this.container.style.width = newW + 'px';
    this.container.style.height = newH + 'px';
    this._resize();
    this.render();
  }

  _handleResizePointerUp(e) {
    this._isResizing = false;
    this._resizeStart = null;
    try { this._resizeHandle.releasePointerCapture(e.pointerId); } catch (_) { /* ok */ }
    this._resizeHandle.removeEventListener('pointermove', this._onResizePointerMove);
    this._resizeHandle.removeEventListener('pointerup', this._onResizePointerUp);
  }

  // ======== Container drag (reposition) ========

  _handleDragBarPointerDown(e) {
    e.preventDefault();
    e.stopPropagation();
    this._dragBar.setPointerCapture(e.pointerId);

    this._isContainerDragging = true;
    const rect = this.container.getBoundingClientRect();
    this._containerDragOffset = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    this._dragBar.style.cursor = 'grabbing';

    this._dragBar.addEventListener('pointermove', this._onDragBarPointerMove);
    this._dragBar.addEventListener('pointerup', this._onDragBarPointerUp);
  }

  _handleDragBarPointerMove(e) {
    if (!this._isContainerDragging) return;
    const parent = this.container.parentElement;
    if (!parent) return;
    const parentRect = parent.getBoundingClientRect();
    const contW = this.container.offsetWidth;
    const contH = this.container.offsetHeight;

    let newLeft = e.clientX - parentRect.left - this._containerDragOffset.x;
    let newTop = e.clientY - parentRect.top - this._containerDragOffset.y;

    newLeft = Math.max(0, Math.min(parentRect.width - contW, newLeft));
    newTop = Math.max(0, Math.min(parentRect.height - contH, newTop));

    this.container.style.left = newLeft + 'px';
    this.container.style.top = newTop + 'px';
    this.container.style.right = 'auto';
    this.container.style.bottom = 'auto';
  }

  _handleDragBarPointerUp(e) {
    this._isContainerDragging = false;
    this._containerDragOffset = null;
    this._dragBar.style.cursor = 'grab';
    try { this._dragBar.releasePointerCapture(e.pointerId); } catch (_) { /* ok */ }
    this._dragBar.removeEventListener('pointermove', this._onDragBarPointerMove);
    this._dragBar.removeEventListener('pointerup', this._onDragBarPointerUp);
  }

  // ======== Rendering ========

  _heatmapColor(value) {
    const v = Math.max(0, Math.min(1, value));
    if (v < 0.5) {
      const t = v / 0.5;
      return [
        Math.round(157 + t * (245 - 157)),
        Math.round(22 + t * (220 - 22)),
        Math.round(46 + t * (105 - 46)),
      ];
    }
    const t = (v - 0.5) / 0.5;
    return [
      Math.round(245 + t * (0 - 245)),
      Math.round(220 + t * (105 - 220)),
      Math.round(105 + t * (62 - 105)),
    ];
  }

  _drawSelectionRect() {
    if (!this._selectionStart || !this._selectionEnd || !this.ctx) return;
    const ctx = this.ctx;
    const sx = Math.min(this._selectionStart.x, this._selectionEnd.x);
    const sy = Math.min(this._selectionStart.y, this._selectionEnd.y);
    const sw = Math.abs(this._selectionEnd.x - this._selectionStart.x);
    const sh = Math.abs(this._selectionEnd.y - this._selectionStart.y);
    ctx.fillStyle = 'rgba(0, 105, 62, 0.15)';
    ctx.fillRect(sx, sy, sw, sh);
    ctx.strokeStyle = '#00693e';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.strokeRect(sx, sy, sw, sh);
    ctx.setLineDash([]);
  }

  render() {
    if (!this.ctx) return;
    if (!this.width || !this.height) this._resize();
    if (!this.width || !this.height) return;

    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, w, h);

    this._drawHeatmap(ctx, w, h);
    this._drawArticles(ctx, w, h);

    if (this.currentViewport) {
      this._drawViewportRect(ctx, w, h);
    }

    // Border
    ctx.strokeStyle = '#00693e';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(0.5, 0.5, w - 1, h - 1, 6);
    ctx.stroke();
  }

  _drawHeatmap(ctx, w, h) {
    if (!this.estimates || this.estimates.length === 0 || !this.heatmapRegion) return;
    const region = this.heatmapRegion;
    const gridSize = Math.round(Math.sqrt(this.estimates.length));
    if (gridSize === 0) return;

    const rx = region.x_min * w;
    const ry = region.y_min * h;
    const rw = (region.x_max - region.x_min) * w;
    const rh = (region.y_max - region.y_min) * h;
    const cellW = rw / gridSize;
    const cellH = rh / gridSize;

    ctx.globalAlpha = 0.4;
    for (const e of this.estimates) {
      const [r, g, b] = this._heatmapColor(e.value);
      const a = e.evidenceCount === 0 ? 0.25 : 0.7;
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;
      ctx.fillRect(rx + e.gx * cellW, ry + e.gy * cellH, cellW + 0.5, cellH + 0.5);
    }
    ctx.globalAlpha = 1;
  }

  _drawArticles(ctx, w, h) {
    if (this.articles.length === 0) return;
    ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
    for (const a of this.articles) {
      ctx.fillRect(a.x * w, a.y * h, 1, 1);
    }
  }

  _drawViewportRect(ctx, w, h) {
    const { x_min, x_max, y_min, y_max } = this.currentViewport;
    const x = x_min * w;
    const y = y_min * h;
    const vw = (x_max - x_min) * w;
    const vh = (y_max - y_min) * h;

    ctx.fillStyle = 'rgba(0, 105, 62, 0.06)';
    ctx.fillRect(x, y, vw, vh);
    ctx.strokeStyle = '#00693e';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([]);
    ctx.strokeRect(x, y, vw, vh);
  }

  // ======== Cleanup ========

  destroy() {
    if (this._dragBar) {
      this._dragBar.removeEventListener('pointerdown', this._onDragBarPointerDown);
      this._dragBar.removeEventListener('pointermove', this._onDragBarPointerMove);
      this._dragBar.removeEventListener('pointerup', this._onDragBarPointerUp);
      this._dragBar.remove();
      this._dragBar = null;
    }
    if (this._resizeHandle) {
      this._resizeHandle.removeEventListener('pointerdown', this._onResizePointerDown);
      this._resizeHandle.removeEventListener('pointermove', this._onResizePointerMove);
      this._resizeHandle.removeEventListener('pointerup', this._onResizePointerUp);
      this._resizeHandle.remove();
      this._resizeHandle = null;
    }
    if (this.canvas) {
      this.canvas.removeEventListener('pointerdown', this._onCanvasPointerDown);
      this.canvas.removeEventListener('pointermove', this._onCanvasPointerMove);
      this.canvas.removeEventListener('pointerup', this._onCanvasPointerUp);
      this.canvas.removeEventListener('click', this._onCanvasClick);
      this.canvas.remove();
      this.canvas = null;
    }
    this.container = null;
    this.ctx = null;
    this.domains = [];
  }
}
