/**
 * Canvas 2D particle system for landing page background.
 * Renders article coordinates as particles with spring-return
 * and mouse-repulsion physics.
 */

const PARTICLE_COUNT = 2500;
const SPRING = 0.012;
const FRICTION = 0.94;
const REPEL_RADIUS = 10;
const REPEL_FORCE = 4;
const PARTICLE_SIZE = 1.5;

export class ParticleSystem {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.particles = [];
    this.mouse = { x: -9999, y: -9999, active: false };
    this.running = false;
    this.raf = null;

    this.viewX = 0;
    this.viewY = 0;
    this.viewW = 1;
    this.viewH = 1;

    // Particle bounding box (computed from data)
    this._boundsMinX = 0;
    this._boundsMaxX = 1;
    this._boundsMinY = 0;
    this._boundsMaxY = 1;

    this._dragging = false;
    this._dragStartX = 0;
    this._dragStartY = 0;
    this._dragStartViewX = 0;
    this._dragStartViewY = 0;

    this._onMouseMove = this._onMouseMove.bind(this);
    this._onMouseLeave = this._onMouseLeave.bind(this);
    this._onMouseDown = this._onMouseDown.bind(this);
    this._onMouseUp = this._onMouseUp.bind(this);
    this._onWheel = this._onWheel.bind(this);
    this._onResize = this._onResize.bind(this);
    this._tick = this._tick.bind(this);
  }

  async init(canvas, basePath) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this._onResize();

    window.addEventListener('resize', this._onResize);
    canvas.addEventListener('mousemove', this._onMouseMove);
    canvas.addEventListener('mouseleave', this._onMouseLeave);
    canvas.addEventListener('mousedown', this._onMouseDown);
    canvas.addEventListener('wheel', this._onWheel, { passive: false });
    window.addEventListener('mouseup', this._onMouseUp);
    canvas.style.cursor = 'grab';

    try {
      const url = `${basePath}data/domains/all.json`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
      const bundle = await res.json();
      const articles = bundle.articles || [];

      // Also load video catalog and merge window coordinates as particles
      let videoPoints = [];
      try {
        const vRes = await fetch(`${basePath}data/videos/catalog.json`);
        if (vRes.ok) {
          const videos = await vRes.json();
          for (const v of videos) {
            if (!v.windows) continue;
            for (const [x, y] of v.windows) {
              videoPoints.push({ x, y });
            }
          }
        }
      } catch { /* video catalog optional */ }

      this._initParticles(articles, videoPoints);
      this.running = true;
      this.raf = requestAnimationFrame(this._tick);
    } catch (err) {
      console.warn('[particles] Could not load article data:', err);
    }
  }

  _initParticles(articles, videoPoints = []) {
    // Subsample with balanced representation: articles get at least 70% of slots
    const articlePts = articles.map(a => ({ x: a.x || Math.random(), y: a.y || Math.random() }));
    const videoPts = videoPoints.map(v => ({ x: v.x, y: v.y }));

    let shuffled;
    const total = articlePts.length + videoPts.length;
    if (total <= PARTICLE_COUNT) {
      shuffled = [...articlePts, ...videoPts];
    } else {
      // Articles get 70% of budget, videos 30% (prevents video-dominated clustering)
      const artBudget = Math.min(articlePts.length, Math.floor(PARTICLE_COUNT * 0.7));
      const vidBudget = Math.min(videoPts.length, PARTICLE_COUNT - artBudget);
      const artSample = articlePts.sort(() => Math.random() - 0.5).slice(0, artBudget);
      const vidSample = videoPts.sort(() => Math.random() - 0.5).slice(0, vidBudget);
      shuffled = [...artSample, ...vidSample].sort(() => Math.random() - 0.5);
    }

    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    const rawParticles = shuffled.map(a => {
      const pctX = a.x;
      const pctY = a.y;
      if (pctX < minX) minX = pctX;
      if (pctX > maxX) maxX = pctX;
      if (pctY < minY) minY = pctY;
      if (pctY > maxY) maxY = pctY;
      return { pctX, pctY };
    });

    this._boundsMinX = minX;
    this._boundsMaxX = maxX;
    this._boundsMinY = minY;
    this._boundsMaxY = maxY;

    this.viewX = this._boundsMinX;
    this.viewY = this._boundsMinY;
    this.viewW = this._boundsMaxX - this._boundsMinX || 1;
    this.viewH = this._boundsMaxY - this._boundsMinY || 1;

    this.particles = rawParticles.map(({ pctX, pctY }) => {
      const px = ((pctX - this.viewX) / this.viewW) * w;
      const py = ((pctY - this.viewY) / this.viewH) * h;
      return {
        x: px,
        y: py,
        homeX: px,
        homeY: py,
        pctX,
        pctY,
        vx: 0,
        vy: 0,
        alpha: 0.15 + Math.random() * 0.4,
      };
    });
  }

  _onResize() {
    if (!this.canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const parent = this.canvas.parentElement;
    if (!parent) return;
    const rect = parent.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';

    const w = rect.width;
    const h = rect.height;
    for (const p of this.particles) {
      p.homeX = ((p.pctX - this.viewX) / this.viewW) * w;
      p.homeY = ((p.pctY - this.viewY) / this.viewH) * h;
      p.x = p.homeX + (p.x - p.homeX) * 0.3;
      p.y = p.homeY + (p.y - p.homeY) * 0.3;
    }
  }

  _onMouseMove(e) {
    if (this._dragging) {
      const rect = this.canvas.getBoundingClientRect();
      const dx = (e.clientX - this._dragStartX) / rect.width * this.viewW;
      const dy = (e.clientY - this._dragStartY) / rect.height * this.viewH;
      this.viewX = this._dragStartViewX - dx;
      this.viewY = this._dragStartViewY - dy;
      this._clampView();
      this._updateHomePositions();
      return;
    }
    const rect = this.canvas.getBoundingClientRect();
    this.mouse.x = e.clientX - rect.left;
    this.mouse.y = e.clientY - rect.top;
    this.mouse.active = true;
  }

  _onMouseLeave() {
    this.mouse.active = false;
    this.mouse.x = -9999;
    this.mouse.y = -9999;
  }

  _onMouseDown(e) {
    this._dragging = true;
    this._dragStartX = e.clientX;
    this._dragStartY = e.clientY;
    this._dragStartViewX = this.viewX;
    this._dragStartViewY = this.viewY;
    this.mouse.active = false;
    this.canvas.style.cursor = 'grabbing';
    e.preventDefault();
  }

  _onMouseUp() {
    if (this._dragging) {
      this._dragging = false;
      if (this.canvas) this.canvas.style.cursor = 'grab';
    }
  }

  _onWheel(e) {
    e.preventDefault();
    const rect = this.canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;

    const worldX = this.viewX + mx * this.viewW;
    const worldY = this.viewY + my * this.viewH;

    const maxW = this._boundsMaxX - this._boundsMinX;
    const maxH = this._boundsMaxY - this._boundsMinY;
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    const newW = Math.min(maxW, Math.max(0.05, this.viewW * factor));
    const newH = Math.min(maxH, Math.max(0.05, this.viewH * factor));

    this.viewX = worldX - mx * newW;
    this.viewY = worldY - my * newH;
    this.viewW = newW;
    this.viewH = newH;

    this._clampView();
    this._updateHomePositions();
  }

  _clampView() {
    this.viewX = Math.max(this._boundsMinX, Math.min(this._boundsMaxX - this.viewW, this.viewX));
    this.viewY = Math.max(this._boundsMinY, Math.min(this._boundsMaxY - this.viewH, this.viewY));
  }

  _updateHomePositions() {
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    for (const p of this.particles) {
      p.homeX = ((p.pctX - this.viewX) / this.viewW) * w;
      p.homeY = ((p.pctY - this.viewY) / this.viewH) * h;
      p.x = p.homeX;
      p.y = p.homeY;
      p.vx = 0;
      p.vy = 0;
    }
  }

  _tick() {
    if (!this.running) return;
    this._update();
    this._draw();
    this.raf = requestAnimationFrame(this._tick);
  }

  _update() {
    const mx = this.mouse.x;
    const my = this.mouse.y;

    // Scale repel radius with zoom: larger when zoomed out (dense clusters),
    // smaller when zoomed in (particles are spread out)
    const fullW = this._boundsMaxX - this._boundsMinX || 1;
    const zoomLevel = this.viewW / fullW; // 1.0 = default, <1 = zoomed in
    const r = REPEL_RADIUS * (1 + zoomLevel); // 20px at default, ~13px at 3x zoom
    const rSq = r * r;

    for (const p of this.particles) {
      // Compute effective home: shift away from cursor so spring cooperates with repulsion
      let hx = p.homeX;
      let hy = p.homeY;

      if (this.mouse.active) {
        const hdx = hx - mx;
        const hdy = hy - my;
        const hDistSq = hdx * hdx + hdy * hdy;
        if (hDistSq < rSq) {
          const hDist = Math.sqrt(hDistSq);
          if (hDist < 0.5) {
            const angle = p._repelAngle || (p._repelAngle = Math.random() * Math.PI * 2);
            hx = mx + Math.cos(angle) * r;
            hy = my + Math.sin(angle) * r;
          } else {
            hx = mx + (hdx / hDist) * r;
            hy = my + (hdy / hDist) * r;
          }
        }
      } else {
        p._repelAngle = 0;
      }

      p.vx += (hx - p.x) * SPRING;
      p.vy += (hy - p.y) * SPRING;

      if (this.mouse.active) {
        const dx = p.x - mx;
        const dy = p.y - my;
        const distSq = dx * dx + dy * dy;
        if (distSq < rSq) {
          const dist = Math.sqrt(distSq);
          if (dist < 0.5) {
            const angle = p._repelAngle || Math.random() * Math.PI * 2;
            p.vx += Math.cos(angle) * REPEL_FORCE;
            p.vy += Math.sin(angle) * REPEL_FORCE;
          } else {
            const force = (1 - dist / r) * REPEL_FORCE;
            p.vx += (dx / dist) * force;
            p.vy += (dy / dist) * force;
          }
        }
      }

      p.vx *= FRICTION;
      p.vy *= FRICTION;
      p.x += p.vx;
      p.y += p.vy;
    }
  }

  _draw() {
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    const ctx = this.ctx;

    ctx.clearRect(0, 0, w, h);

    const levels = [
      { alpha: 0.2, particles: [] },
      { alpha: 0.35, particles: [] },
      { alpha: 0.55, particles: [] },
    ];
    for (const p of this.particles) {
      if (p.alpha < 0.25) levels[0].particles.push(p);
      else if (p.alpha < 0.45) levels[1].particles.push(p);
      else levels[2].particles.push(p);
    }

    const r = 0;
    const g = 105;
    const b = 62;

    for (const level of levels) {
      if (level.particles.length === 0) continue;
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${level.alpha})`;
      ctx.beginPath();
      for (const p of level.particles) {
        if (p.x < -10 || p.x > w + 10 || p.y < -10 || p.y > h + 10) continue;
        ctx.rect(p.x, p.y, PARTICLE_SIZE, PARTICLE_SIZE);
      }
      ctx.fill();
    }
  }

  destroy() {
    this.running = false;
    if (this.raf) {
      cancelAnimationFrame(this.raf);
      this.raf = null;
    }
    if (this.canvas) {
      this.canvas.removeEventListener('mousemove', this._onMouseMove);
      this.canvas.removeEventListener('mouseleave', this._onMouseLeave);
      this.canvas.removeEventListener('mousedown', this._onMouseDown);
      this.canvas.removeEventListener('wheel', this._onWheel);
    }
    window.removeEventListener('mouseup', this._onMouseUp);
    window.removeEventListener('resize', this._onResize);
    this.particles = [];
    this.canvas = null;
    this.ctx = null;
  }
}
