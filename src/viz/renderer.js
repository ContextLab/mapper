/** Canvas 2D renderer for point cloud, heatmap overlay, and answered-question dots. */

import { mergeForTransition, buildTransitionFrames, needs3D, cubicInOut } from './transitions.js';

function valueToDarkColor(v) {
  const val = Math.max(0, Math.min(1, v));
  let r, g, b;
  if (val < 0.5) {
    const t = val / 0.5;
    r = Math.round(15 + t * (0 - 15));
    g = Math.round(23 + t * (105 - 23));
    b = Math.round(42 + t * (62 - 42));
  } else {
    const t = (val - 0.5) / 0.5;
    r = Math.round(0 + t * (255 - 0));
    g = Math.round(105 + t * (160 - 105));
    b = Math.round(62 + t * (15 - 62));
  }
  return [r, g, b];
}

function valueToLightColor(v) {
  const val = Math.max(0, Math.min(1, v));
  let r, g, b;
  if (val < 0.5) {
    const t = val / 0.5;
    r = Math.round(248 + t * (167 - 248));
    g = Math.round(250 + t * (210 - 250));
    b = Math.round(252 + t * (178 - 252));
  } else {
    const t = (val - 0.5) / 0.5;
    r = Math.round(167 + t * (0 - 167));
    g = Math.round(210 + t * (105 - 210));
    b = Math.round(178 + t * (62 - 178));
  }
  return [r, g, b];
}

const TRANSITION_DURATION = 600;
const HEATMAP_OPACITY = 0.55;

export class Renderer {
  constructor() {
    this._container = null;
    this._canvas = null;
    this._ctx = null;
    this._dpr = 1;
    this._width = 0;   // CSS pixels
    this._height = 0;  // CSS pixels

    this._points = [];
    this._heatmapEstimates = [];
    this._heatmapRegion = null;
    this._answeredData = [];
    this._showColorbar = false;

    this._onReanswer = null;
    this._onViewportChange = null;
    this._onCellClick = null;

    // Pan/zoom state (identity = full [0,1] view)
    this._panX = 0;
    this._panY = 0;
    this._zoom = 1;

    // Tooltip element
    this._tooltip = null;

    // Transition state
    this._transitionAbort = null;
    this._animFrame = null;

    // Interaction state
    this._hoveredPoint = null;
    this._isDragging = false;
    this._dragMoved = false;
    this._lastMouse = null;

    // Bound handlers (for removal)
    this._onMouseMove = this._handleMouseMove.bind(this);
    this._onMouseDown = this._handleMouseDown.bind(this);
    this._onMouseUp = this._handleMouseUp.bind(this);
    this._onMouseLeave = this._handleMouseLeave.bind(this);
    this._onWheel = this._handleWheel.bind(this);
    this._onResize = this._handleResize.bind(this);
    this._onClick = this._handleClick.bind(this);

    // Touch handlers
    this._onTouchStart = this._handleTouchStart.bind(this);
    this._onTouchMove = this._handleTouchMove.bind(this);
    this._onTouchEnd = this._handleTouchEnd.bind(this);
    this._lastTouchDist = null;
    this._lastTouchCenter = null;
  }

