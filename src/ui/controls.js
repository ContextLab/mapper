/** Top-level controls for domain selection, reset, and data export. */

import { getHierarchy } from '../domain/registry.js';

let onDomainSelectCb = null;
let onResetCb = null;
let onExportCb = null;

let container = null;
let resetButton = null;
let exportButton = null;

function buildOptions() {
  const hierarchy = getHierarchy();
  const items = [];
  hierarchy.forEach(node => {
    items.push({
      value: node.id,
      label: node.id === 'all' ? 'All (General)' : node.name,
      isChild: false,
    });
    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        items.push({ value: child.id, label: child.name, isChild: true });
      });
    }
  });
  return items;
}

function createDropdown(placeholder, items, onChange) {
  const wrapper = document.createElement('div');
  wrapper.className = 'custom-select';
  wrapper.setAttribute('role', 'combobox');
  wrapper.setAttribute('aria-expanded', 'false');
  wrapper.setAttribute('aria-haspopup', 'listbox');

  const trigger = document.createElement('button');
  trigger.className = 'custom-select-trigger';
  trigger.type = 'button';

  const valueSpan = document.createElement('span');
  valueSpan.className = 'custom-select-value';
  valueSpan.textContent = placeholder;

  const arrow = document.createElement('span');
  arrow.className = 'custom-select-arrow';
  arrow.textContent = '\u25BE';

  trigger.appendChild(valueSpan);
  trigger.appendChild(arrow);

  const panel = document.createElement('div');
  panel.className = 'custom-select-options';
  panel.setAttribute('role', 'listbox');

  let focusedIdx = -1;

  for (const opt of items) {
    const el = document.createElement('div');
    el.className = 'custom-select-option' + (opt.isChild ? ' custom-select-option--child' : '');
    el.setAttribute('role', 'option');
    el.dataset.value = opt.value;
    el.textContent = opt.isChild ? '\u00A0\u00A0\u00A0' + opt.label : opt.label;
    panel.appendChild(el);
  }

  wrapper.appendChild(trigger);
  wrapper.appendChild(panel);

  function open() {
    wrapper.classList.add('open');
    wrapper.setAttribute('aria-expanded', 'true');
    focusedIdx = -1;
  }

  function close() {
    wrapper.classList.remove('open');
    wrapper.setAttribute('aria-expanded', 'false');
    focusedIdx = -1;
    panel.querySelectorAll('.focused').forEach(el => el.classList.remove('focused'));
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    wrapper.classList.contains('open') ? close() : open();
  });

  panel.addEventListener('click', (e) => {
    const item = e.target.closest('.custom-select-option');
    if (!item) return;
    valueSpan.textContent = item.textContent.trim();
    wrapper.dataset.value = item.dataset.value;
    close();
    if (onChange) onChange(item.dataset.value);
  });

  document.addEventListener('click', (e) => {
    if (!wrapper.contains(e.target)) close();
  });

  trigger.addEventListener('keydown', (e) => {
    const opts = panel.querySelectorAll('.custom-select-option');
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (wrapper.classList.contains('open') && focusedIdx >= 0) {
        opts[focusedIdx].click();
      } else {
        open();
      }
    } else if (e.key === 'Escape') {
      close();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!wrapper.classList.contains('open')) open();
      focusedIdx = Math.min(focusedIdx + 1, opts.length - 1);
      opts.forEach((o, i) => o.classList.toggle('focused', i === focusedIdx));
      opts[focusedIdx]?.scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIdx = Math.max(focusedIdx - 1, 0);
      opts.forEach((o, i) => o.classList.toggle('focused', i === focusedIdx));
      opts[focusedIdx]?.scrollIntoView({ block: 'nearest' });
    }
  });

  return wrapper;
}

export function init(headerElement) {
  const domainSelector = headerElement.querySelector('.domain-selector');
  if (!domainSelector) {
    console.error('Controls: .domain-selector not found in header');
    return;
  }
  container = domainSelector;
  container.innerHTML = '';

  container.style.display = 'flex';
  container.style.alignItems = 'center';
  container.style.gap = '0.5rem';

  if (!document.getElementById('controls-style')) {
    const style = document.createElement('style');
    style.id = 'controls-style';
    style.textContent = `
      .control-btn {
        min-height: 36px;
        width: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid var(--color-border);
        border-radius: 6px;
        background: var(--color-surface-raised);
        cursor: pointer;
        color: var(--color-text-muted);
        font-size: 1rem;
        transition: all 0.2s ease;
      }
      .control-btn:hover {
        border-color: var(--color-primary);
        color: var(--color-primary);
        box-shadow: 0 0 8px var(--color-glow-primary);
      }
      @media (max-width: 768px) {
        .header-left { flex: 1; }
        .domain-selector { flex: 1; }
      }
    `;
    document.head.appendChild(style);
  }

  const dropdown = createDropdown('Choose a domain\u2026', buildOptions(), (value) => {
    if (onDomainSelectCb) onDomainSelectCb(value);
  });
  container.appendChild(dropdown);

  resetButton = document.createElement('button');
  resetButton.className = 'control-btn';
  resetButton.ariaLabel = 'Reset all progress';
  resetButton.innerHTML = '<i class="fa-solid fa-rotate-right"></i>';
  resetButton.hidden = true;
  resetButton.addEventListener('click', () => {
    if (onResetCb) onResetCb();
  });
  container.appendChild(resetButton);

  exportButton = document.createElement('button');
  exportButton.className = 'control-btn';
  exportButton.ariaLabel = 'Export progress as JSON';
  exportButton.innerHTML = '<i class="fa-solid fa-download"></i>';
  exportButton.hidden = true;
  exportButton.addEventListener('click', () => {
    if (onExportCb) onExportCb();
  });
  container.appendChild(exportButton);

  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('mapper-theme', next);
      const icon = themeToggle.querySelector('i');
      if (icon) {
        icon.className = next === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
      }
    });
  }
}

export function onDomainSelect(callback) {
  onDomainSelectCb = callback;
}

export function onReset(callback) {
  onResetCb = callback;
}

export function onExport(callback) {
  onExportCb = callback;
}

export function showActionButtons() {
  if (container) container.hidden = false;
  if (resetButton) resetButton.hidden = false;
  if (exportButton) exportButton.hidden = false;
}

export function createLandingSelector(container, callback) {
  const dropdown = createDropdown('Choose a region to explore\u2026', buildOptions(), callback);
  dropdown.classList.add('custom-select--landing');
  container.appendChild(dropdown);
}
