/**
 * Canvas 2D particle system for landing page background.
 * Renders article coordinates as particles with spring-return
 * and mouse-repulsion physics.
 */

const PARTICLE_COUNT = 3000;
const SPRING = 0.012;
const FRICTION = 0.94;
const REPEL_RADIUS = 100;
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
    this._onMouseMove = this._onMouseMove.bind(this);
    this._onMouseLeave = this._onMouseLeave.bind(this);
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

    try {
      const url = `${basePath}data/domains/all.json`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
      const bundle = await res.json();
      const articles = bundle.articles || [];
      this._initParticles(articles);
      this.running = true;
      this.raf = requestAnimationFrame(this._tick);
    } catch (err) {
      console.warn('[particles] Could not load article data:', err);
    }
  }

  _initParticles(articles) {
    const shuffled = articles.length > PARTICLE_COUNT
      ? articles.sort(() => Math.random() - 0.5).slice(0, PARTICLE_COUNT)
      : [...articles];

    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);

    this.particles = shuffled.map(a => {
      const px = (a.x || Math.random()) * w;
      const py = (a.y || Math.random()) * h;
      return {
        x: px,
        y: py,
        homeX: px,
        homeY: py,
        pctX: a.x || Math.random(),
        pctY: a.y || Math.random(),
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
      p.homeX = p.pctX * w;
      p.homeY = p.pctY * h;
      p.x = p.homeX + (p.x - p.homeX) * 0.3;
      p.y = p.homeY + (p.y - p.homeY) * 0.3;
    }
  }

  _onMouseMove(e) {
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

  _tick() {
    if (!this.running) return;
    this._update();
    this._draw();
    this.raf = requestAnimationFrame(this._tick);
  }

  _update() {
    const mx = this.mouse.x;
    const my = this.mouse.y;
    const rSq = REPEL_RADIUS * REPEL_RADIUS;

    for (const p of this.particles) {
      p.vx += (p.homeX - p.x) * SPRING;
      p.vy += (p.homeY - p.y) * SPRING;

      if (this.mouse.active) {
        const dx = p.x - mx;
        const dy = p.y - my;
        const distSq = dx * dx + dy * dy;
        if (distSq < rSq && distSq > 1) {
          const dist = Math.sqrt(distSq);
          const force = (1 - dist / REPEL_RADIUS) * REPEL_FORCE;
          p.vx += (dx / dist) * force;
          p.vy += (dy / dist) * force;
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

    for (const level of levels) {
      if (level.particles.length === 0) continue;
      ctx.fillStyle = `rgba(255, 126, 219, ${level.alpha})`;
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
    }
    window.removeEventListener('resize', this._onResize);
    this.particles = [];
    this.canvas = null;
    this.ctx = null;
  }
}