  /**
   * Initialize with a DOM container.
   * @param {object} config - { container, onViewportChange, onCellClick }
   */
  init(config) {
    const { container, onViewportChange, onCellClick } = config;
    this._container = container;
    this._onViewportChange = onViewportChange;
    this._onCellClick = onCellClick;

    // Create canvas
    this._canvas = document.createElement('canvas');
    this._canvas.style.display = 'block';
    this._canvas.style.width = '100%';
    this._canvas.style.height = '100%';
    container.appendChild(this._canvas);
    this._ctx = this._canvas.getContext('2d');

    this._tooltip = document.createElement('div');
    this._tooltip.className = 'map-tooltip';
    this._tooltip.style.cssText =
      'position:absolute;pointer-events:none;z-index:20;' +
      'background:var(--color-surface);color:var(--color-text);' +
      'padding:8px 12px;border-radius:8px;font-size:0.78rem;' +
      'font-family:var(--font-body);border:1px solid var(--color-border);' +
      'box-shadow:0 4px 16px rgba(0,0,0,0.35);opacity:0;transition:opacity 0.15s ease;' +
      'white-space:normal;max-width:340px;overflow:hidden;line-height:1.5;' +
      'border-left:3px solid var(--color-border);';
    container.style.position = 'relative';
    container.appendChild(this._tooltip);

    // Size canvas
    this._resize();

    // Event listeners
    this._canvas.addEventListener('mousemove', this._onMouseMove);
    this._canvas.addEventListener('mousedown', this._onMouseDown);
    this._canvas.addEventListener('mouseup', this._onMouseUp);
    this._canvas.addEventListener('mouseleave', this._onMouseLeave);
    this._canvas.addEventListener('wheel', this._onWheel, { passive: false });
    this._canvas.addEventListener('click', this._onClick);
    this._canvas.addEventListener('touchstart', this._onTouchStart, { passive: false });
    this._canvas.addEventListener('touchmove', this._onTouchMove, { passive: false });
    this._canvas.addEventListener('touchend', this._onTouchEnd);
    window.addEventListener('resize', this._onResize);

    this._onThemeChange = () => this._render();
    document.documentElement.addEventListener('theme-changed', this._onThemeChange);

    this._render();
  }

  /**
   * Update visible points.
   * @param {Array<object>} points - PointData[]
   */
  setPoints(points) {
    this._points = points || [];
    if (this._points.length > 0) this._showColorbar = true;
    this._render();
  }

  /**
   * Update heatmap overlay from knowledge estimates.
   * @param {Array<object>} estimates - CellEstimate[]
   * @param {object} region - { x_min, x_max, y_min, y_max }
   */
  setHeatmap(estimates, region) {
    this._heatmapEstimates = estimates || [];
    this._heatmapRegion = region || null;
    this._render();
  }

  setLabels() {}

  /**
   * Update answered-question dot overlay.
   * @param {Array<object>} data - { x, y, questionId, title, color, isCorrect }
   */
  setAnsweredQuestions(data) {
    this._answeredData = data || [];
    this._render();
  }

  /**
   * Register callback for re-answer clicks on answered dots.
   * @param {function} handler - receives (questionId)
   */
  onReanswer(handler) {
    this._onReanswer = handler;
  }

