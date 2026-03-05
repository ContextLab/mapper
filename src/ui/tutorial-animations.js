// Tutorial inline SVG animation components
// Each function returns a DOM element with CSS crossfade frames
// All SVG content is static (no user input) — safe hardcoded markup

const COLORS = {
  gray: '#2a2a3e',
  green: '#00693e',
  greenLight: '#4CAF50',
  red: '#9d162e',
  redLight: '#ef4444',
};

function svgEl(tag, attrs, children) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  if (children) for (const c of children) el.appendChild(c);
  return el;
}

function makeFrame(active) {
  const div = document.createElement('div');
  div.className = 'tutorial-svg-frame' + (active ? ' active' : '');
  Object.assign(div.style, { position: 'absolute', top: '0', left: '0', width: '100%', height: '100%' });
  return div;
}

function animateFrames(container, intervalMs) {
  let current = 0;
  const frames = container.querySelectorAll('.tutorial-svg-frame');
  const id = setInterval(() => {
    frames[current].classList.remove('active');
    current = (current + 1) % frames.length;
    frames[current].classList.add('active');
  }, intervalMs);
  container._cleanup = () => clearInterval(id);
}

/** T026: Map evolution — 200x120px, 3 frames: gray → green → green+red */
export function createMapEvolution() {
  const container = document.createElement('div');
  container.className = 'tutorial-svg-animation';
  Object.assign(container.style, { position: 'relative', width: '200px', height: '120px' });

  const makeMapSvg = (regions) => {
    const svg = svgEl('svg', { viewBox: '0 0 200 120', width: '200', height: '120' });
    svg.appendChild(svgEl('rect', { width: '200', height: '120', fill: COLORS.gray, rx: '4' }));
    for (const r of regions) {
      svg.appendChild(svgEl('ellipse', { cx: r.cx, cy: r.cy, rx: r.rx, ry: r.ry, fill: r.fill, opacity: r.opacity }));
    }
    // Grid dots
    for (let x = 10; x < 200; x += 20) {
      for (let y = 10; y < 120; y += 20) {
        svg.appendChild(svgEl('circle', { cx: x, cy: y, r: '1', fill: COLORS.gray, opacity: '0.3' }));
      }
    }
    return svg;
  };

  const frameDefs = [
    [], // Frame 1: empty
    [ // Frame 2: green
      { cx: 70, cy: 50, rx: 45, ry: 35, fill: COLORS.green, opacity: '0.7' },
      { cx: 70, cy: 50, rx: 25, ry: 20, fill: COLORS.greenLight, opacity: '0.5' },
    ],
    [ // Frame 3: green + red
      { cx: 70, cy: 50, rx: 45, ry: 35, fill: COLORS.green, opacity: '0.7' },
      { cx: 70, cy: 50, rx: 25, ry: 20, fill: COLORS.greenLight, opacity: '0.5' },
      { cx: 150, cy: 75, rx: 35, ry: 28, fill: COLORS.red, opacity: '0.6' },
      { cx: 150, cy: 75, rx: 18, ry: 14, fill: COLORS.redLight, opacity: '0.4' },
    ],
  ];

  frameDefs.forEach((regions, i) => {
    const frame = makeFrame(i === 0);
    frame.appendChild(makeMapSvg(regions));
    container.appendChild(frame);
  });

  animateFrames(container, 1500);
  return container;
}

/** T027: Minimap animation — 80x80px, viewport rectangle moving */
export function createMinimapAnimation() {
  const container = document.createElement('div');
  container.className = 'tutorial-svg-animation';
  Object.assign(container.style, { width: '80px', height: '80px' });

  const svg = svgEl('svg', { viewBox: '0 0 80 80', width: '80', height: '80' });
  svg.appendChild(svgEl('rect', { width: '80', height: '80', fill: COLORS.gray, rx: '4' }));

  // Scatter dots
  const seed = [12,8,55,22,70,35,40,60,15,50,68,28,45,18,62,33,7,48,25,58];
  for (let i = 0; i < seed.length; i += 2) {
    svg.appendChild(svgEl('circle', { cx: seed[i], cy: seed[i + 1], r: '1.5', fill: '#555', opacity: '0.6' }));
  }

  const viewport = svgEl('rect', { x: '5', y: '5', width: '25', height: '25', fill: 'none', stroke: '#6C63FF', 'stroke-width': '1.5', rx: '2' });
  const anim = svgEl('animateTransform', {
    attributeName: 'transform', type: 'translate',
    values: '0,0; 30,0; 30,30; 0,30; 0,0',
    dur: '4s', repeatCount: 'indefinite',
    calcMode: 'spline',
    keySplines: '0.2 0 0 1; 0.2 0 0 1; 0.2 0 0 1; 0.2 0 0 1',
  });
  viewport.appendChild(anim);
  svg.appendChild(viewport);

  container.appendChild(svg);
  return container;
}

/** T028: Feature highlight — button tap → panel open, 120x60px */
export function createFeatureHighlight() {
  const container = document.createElement('div');
  container.className = 'tutorial-svg-animation';
  Object.assign(container.style, { position: 'relative', width: '120px', height: '60px' });

  // Frame 1: Button
  const svg1 = svgEl('svg', { viewBox: '0 0 120 60', width: '120', height: '60' });
  svg1.appendChild(svgEl('rect', { x: '30', y: '20', width: '60', height: '20', rx: '6', fill: '#6C63FF', opacity: '0.9' }));
  const txt = svgEl('text', { x: '60', y: '34', 'text-anchor': 'middle', fill: '#fff', 'font-size': '10', 'font-family': 'sans-serif' });
  txt.textContent = 'Tap';
  svg1.appendChild(txt);

  const f1 = makeFrame(true);
  f1.appendChild(svg1);
  container.appendChild(f1);

  // Frame 2: Panel
  const svg2 = svgEl('svg', { viewBox: '0 0 120 60', width: '120', height: '60' });
  svg2.appendChild(svgEl('rect', { x: '10', y: '5', width: '100', height: '50', rx: '6', fill: '#1e293b', stroke: '#334155', 'stroke-width': '1' }));
  svg2.appendChild(svgEl('rect', { x: '16', y: '12', width: '40', height: '4', rx: '2', fill: '#475569' }));
  svg2.appendChild(svgEl('rect', { x: '16', y: '20', width: '60', height: '3', rx: '1.5', fill: '#334155' }));
  svg2.appendChild(svgEl('rect', { x: '16', y: '27', width: '55', height: '3', rx: '1.5', fill: '#334155' }));
  svg2.appendChild(svgEl('rect', { x: '16', y: '34', width: '45', height: '3', rx: '1.5', fill: '#334155' }));

  const f2 = makeFrame(false);
  f2.appendChild(svg2);
  container.appendChild(f2);

  animateFrames(container, 1200);
  return container;
}
