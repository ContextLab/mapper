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

    this._handleMouseDown = this._onMouseDown.bind(this);
    this._handleMouseMove = this._onMouseMove.bind(this);
    this._handleMouseUp = this._onMouseUp.bind(this);
    this._handleClick = this._onClick.bind(this);
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

    this.canvas.addEventListener('mousedown', this._handleMouseDown);
    this.canvas.addEventListener('click', this._handleClick);
    window.addEventListener('mousemove', this._handleMouseMove);
    window.addEventListener('mouseup', this._handleMouseUp);

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

  _synthwaveColor(value) {
    const v = Math.max(0, Math.min(1, value));
    if (v < 0.5) {
      const t = v / 0.5;
      return [
        Math.round(61 + t * 194),
        Math.round(21 + t * 105),
        Math.round(96 + t * 123),
      ];
    }
    const t = (v - 0.5) / 0.5;
    return [
      Math.round(255 - t * 201),
      Math.round(126 + t * 123),
      Math.round(219 + t * 27),
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
    }
  }

  _onMouseMove(e) {
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
    });
  }

  _onMouseUp() {
    if (this._isDragging) {
      this._isDragging = false;
      this._dragOffset = null;
      this.canvas.style.cursor = 'pointer';
    }
  }

  _onClick(e) {
    if (this._isDragging) return;
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
    });
  }

  render() {
    if (!this.ctx || !this.width || !this.height) return;

    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#1a1525';
    ctx.fillRect(0, 0, w, h);

    this._drawHeatmap(ctx, w, h);
    this._drawArticles(ctx, w, h);
    this._drawDomainOutlines(ctx, w, h);

    if (this.currentViewport) {
      this._drawViewportRect(ctx, w, h);
    }
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

    ctx.globalAlpha = 0.5;
    for (const e of this.estimates) {
      if (e.state === 'unknown') continue;
      const [r, g, b] = this._synthwaveColor(e.value);
      const a = e.evidenceCount === 0 ? 0.25 : 0.7;
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;
      ctx.fillRect(rx + e.gx * cellW, ry + e.gy * cellH, cellW + 0.5, cellH + 0.5);
    }
    ctx.globalAlpha = 1;
  }

  _drawArticles(ctx, w, h) {
    if (this.articles.length === 0) return;

    ctx.fillStyle = 'rgba(180, 180, 220, 0.25)';
    for (const a of this.articles) {
      ctx.fillRect(a.x * w, a.y * h, 1, 1);
    }
  }

  _drawDomainOutlines(ctx, w, h) {
    const sorted = [...this.domains].sort((a, b) => {
      const areaA = a.region ? (a.region.x_max - a.region.x_min) * (a.region.y_max - a.region.y_min) : 0;
      const areaB = b.region ? (b.region.x_max - b.region.x_min) * (b.region.y_max - b.region.y_min) : 0;
      return areaB - areaA;
    });

    for (const d of sorted) {
      if (!d.region) continue;
      const { x_min, x_max, y_min, y_max } = d.region;
      const x = x_min * w;
      const y = y_min * h;
      const dw = (x_max - x_min) * w;
      const dh = (y_max - y_min) * h;

      const isActive = d.id === this.activeDomainId;
      const isAll = d.id === 'all';

      if (isActive) {
        ctx.strokeStyle = 'var(--color-primary, #ff7edb)';
        ctx.lineWidth = 2;
      } else if (isAll) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 0.5;
      } else {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 0.5;
      }

      ctx.strokeRect(x, y, dw, dh);

      if (!isAll && dw > 25 && dh > 12) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(x, y, dw, dh);
        ctx.clip();
        ctx.fillStyle = isActive ? 'rgba(255, 126, 219, 0.8)' : 'rgba(255, 255, 255, 0.4)';
        ctx.font = '9px "Space Mono", monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(d.name, x + 2, y + 2);
        ctx.restore();
      }
    }
  }

  _drawViewportRect(ctx, w, h) {
    const { x_min, x_max, y_min, y_max } = this.currentViewport;
    const x = x_min * w;
    const y = y_min * h;
    const vw = (x_max - x_min) * w;
    const vh = (y_max - y_min) * h;

    ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.fillRect(x, y, vw, vh);

    ctx.strokeStyle = 'rgba(54, 249, 246, 0.9)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([]);
    ctx.strokeRect(x, y, vw, vh);
  }

  destroy() {
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
