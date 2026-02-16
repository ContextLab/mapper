/** Hierarchical domain minimap with active domain highlighting and viewport indicator. */

export class Minimap {
  constructor() {
    this.container = null;
    this.canvas = null;
    this.ctx = null;
    this.domains = [];
    this.activeDomainId = null;
    this.currentViewport = null;
    this.clickHandler = null;
    this.width = 0;
    this.height = 0;
    
    this.handleClick = this.handleClick.bind(this);
  }

  init(container, domains) {
    this.container = container;
    this.domains = domains;

    this.canvas = document.createElement('canvas');
    this.canvas.style.display = 'block';
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    this.container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    this.resize();

    this.canvas.addEventListener('click', this.handleClick);
    
    this.render();
  }

  resize() {
    if (!this.container || !this.canvas) return;
    
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    
    this.ctx.scale(dpr, dpr);
    
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

  onClick(handler) {
    this.clickHandler = handler;
  }

  handleClick(e) {
    if (!this.clickHandler || !this.width || !this.height) return;

    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    const matches = this.domains.filter(d => {
      if (!d.region) return false;
      const { x_min, x_max, y_min, y_max } = d.region;
      return x >= x_min && x <= x_max && y >= y_min && y <= y_max;
    });

    if (matches.length === 0) return;

    // Sort by area ascending (smallest first) to pick specific sub-domains over parents
    matches.sort((a, b) => {
      const areaA = (a.region.x_max - a.region.x_min) * (a.region.y_max - a.region.y_min);
      const areaB = (b.region.x_max - b.region.x_min) * (b.region.y_max - b.region.y_min);
      return areaA - areaB;
    });

    this.clickHandler(matches[0].id);
  }

  render() {
    if (!this.ctx) return;

    this.ctx.clearRect(0, 0, this.width, this.height);
    
    this.ctx.fillStyle = '#1a1a2e';
    this.ctx.fillRect(0, 0, this.width, this.height);

    // Sort domains by area descending so we draw large ones first (backgrounds)
    const sortedDomains = [...this.domains].sort((a, b) => {
      const areaA = (a.region ? (a.region.x_max - a.region.x_min) * (a.region.y_max - a.region.y_min) : 0);
      const areaB = (b.region ? (b.region.x_max - b.region.x_min) * (b.region.y_max - b.region.y_min) : 0);
      return areaB - areaA;
    });

    for (const d of sortedDomains) {
      this.drawDomain(d);
    }

    if (this.currentViewport) {
      this.drawViewport(this.currentViewport);
    }
  }

  drawDomain(domain) {
    if (!domain.region) return;

    const { x_min, x_max, y_min, y_max } = domain.region;
    
    const x = x_min * this.width;
    const y = y_min * this.height;
    const w = (x_max - x_min) * this.width;
    const h = (y_max - y_min) * this.height;
    
    const isActive = domain.id === this.activeDomainId;
    const isAll = domain.id === 'all';

    this.ctx.save();

    if (isActive) {
      this.ctx.strokeStyle = '#f50057';
      this.ctx.lineWidth = 2;
      this.ctx.fillStyle = 'rgba(245, 0, 87, 0.15)';
    } else if (isAll) {
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
      this.ctx.lineWidth = 1;
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
    } else {
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      this.ctx.lineWidth = 1;
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
    }

    this.ctx.fillRect(x, y, w, h);
    this.ctx.strokeRect(x, y, w, h);

    // Don't label 'all' to avoid clutter
    if (!isAll) {
      this.ctx.fillStyle = isActive ? '#f50057' : 'rgba(255, 255, 255, 0.6)';
      this.ctx.font = '8px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.textAlign = 'left';
      this.ctx.textBaseline = 'top';
      
      this.ctx.beginPath();
      this.ctx.rect(x, y, w, h);
      this.ctx.clip();
      
      if (w > 20 && h > 10) {
        this.ctx.fillText(domain.name, x + 3, y + 3);
      }
    }
    
    this.ctx.restore();
  }

  drawViewport(viewport) {
    const { x_min, x_max, y_min, y_max } = viewport;
    
    const x = x_min * this.width;
    const y = y_min * this.height;
    const w = (x_max - x_min) * this.width;
    const h = (y_max - y_min) * this.height;

    this.ctx.save();
    this.ctx.strokeStyle = '#ffffff';
    this.ctx.lineWidth = 1.5;
    this.ctx.setLineDash([3, 3]);
    this.ctx.strokeRect(x, y, w, h);
    this.ctx.restore();
  }

  destroy() {
    if (this.canvas) {
      this.canvas.removeEventListener('click', this.handleClick);
      this.canvas.remove();
      this.canvas = null;
    }
    this.container = null;
    this.ctx = null;
    this.domains = [];
  }
}
