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

    this._onThemeChange = () => this.render();
    document.documentElement.addEventListener('theme-changed', this._onThemeChange);

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

  _isLightMode() {
    return document.documentElement.getAttribute('data-theme') === 'light';
  }

  _heatmapColor(value, light) {
    const v = Math.max(0, Math.min(1, value));
    if (light) {
      if (v < 0.5) {
        const t = v / 0.5;
        return [
          Math.round(248 + t * (167 - 248)),
          Math.round(250 + t * (210 - 250)),
          Math.round(252 + t * (178 - 252)),
        ];
      }
      const t = (v - 0.5) / 0.5;
      return [
        Math.round(167 + t * (0 - 167)),
        Math.round(210 + t * (105 - 210)),
        Math.round(178 + t * (62 - 178)),
      ];
    }
    if (v < 0.5) {
      const t = v / 0.5;
      return [
        Math.round(15 + t * (0 - 15)),
        Math.round(23 + t * (105 - 23)),
        Math.round(42 + t * (62 - 42)),
      ];
    }
    const t = (v - 0.5) / 0.5;
    return [
      Math.round(0 + t * (255 - 0)),
      Math.round(105 + t * (160 - 105)),
      Math.round(62 + t * (15 - 62)),
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
    }, false); // drag = instant (not animated)
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
    }, true); // click = animated
  }

  render() {
    if (!this.ctx || !this.width || !this.height) return;

    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;
    const light = this._isLightMode();

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = light ? '#f8fafc' : '#0f172a';
    ctx.fillRect(0, 0, w, h);

    this._drawHeatmap(ctx, w, h, light);
    this._drawArticles(ctx, w, h, light);
    this._drawDomainOutlines(ctx, w, h, light);

    if (this.currentViewport) {
      this._drawViewportRect(ctx, w, h, light);
    }
  }

  _drawHeatmap(ctx, w, h, light) {
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

    ctx.globalAlpha = light ? 0.4 : 0.5;
    for (const e of this.estimates) {
      if (e.state === 'unknown') continue;
      const [r, g, b] = this._heatmapColor(e.value, light);
      const a = e.evidenceCount === 0 ? 0.25 : 0.7;
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;
      ctx.fillRect(rx + e.gx * cellW, ry + e.gy * cellH, cellW + 0.5, cellH + 0.5);
    }
    ctx.globalAlpha = 1;
  }

  _drawArticles(ctx, w, h, light) {
    if (this.articles.length === 0) return;

    ctx.fillStyle = light ? 'rgba(100, 116, 139, 0.25)' : 'rgba(148, 163, 184, 0.2)';
    for (const a of this.articles) {
      ctx.fillRect(a.x * w, a.y * h, 1, 1);
    }
  }

  _drawDomainOutlines(ctx, w, h, light) {
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
        ctx.strokeStyle = '#00693e';
        ctx.lineWidth = 2;
      } else if (isAll) {
        ctx.strokeStyle = light ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 0.5;
      } else {
        ctx.strokeStyle = light ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 0.5;
      }

      ctx.strokeRect(x, y, dw, dh);

      if (!isAll && dw > 25 && dh > 12) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(x, y, dw, dh);
        ctx.clip();
        ctx.fillStyle = isActive
          ? 'rgba(0, 105, 62, 0.9)'
          : (light ? 'rgba(0, 0, 0, 0.35)' : 'rgba(255, 255, 255, 0.4)');
        ctx.font = `9px ${getComputedStyle(document.documentElement).getPropertyValue('--font-body').trim() || 'sans-serif'}`;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(d.name, x + 2, y + 2);
        ctx.restore();
      }
    }
  }

  _drawViewportRect(ctx, w, h, light) {
    const { x_min, x_max, y_min, y_max } = this.currentViewport;
    const x = x_min * w;
    const y = y_min * h;
    const vw = (x_max - x_min) * w;
    const vh = (y_max - y_min) * h;

    ctx.fillStyle = light ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.06)';
    ctx.fillRect(x, y, vw, vh);

    ctx.strokeStyle = 'rgba(38, 122, 186, 0.9)';
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
    if (this._onThemeChange) {
      document.documentElement.removeEventListener('theme-changed', this._onThemeChange);
    }
    this.container = null;
    this.ctx = null;
    this.domains = [];
  }
}