  /**
   * Get current viewport in normalized [0,1] coordinates.
   * @returns {{ x_min, x_max, y_min, y_max }}
   */
  getViewport() {
    if (!this._width || !this._height) {
      return { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
    }
    // Invert the transform: screen coords [0, width] → normalized coords
    // Screen x = panX + normX * zoom * width  →  normX = (screenX - panX) / (zoom * width)
    const x_min = Math.max(0, -this._panX / (this._zoom * this._width));
    const y_min = Math.max(0, -this._panY / (this._zoom * this._height));
    const x_max = Math.min(1, (this._width - this._panX) / (this._zoom * this._width));
    const y_max = Math.min(1, (this._height - this._panY) / (this._zoom * this._height));
    return { x_min, x_max, y_min, y_max };
  }

  /**
   * Animate to a new region.
   * @param {object} region - { x_min, x_max, y_min, y_max }
   * @param {number} [duration=600]
   * @returns {Promise<void>}
   */
  jumpTo(region) {
    this.abortTransition();
    const target = this._computePanZoomForRegion(region);
    this._panX = target.panX;
    this._panY = target.panY;
    this._zoom = target.zoom;
    this._clampPanZoom();
    this._render();
    this._notifyViewport();
  }

  transitionTo(region, duration = TRANSITION_DURATION) {
    this.abortTransition();
    return new Promise((resolve) => {
      if (duration <= 0) { this.jumpTo(region); resolve(); return; }

      const target = this._computePanZoomForRegion(region);
      const startPanX = this._panX;
      const startPanY = this._panY;
      const startZoom = this._zoom;
      const startTime = performance.now();

      let aborted = false;
      this._transitionAbort = () => { aborted = true; resolve(); };

      const animate = (now) => {
        if (aborted) return;
        const elapsed = now - startTime;
        const t = Math.min(1, elapsed / duration);
        const e = cubicInOut(t);

        this._panX = startPanX + (target.panX - startPanX) * e;
        this._panY = startPanY + (target.panY - startPanY) * e;
        this._zoom = startZoom + (target.zoom - startZoom) * e;
        this._render();

        if (t < 1) {
          this._animFrame = requestAnimationFrame(animate);
        } else {
          this._panX = target.panX;
          this._panY = target.panY;
          this._zoom = target.zoom;
          this._clampPanZoom();
          this._render();
          this._notifyViewport();
          this._transitionAbort = null;
          resolve();
        }
      };

      this._animFrame = requestAnimationFrame(animate);
    });
  }

  /**
   * Abort any in-progress transition.
   */
  abortTransition() {
    if (this._transitionAbort) {
      this._transitionAbort();
      this._transitionAbort = null;
    }
    if (this._animFrame) {
      cancelAnimationFrame(this._animFrame);
      this._animFrame = null;
    }
  }

  /**
   * Animate points from source set to target set.
   * For nearby domains (IoU >= 0.3): merge + pan-fade.
   * For distant domains (IoU < 0.3): crossfade.
   */
  transitionPoints(sourcePoints, targetPoints, sourceRegion, targetRegion, duration = TRANSITION_DURATION) {
    this.abortTransition();
    const useCrossfade = needs3D(sourceRegion, targetRegion);

    return new Promise((resolve) => {
      let aborted = false;
      this._transitionAbort = () => { aborted = true; resolve(); };

      if (useCrossfade) {
        this._crossfadeTransition(sourcePoints, targetPoints, sourceRegion, targetRegion, duration, () => aborted, resolve);
      } else {
        this._panFadeTransition(sourcePoints, targetPoints, targetRegion, duration, () => aborted, resolve);
      }
    });
  }

  destroy() {
    this.abortTransition();
    if (this._canvas) {
      this._canvas.removeEventListener('mousemove', this._onMouseMove);
      this._canvas.removeEventListener('mousedown', this._onMouseDown);
      this._canvas.removeEventListener('mouseup', this._onMouseUp);
      this._canvas.removeEventListener('mouseleave', this._onMouseLeave);
      this._canvas.removeEventListener('wheel', this._onWheel);
      this._canvas.removeEventListener('click', this._onClick);
      this._canvas.removeEventListener('touchstart', this._onTouchStart);
      this._canvas.removeEventListener('touchmove', this._onTouchMove);
      this._canvas.removeEventListener('touchend', this._onTouchEnd);
      this._canvas.remove();
      this._canvas = null;
    }
    if (this._tooltip) {
      this._tooltip.remove();
      this._tooltip = null;
    }
    window.removeEventListener('resize', this._onResize);
    if (this._onThemeChange) {
      document.documentElement.removeEventListener('theme-changed', this._onThemeChange);
    }
    this._ctx = null;
    this._container = null;
  }

  // ======== PRIVATE: Rendering ========

  _resize() {
    if (!this._container || !this._canvas) return;
    const rect = this._container.getBoundingClientRect();
    this._dpr = window.devicePixelRatio || 1;
    this._width = rect.width;
    this._height = rect.height;
    this._canvas.width = rect.width * this._dpr;
    this._canvas.height = rect.height * this._dpr;
  }

  _isLightMode() {
    return document.documentElement.getAttribute('data-theme') === 'light';
  }

  _render() {
    if (!this._ctx || !this._width || !this._height) return;

    const ctx = this._ctx;
    const dpr = this._dpr;
    const w = this._width;
    const h = this._height;
    const light = this._isLightMode();

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = light ? '#ffffff' : (getComputedStyle(this._container).getPropertyValue('--color-bg').trim() || '#0f172a');
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(this._panX, this._panY);
    ctx.scale(this._zoom, this._zoom);

    this._drawHeatmap(ctx, w, h, light);
    this._drawPoints(ctx, w, h, light);
    this._drawAnsweredDots(ctx, w, h, light);

    ctx.restore();

    this._drawColorbar(ctx, w, h, light);
  }

  _drawHeatmap(ctx, w, h, light) {
    const estimates = this._heatmapEstimates;
    const region = this._heatmapRegion;
    if (!estimates || estimates.length === 0 || !region) return;

    const gridSize = Math.round(Math.sqrt(estimates.length));
    if (gridSize === 0) return;

    const rx = region.x_min * w;
    const ry = region.y_min * h;
    const rw = (region.x_max - region.x_min) * w;
    const rh = (region.y_max - region.y_min) * h;
    const cellW = rw / gridSize;
    const cellH = rh / gridSize;

    ctx.globalAlpha = light ? 0.45 : HEATMAP_OPACITY;
    const colorFn = light ? valueToLightColor : valueToDarkColor;

    for (const e of estimates) {
      if (e.state === 'unknown') continue;
      const [r, g, b] = colorFn(e.value);
      const a = e.evidenceCount === 0 ? 0.3 : 0.75;
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;
      ctx.fillRect(rx + e.gx * cellW, ry + e.gy * cellH, cellW + 0.5, cellH + 0.5);
    }

    ctx.globalAlpha = 1;
  }

  _drawPoints(ctx, w, h, light) {
    if (this._points.length === 0) return;

    const defaultColor = light ? [100, 116, 139, 80] : [148, 163, 184, 80];
    for (const p of this._points) {
      const px = p.x * w;
      const py = p.y * h;
      const r = (p.radius || 2) / this._zoom;
      const isDefaultDark = p.color && p.color[0] === 148 && p.color[1] === 163;
      const color = (light && isDefaultDark) ? defaultColor : (p.color || defaultColor);
      const alpha = (color[3] ?? 100) / 255;

      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
      ctx.fill();
    }
  }

  _drawAnsweredDots(ctx, w, h, light) {
    if (this._answeredData.length === 0) return;

    for (const d of this._answeredData) {
      const px = d.x * w;
      const py = d.y * h;
      const r = 5 / this._zoom;

      ctx.beginPath();
      ctx.arc(px, py, r + 1.5 / this._zoom, 0, Math.PI * 2);
      ctx.fillStyle = light ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.9)';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      const c = d.color || [200, 200, 200, 200];
      ctx.fillStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${(c[3] ?? 200) / 255})`;
      ctx.fill();
    }
  }

  _drawColorbar(ctx, w, h, light) {
    if (!this._showColorbar) return;

    const barW = 12;
    const barH = 120;
    const margin = 16;
    const x = w - barW - margin;
    const y = h - barH - margin;

    ctx.save();
    ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);

    ctx.fillStyle = light ? 'rgba(255,255,255,0.85)' : 'rgba(15,23,42,0.8)';
    ctx.beginPath();
    ctx.roundRect(x - 6, y - 20, barW + 12, barH + 36, 6);
    ctx.fill();

    const colorFn = light ? valueToLightColor : valueToDarkColor;
    const steps = 40;
    const stepH = barH / steps;
    for (let i = 0; i < steps; i++) {
      const v = 1 - i / (steps - 1);
      const [r, g, b] = colorFn(v);
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
      ctx.fillRect(x, y + i * stepH, barW, stepH + 0.5);
    }

    ctx.strokeStyle = light ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 0.5;
    ctx.strokeRect(x, y, barW, barH);

    const fontFamily = getComputedStyle(document.documentElement).getPropertyValue('--font-body').trim() || 'sans-serif';
    ctx.font = `9px ${fontFamily}`;
    ctx.textAlign = 'center';
    ctx.fillStyle = light ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.6)';
    ctx.fillText('100%', x + barW / 2, y - 4);
    ctx.fillText('0%', x + barW / 2, y + barH + 12);

    ctx.restore();
  }

  // ======== Pan/Zoom ========

  _computePanZoomForRegion(region) {
    const w = this._width;
    const h = this._height;
    const rw = region.x_max - region.x_min;
    const rh = region.y_max - region.y_min;

    // 30% padding gives context around the domain
    const padding = 1.3;
    const zoomX = 1 / (rw * padding);
    const zoomY = 1 / (rh * padding);
    const zoom = Math.max(1, Math.min(10, Math.min(zoomX, zoomY)));

    const cx = (region.x_min + region.x_max) / 2;
    const cy = (region.y_min + region.y_max) / 2;
    let panX = w / 2 - cx * zoom * w;
    let panY = h / 2 - cy * zoom * h;

    // Clamp so content always fills screen
    const contentW = zoom * w;
    const contentH = zoom * h;
    panX = Math.max(w - contentW, Math.min(0, panX));
    panY = Math.max(h - contentH, Math.min(0, panY));

    return { panX, panY, zoom };
  }

  _clampPanZoom() {
    this._zoom = Math.max(1, Math.min(10, this._zoom));

    // Prevent panning beyond the [0,1] content
    const w = this._width;
    const h = this._height;
    const contentW = this._zoom * w;
    const contentH = this._zoom * h;

    // panX: left edge can't go right of 0, right edge can't go left of w
    this._panX = Math.max(w - contentW, Math.min(0, this._panX));
    this._panY = Math.max(h - contentH, Math.min(0, this._panY));
  }

  // ======== PRIVATE: Event handlers ========

  _handleResize() {
    this._resize();
    this._render();
  }

  _handleWheel(e) {
    e.preventDefault();

    const rect = this._canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left; // Mouse position in CSS pixels
    const my = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    const newZoom = Math.max(1, Math.min(10, this._zoom * zoomFactor));

    if (newZoom === this._zoom) return;

    // Zoom centered on cursor
    const scale = newZoom / this._zoom;
    this._panX = mx - scale * (mx - this._panX);
    this._panY = my - scale * (my - this._panY);
    this._zoom = newZoom;

    this._clampPanZoom();
    this._render();
    this._notifyViewport();
  }

  _handleMouseDown(e) {
    if (e.button !== 0) return;
    this._isDragging = true;
    this._dragMoved = false;
    this._lastMouse = { x: e.clientX, y: e.clientY };
    this._canvas.style.cursor = 'grabbing';
  }

  _handleMouseUp() {
    this._isDragging = false;
    this._lastMouse = null;
    this._canvas.style.cursor = this._hoveredPoint ? 'pointer' : '';
  }

  _handleMouseLeave() {
    this._isDragging = false;
    this._lastMouse = null;
    this._hideTooltip();
    this._canvas.style.cursor = '';
  }

  _handleMouseMove(e) {
    const rect = this._canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (this._isDragging && this._lastMouse) {
      const dx = e.clientX - this._lastMouse.x;
      const dy = e.clientY - this._lastMouse.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) this._dragMoved = true;
      this._panX += dx;
      this._panY += dy;
      this._lastMouse = { x: e.clientX, y: e.clientY };

      this._clampPanZoom();
      this._render();
      this._notifyViewport();
      return;
    }

    const hit = this._hitTest(mx, my);
    if (hit) {
      this._hoveredPoint = hit;
      this._canvas.style.cursor = 'pointer';
      this._showTooltip(this._buildTooltipHTML(hit), e.clientX - rect.left, e.clientY - rect.top);
    } else {
      this._hoveredPoint = null;
      this._canvas.style.cursor = '';
      this._hideTooltip();
    }
  }

  _handleClick(e) {
    // Don't treat drag-release as a click
    if (this._dragMoved) {
      this._dragMoved = false;
      return;
    }

    const rect = this._canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const hit = this._hitTest(mx, my);

    if (!hit) return;

    // Answered dot → reanswer
    if (hit.questionId && this._onReanswer) {
      this._onReanswer(hit.questionId);
      return;
    }

    // Article → open Wikipedia
    if (hit.url) {
      window.open(hit.url, '_blank', 'noopener');
    }
  }

  _hitTest(mx, my) {
    // Convert screen coords to normalized [0,1] coords
    const normX = (mx - this._panX) / (this._zoom * this._width);
    const normY = (my - this._panY) / (this._zoom * this._height);
    const hitRadius = 8 / (this._zoom * this._width); // 8px hit area

    // Check answered dots first (on top)
    for (const d of this._answeredData) {
      const dx = d.x - normX;
      const dy = d.y - normY;
      if (Math.sqrt(dx * dx + dy * dy) < hitRadius * 1.5) {
        return { ...d, title: d.title };
      }
    }

    // Check article points
    for (const p of this._points) {
      const dx = p.x - normX;
      const dy = p.y - normY;
      if (Math.sqrt(dx * dx + dy * dy) < hitRadius) {
        return p;
      }
    }

    return null;
  }

  // Touch handling for pinch-zoom
  _handleTouchStart(e) {
    if (e.touches.length === 2) {
      e.preventDefault();
      const t0 = e.touches[0];
      const t1 = e.touches[1];
      this._lastTouchDist = Math.hypot(t1.clientX - t0.clientX, t1.clientY - t0.clientY);
      this._lastTouchCenter = {
        x: (t0.clientX + t1.clientX) / 2,
        y: (t0.clientY + t1.clientY) / 2,
      };
    } else if (e.touches.length === 1) {
      this._isDragging = true;
      this._dragMoved = false;
      this._lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }

  _handleTouchMove(e) {
    if (e.touches.length === 2 && this._lastTouchDist != null) {
      e.preventDefault();
      const t0 = e.touches[0];
      const t1 = e.touches[1];
      const dist = Math.hypot(t1.clientX - t0.clientX, t1.clientY - t0.clientY);
      const center = {
        x: (t0.clientX + t1.clientX) / 2,
        y: (t0.clientY + t1.clientY) / 2,
      };

      const rect = this._canvas.getBoundingClientRect();
      const mx = center.x - rect.left;
      const my = center.y - rect.top;

      const scale = dist / this._lastTouchDist;
      const newZoom = Math.max(1, Math.min(10, this._zoom * scale));

      if (newZoom !== this._zoom) {
        const s = newZoom / this._zoom;
        this._panX = mx - s * (mx - this._panX);
        this._panY = my - s * (my - this._panY);
        this._zoom = newZoom;
        this._clampPanZoom();
        this._render();
        this._notifyViewport();
      }

      this._lastTouchDist = dist;
      this._lastTouchCenter = center;
    } else if (e.touches.length === 1 && this._isDragging && this._lastMouse) {
      const t = e.touches[0];
      const dx = t.clientX - this._lastMouse.x;
      const dy = t.clientY - this._lastMouse.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) this._dragMoved = true;
      this._panX += dx;
      this._panY += dy;
      this._lastMouse = { x: t.clientX, y: t.clientY };
      this._clampPanZoom();
      this._render();
      this._notifyViewport();
    }
  }

  _handleTouchEnd() {
    this._isDragging = false;
    this._lastMouse = null;
    this._lastTouchDist = null;
    this._lastTouchCenter = null;
  }

  // ======== PRIVATE: Tooltip ========

  _buildTooltipHTML(hit) {
    if (hit.questionId) {
      const isCorrect = hit.isCorrect;
      const borderColor = isCorrect ? 'var(--color-correct)' : 'var(--color-incorrect)';
      const icon = isCorrect ? '✅' : '❌';
      const text = hit.title || 'Question';
      const truncated = text.length > 200 ? text.slice(0, 200) + '…' : text;
      return { html: `<div style="font-weight:600;margin-bottom:2px;">${icon} Answered</div><div style="font-size:0.73rem;color:var(--color-text-muted);">${this._escapeHtml(truncated)}</div>`, borderColor };
    }

    const title = hit.title || '';
    const excerpt = hit.excerpt || '';
    if (excerpt) {
      const truncExcerpt = excerpt.length > 150 ? excerpt.slice(0, 150) + '…' : excerpt;
      return { html: `<div style="font-weight:600;margin-bottom:2px;">${this._escapeHtml(title)}</div><div style="font-size:0.73rem;color:var(--color-text-muted);">${this._escapeHtml(truncExcerpt)}</div>`, borderColor: 'var(--color-secondary)' };
    }

    return { html: `<div style="font-weight:600;">${this._escapeHtml(title)}</div>`, borderColor: 'var(--color-border)' };
  }

  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  _showTooltip(tooltipData, x, y) {
    if (!tooltipData || !this._tooltip) return;
    this._tooltip.innerHTML = tooltipData.html;
    this._tooltip.style.borderLeftColor = tooltipData.borderColor;

    const containerW = this._width;
    const containerH = this._height;
    let left = x + 14;
    let top = y - 8;

    if (left + 340 > containerW) left = x - 350;
    if (top + 100 > containerH) top = containerH - 110;
    if (left < 0) left = 4;
    if (top < 0) top = 4;

    this._tooltip.style.left = left + 'px';
    this._tooltip.style.top = top + 'px';
    this._tooltip.style.opacity = '1';
  }

  _hideTooltip() {
    if (this._tooltip) this._tooltip.style.opacity = '0';
  }

  // ======== PRIVATE: Transitions ========

  _panFadeTransition(sourcePoints, targetPoints, targetRegion, duration, isAborted, resolve) {
    const { merged } = mergeForTransition(sourcePoints, targetPoints);
    const { startData, endData } = buildTransitionFrames(merged);

    const targetPanZoom = this._computePanZoomForRegion(targetRegion);
    const startPanX = this._panX;
    const startPanY = this._panY;
    const startZoom = this._zoom;
    const startTime = performance.now();

    // Set initial points
    this._points = startData;
    this._render();

    const animate = (now) => {
      if (isAborted()) return;

      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      const e = cubicInOut(t);

      // Interpolate points
      const interpolated = startData.map((sp, i) => {
        const ep = endData[i];
        const color = sp.color || [200, 200, 200, 100];
        const endColor = ep.color || [200, 200, 200, 100];
        return {
          ...ep,
          x: sp.x + (ep.x - sp.x) * e,
          y: sp.y + (ep.y - sp.y) * e,
          color: [
            Math.round(color[0] + (endColor[0] - color[0]) * e),
            Math.round(color[1] + (endColor[1] - color[1]) * e),
            Math.round(color[2] + (endColor[2] - color[2]) * e),
            Math.round(color[3] + (endColor[3] - color[3]) * e),
          ],
        };
      });

      // Interpolate viewport
      this._panX = startPanX + (targetPanZoom.panX - startPanX) * e;
      this._panY = startPanY + (targetPanZoom.panY - startPanY) * e;
      this._zoom = startZoom + (targetPanZoom.zoom - startZoom) * e;

      this._points = interpolated;
      this._render();

      if (t < 1) {
        this._animFrame = requestAnimationFrame(animate);
      } else {
        this._points = targetPoints;
        this._panX = targetPanZoom.panX;
        this._panY = targetPanZoom.panY;
        this._zoom = targetPanZoom.zoom;
        this._clampPanZoom();
        this._render();
        this._notifyViewport();
        this._transitionAbort = null;
        resolve();
      }
    };

    this._animFrame = requestAnimationFrame(animate);
  }

  // Smooth crossfade: viewport pans throughout, points fade at midpoint
  _crossfadeTransition(sourcePoints, targetPoints, _sourceRegion, targetRegion, duration, isAborted, resolve) {
    const startTime = performance.now();
    const targetPanZoom = this._computePanZoomForRegion(targetRegion);
    const startPanX = this._panX;
    const startPanY = this._panY;
    const startZoom = this._zoom;

    const animate = (now) => {
      if (isAborted()) return;
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      const e = cubicInOut(t);

      this._panX = startPanX + (targetPanZoom.panX - startPanX) * e;
      this._panY = startPanY + (targetPanZoom.panY - startPanY) * e;
      this._zoom = startZoom + (targetPanZoom.zoom - startZoom) * e;

      if (t < 0.5) {
        const fadeOut = 1 - (t / 0.5);
        this._points = sourcePoints.map((p) => ({
          ...p,
          color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200,
            Math.round((p.color?.[3] ?? 150) * fadeOut)],
        }));
      } else {
        const fadeIn = (t - 0.5) / 0.5;
        this._points = targetPoints.map((p) => ({
          ...p,
          color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200,
            Math.round((p.color?.[3] ?? 150) * fadeIn)],
        }));
      }

      this._render();

      if (t < 1) {
        this._animFrame = requestAnimationFrame(animate);
      } else {
        this._points = targetPoints;
        this._panX = targetPanZoom.panX;
        this._panY = targetPanZoom.panY;
        this._zoom = targetPanZoom.zoom;
        this._clampPanZoom();
        this._render();
        this._notifyViewport();
        this._transitionAbort = null;
        resolve();
      }
    };

    this._animFrame = requestAnimationFrame(animate);
  }

  _notifyViewport() {
    if (this._onViewportChange) {
      this._onViewportChange(this.getViewport());
    }
  }
}
