/** Full-map thumbnail minimap with heatmap, articles, domain outlines, and draggable viewport. */

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
    this.width = 0;
    this.height = 0;
    this.estimates = null;
    this.heatmapRegion = null;
    this.articles = [];

    this._isDragging = false;
    this._dragOffset = null;

    this._isSelecting = false;
    this._selectionStart = null;
    this._selectionEnd = null;

    this._isResizing = false;
    this._resizeStart = null;
    this._resizeHandle = null;
    this._handleResizeStart = null;
    this._handleResizeMove = null;
    this._handleResizeEnd = null;

    this._handleMouseDown = this._onMouseDown.bind(this);
    this._handleMouseMove = this._onMouseMove.bind(this);
    this._handleMouseUp = this._onMouseUp.bind(this);
    this._handleClick = this._onClick.bind(this);

    // Container drag state
    this._isContainerDragging = false;
    this._containerDragOffset = null;
    this._dragBar = null;
    this._handleDragBarDown = null;
    this._cbContainerMove = null;
    this._cbContainerUp = null;
  }

  init(container, domains) {
    this.container = container;
    this.domains = domains;

    this.canvas = document.createElement('canvas');
    this.canvas.style.display = 'block';
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    this.canvas.style.cursor = 'pointer';
    this.container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    this._resize();

    this._resizeHandle = document.createElement('div');
    this._resizeHandle.style.cssText = 'position:absolute;bottom:0;right:0;width:14px;height:14px;cursor:nwse-resize;z-index:2;';
    this._resizeHandle.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14"><path d="M12 2L2 12M12 6L6 12M12 10L10 12" stroke="#00693e" stroke-width="1.5" opacity="0.5"/></svg>';
    // Only set position if not already absolute (needed for resize handle child positioning)
    const currentPos = window.getComputedStyle(container).position;
    if (currentPos === 'static') container.style.position = 'relative';
    container.appendChild(this._resizeHandle);

    this._handleResizeStart = this._onResizeStart.bind(this);
    this._resizeHandle.addEventListener('mousedown', this._handleResizeStart);

    this.canvas.addEventListener('mousedown', this._handleMouseDown);
    this.canvas.addEventListener('click', this._handleClick);
    window.addEventListener('mousemove', this._handleMouseMove);
    window.addEventListener('mouseup', this._handleMouseUp);

    // Prevent ALL mouse events on the minimap from propagating to the map canvas below
    container.addEventListener('mousedown', (e) => e.stopPropagation());
    container.addEventListener('mousemove', (e) => e.stopPropagation());
    container.addEventListener('mouseup', (e) => e.stopPropagation());
    container.addEventListener('click', (e) => e.stopPropagation());
    container.addEventListener('wheel', (e) => e.stopPropagation());
    container.addEventListener('pointerdown', (e) => e.stopPropagation());

    // Drag bar for repositioning the minimap container
    this._dragBar = document.createElement('div');
    this._dragBar.style.cssText =
      'position:absolute;top:0;left:0;right:0;height:16px;cursor:grab;z-index:3;' +
      'background:linear-gradient(to bottom, rgba(0,105,62,0.12), transparent);';
    // Grip pill visual indicator
    const grip = document.createElement('div');
    grip.style.cssText =
      'width:32px;height:4px;margin:6px auto 0;border-radius:2px;' +
      'background:rgba(0,105,62,0.35);pointer-events:none;';
    this._dragBar.appendChild(grip);
    container.appendChild(this._dragBar);
    this._initContainerDrag();

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

  setActive(domainId) {
    this.activeDomainId = domainId;
    this.render();
  }

  setViewport(viewport) {
    this.currentViewport = viewport;
    this.render();
  }

  setEstimates(estimates, region) {
    this.estimates = estimates;
    if (region) this.heatmapRegion = region;
    this.render();
  }

  setArticles(articles) {
    this.articles = articles || [];
    this.render();
  }

  onClick(handler) {
    this.clickHandler = handler;
  }

  onNavigate(handler) {
    this.navigateHandler = handler;
  }

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

  _isInsideViewport(mx, my) {
    if (!this.currentViewport) return false;
    const { x_min, x_max, y_min, y_max } = this.currentViewport;
    const nx = mx / this.width;
    const ny = my / this.height;
    return nx >= x_min && nx <= x_max && ny >= y_min && ny <= y_max;
  }

  _onMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (this._isInsideViewport(mx, my) && this.currentViewport) {
      this._isDragging = true;
      const vp = this.currentViewport;
      const vpCx = ((vp.x_min + vp.x_max) / 2) * this.width;
      const vpCy = ((vp.y_min + vp.y_max) / 2) * this.height;
      this._dragOffset = { x: mx - vpCx, y: my - vpCy };
      this.canvas.style.cursor = 'grabbing';
      e.preventDefault();
    } else {
      this._isSelecting = true;
      this._selectionStart = { x: mx, y: my };
      this._selectionEnd = { x: mx, y: my };
      this.canvas.style.cursor = 'crosshair';
      e.preventDefault();
    }
  }

  _onMouseMove(e) {
    if (this._isSelecting && this._selectionStart) {
      const rect = this.canvas.getBoundingClientRect();
      this._selectionEnd = {
        x: Math.max(0, Math.min(this.width, e.clientX - rect.left)),
        y: Math.max(0, Math.min(this.height, e.clientY - rect.top)),
      };
      this.render();
      this._drawSelectionRect();
      return;
    }

    if (!this._isDragging || !this.navigateHandler || !this.currentViewport) return;

    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const vp = this.currentViewport;
    const vpW = vp.x_max - vp.x_min;
    const vpH = vp.y_max - vp.y_min;

    const cx = (mx - this._dragOffset.x) / this.width;
    const cy = (my - this._dragOffset.y) / this.height;

    const x_min = Math.max(0, Math.min(1 - vpW, cx - vpW / 2));
    const y_min = Math.max(0, Math.min(1 - vpH, cy - vpH / 2));

    this.navigateHandler({
      x_min,
      x_max: x_min + vpW,
      y_min,
      y_max: y_min + vpH,
    }, false);
  }

  _onMouseUp() {
    if (this._isSelecting && this._selectionStart && this._selectionEnd && this.navigateHandler) {
      const sx = Math.min(this._selectionStart.x, this._selectionEnd.x);
      const sy = Math.min(this._selectionStart.y, this._selectionEnd.y);
      const sw = Math.abs(this._selectionEnd.x - this._selectionStart.x);
      const sh = Math.abs(this._selectionEnd.y - this._selectionStart.y);

      if (sw > 5 && sh > 5) {
        this.navigateHandler({
          x_min: sx / this.width,
          x_max: (sx + sw) / this.width,
          y_min: sy / this.height,
          y_max: (sy + sh) / this.height,
        }, true);
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
      this._dragOffset = null;
      this.canvas.style.cursor = 'pointer';
    }
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

  _onClick(e) {
    if (this._isDragging || this._isSelecting) return;
    if (!this.navigateHandler || !this.width || !this.height) return;

    const rect = this.canvas.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / this.width;
    const ny = (e.clientY - rect.top) / this.height;

    const vp = this.currentViewport || { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
    const vpW = vp.x_max - vp.x_min;
    const vpH = vp.y_max - vp.y_min;

    const x_min = Math.max(0, Math.min(1 - vpW, nx - vpW / 2));
    const y_min = Math.max(0, Math.min(1 - vpH, ny - vpH / 2));

    this.navigateHandler({
      x_min,
      x_max: x_min + vpW,
      y_min,
      y_max: y_min + vpH,
    }, true); // click = animated
  }

  render() {
    if (!this.ctx) return;
    // Re-check dimensions in case container was hidden during init and is now visible
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
    this._drawDomainOutlines(ctx, w, h);

    if (this.currentViewport) {
      this._drawViewportRect(ctx, w, h);
    }

    // Draw minimap border
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

    ctx.fillStyle = 'rgba(100, 116, 139, 0.25)';
    for (const a of this.articles) {
      ctx.fillRect(a.x * w, a.y * h, 1, 1);
    }
  }

  _drawDomainOutlines(ctx, w, h) {
    // Only draw the viewport rectangle (no domain outlines) to avoid
    // the confusing appearance of "two selected regions" in the minimap.
    // The viewport rect is drawn separately in _drawViewportRect.
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

  _initContainerDrag() {
    this._handleDragBarDown = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this._isContainerDragging = true;
      const rect = this.container.getBoundingClientRect();
      this._containerDragOffset = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
      this._dragBar.style.cursor = 'grabbing';
      // Capture pointer so we receive events even outside the element
      if (e.pointerId !== undefined) {
        this._dragBar.setPointerCapture(e.pointerId);
      }
    };

    this._cbContainerMove = (e) => {
      if (!this._isContainerDragging) return;
      const parent = this.container.parentElement;
      if (!parent) return;
      const parentRect = parent.getBoundingClientRect();
      const contW = this.container.offsetWidth;
      const contH = this.container.offsetHeight;

      let newLeft = e.clientX - parentRect.left - this._containerDragOffset.x;
      let newTop = e.clientY - parentRect.top - this._containerDragOffset.y;

      // Clamp within parent bounds
      newLeft = Math.max(0, Math.min(parentRect.width - contW, newLeft));
      newTop = Math.max(0, Math.min(parentRect.height - contH, newTop));

      this.container.style.left = newLeft + 'px';
      this.container.style.top = newTop + 'px';
      // Clear bottom/right anchoring so left/top take effect
      this.container.style.right = 'auto';
      this.container.style.bottom = 'auto';
    };

    this._cbContainerUp = (e) => {
      if (this._isContainerDragging) {
        this._isContainerDragging = false;
        this._containerDragOffset = null;
        this._dragBar.style.cursor = 'grab';
        if (e.pointerId !== undefined) {
          try { this._dragBar.releasePointerCapture(e.pointerId); } catch (_) { /* already released */ }
        }
      }
    };

    // Use pointer events for capture support, with mouse fallback
    this._dragBar.addEventListener('pointerdown', this._handleDragBarDown);
    window.addEventListener('pointermove', this._cbContainerMove);
    window.addEventListener('pointerup', this._cbContainerUp);
  }

  _onResizeStart(e) {
    e.preventDefault();
    e.stopPropagation();
    const rect = this.container.getBoundingClientRect();
    this._isResizing = true;
    this._resizeStart = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      width: rect.width,
      height: rect.height,
    };
    this._handleResizeMove = this._onResizeMove.bind(this);
    this._handleResizeEnd = this._onResizeEnd.bind(this);
    window.addEventListener('mousemove', this._handleResizeMove);
    window.addEventListener('mouseup', this._handleResizeEnd);
  }

  _onResizeMove(e) {
    if (!this._isResizing || !this._resizeStart) return;
    const dx = e.clientX - this._resizeStart.mouseX;
    const rawW = this._resizeStart.width + dx;
    const aspect = 4 / 3;
    let newW = Math.max(120, Math.min(400, rawW));
    let newH = Math.round(newW / aspect);
    if (newH < 90) { newH = 90; newW = Math.round(newH * aspect); }
    if (newH > 300) { newH = 300; newW = Math.round(newH * aspect); }
    this.container.style.width = newW + 'px';
    this.container.style.height = newH + 'px';
    this._resize();
    this.render();
  }

  _onResizeEnd() {
    this._isResizing = false;
    this._resizeStart = null;
    if (this._handleResizeMove) {
      window.removeEventListener('mousemove', this._handleResizeMove);
      this._handleResizeMove = null;
    }
    if (this._handleResizeEnd) {
      window.removeEventListener('mouseup', this._handleResizeEnd);
      this._handleResizeEnd = null;
    }
  }

  destroy() {
    // Clean up drag bar
    if (this._dragBar) {
      if (this._handleDragBarDown) {
        this._dragBar.removeEventListener('pointerdown', this._handleDragBarDown);
      }
      this._dragBar.remove();
      this._dragBar = null;
    }
    if (this._cbContainerMove) {
      window.removeEventListener('pointermove', this._cbContainerMove);
      this._cbContainerMove = null;
    }
    if (this._cbContainerUp) {
      window.removeEventListener('pointerup', this._cbContainerUp);
      this._cbContainerUp = null;
    }

    if (this._resizeHandle) {
      if (this._handleResizeStart) {
        this._resizeHandle.removeEventListener('mousedown', this._handleResizeStart);
      }
      this._resizeHandle.remove();
      this._resizeHandle = null;
    }
    this._onResizeEnd();
    if (this.canvas) {
      this.canvas.removeEventListener('mousedown', this._handleMouseDown);
      this.canvas.removeEventListener('click', this._handleClick);
      this.canvas.remove();
      this.canvas = null;
    }
    window.removeEventListener('mousemove', this._handleMouseMove);
    window.removeEventListener('mouseup', this._handleMouseUp);
    this.container = null;
    this.ctx = null;
    this.domains = [];
  }
}
