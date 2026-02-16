/** Learning insights panel: expertise, weakness, and suggested learning topics. */

let panelEl = null;
let contentEl = null;

export function init(container) {
  if (!container) return;

  if (!document.getElementById('insights-style')) {
    const style = document.createElement('style');
    style.id = 'insights-style';
    style.textContent = `
      .insights-panel { margin-top: 0.5rem; }
      .insights-section {
        margin-bottom: 1rem;
        padding: 0.75rem;
        border-radius: 8px;
        background: rgba(0,0,0,0.03);
      }
      .insights-section h3 {
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
      }
      .insights-list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .insights-list li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.3rem 0;
        font-size: 0.85rem;
        border-bottom: 1px solid rgba(0,0,0,0.06);
      }
      .insights-list li:last-child { border-bottom: none; }
      .insights-bar {
        width: 50px;
        height: 6px;
        background: rgba(0,0,0,0.1);
        border-radius: 3px;
        overflow: hidden;
        flex-shrink: 0;
        margin-left: 0.5rem;
      }
      .insights-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
      }
      .insights-empty {
        color: #888;
        font-style: italic;
        font-size: 0.85rem;
        text-align: center;
        padding: 1rem 0;
      }
    `;
    document.head.appendChild(style);
  }

  panelEl = document.createElement('div');
  panelEl.className = 'insights-panel';
  panelEl.hidden = true;
  contentEl = document.createElement('div');
  panelEl.appendChild(contentEl);
  container.appendChild(panelEl);
}

export function show(type, estimates, labels) {
  if (!panelEl || !contentEl) return;

  if (!estimates || estimates.length === 0) {
    contentEl.innerHTML = '<div class="insights-empty">Answer more questions to unlock insights.</div>';
    panelEl.hidden = false;
    return;
  }

  const labelMap = buildLabelMap(labels);
  let items = [];
  let title = '';
  let icon = '';
  let barColor = '';

  if (type === 'expertise') {
    title = 'Areas of Expertise';
    icon = 'fa-trophy';
    barColor = '#4caf50';
    items = getTopCells(estimates, 5, 'high');
  } else if (type === 'weakness') {
    title = 'Areas of Weakness';
    icon = 'fa-arrow-trend-down';
    barColor = '#f44336';
    items = getTopCells(estimates, 5, 'low');
  } else if (type === 'suggested') {
    title = 'Suggested Learning';
    icon = 'fa-lightbulb';
    barColor = '#ff9800';
    items = getTopCells(estimates, 5, 'mid');
  }

  if (items.length === 0) {
    contentEl.innerHTML = '<div class="insights-empty">Not enough data yet. Keep answering questions!</div>';
    panelEl.hidden = false;
    return;
  }

  const section = document.createElement('div');
  section.className = 'insights-section';

  const heading = document.createElement('h3');
  heading.innerHTML = `<i class="fa-solid ${icon}" style="color: ${barColor}"></i> ${title}`;
  section.appendChild(heading);

  const list = document.createElement('ul');
  list.className = 'insights-list';

  for (const item of items) {
    const label = labelMap.get(`${item.gx},${item.gy}`) || `Cell (${item.gx}, ${item.gy})`;
    const li = document.createElement('li');
    const pct = Math.round(item.value * 100);

    li.innerHTML = `
      <span>${label}</span>
      <span style="display:flex;align-items:center;gap:0.3rem;">
        <span style="font-size:0.75rem;color:#888;">${pct}%</span>
        <span class="insights-bar">
          <span class="insights-bar-fill" style="width:${pct}%;background:${barColor};"></span>
        </span>
      </span>
    `;
    list.appendChild(li);
  }

  section.appendChild(list);
  contentEl.innerHTML = '';
  contentEl.appendChild(section);
  panelEl.hidden = false;
}

export function hide() {
  if (panelEl) panelEl.hidden = true;
}

function buildLabelMap(labels) {
  const map = new Map();
  if (!labels) return map;
  for (const l of labels) {
    map.set(`${l.gx},${l.gy}`, l.label);
  }
  return map;
}

function getTopCells(estimates, count, type) {
  const withEvidence = estimates.filter((e) => e.evidenceCount > 0);
  if (withEvidence.length === 0) return [];

  let sorted;
  if (type === 'high') {
    sorted = [...withEvidence].sort((a, b) => b.value - a.value);
  } else if (type === 'low') {
    sorted = [...withEvidence].sort((a, b) => a.value - b.value);
  } else {
    // 'mid' — cells closest to 0.5 value with moderate uncertainty (best learning ROI)
    sorted = [...withEvidence].sort((a, b) => {
      const aMidDist = Math.abs(a.value - 0.5) - a.uncertainty * 0.3;
      const bMidDist = Math.abs(b.value - 0.5) - b.uncertainty * 0.3;
      return aMidDist - bMidDist;
    });
  }

  return sorted.slice(0, count);
}
