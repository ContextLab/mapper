/** Top-level controls for domain selection, reset, and data export. */

import { getHierarchy } from '../domain/registry.js';

let onDomainSelectCb = null;
let onResetCb = null;
let onExportCb = null;

let container = null;
let selectElement = null;
let resetButton = null;
let exportButton = null;

/**
 * Initialize the domain selector in the header.
 * @param {HTMLElement} headerElement
 */
export function init(headerElement) {
  const domainSelector = headerElement.querySelector('.domain-selector');
  if (!domainSelector) {
    console.error('Controls: .domain-selector not found in header');
    return;
  }
  container = domainSelector;

  container.innerHTML = '';
  container.hidden = false;
  
  container.style.display = 'flex';
  container.style.alignItems = 'center';
  container.style.gap = '0.5rem';

  if (!document.getElementById('controls-style')) {
    const style = document.createElement('style');
    style.id = 'controls-style';
    style.textContent = `
      .domain-selector select {
        font-family: var(--font-body);
        font-size: 0.85rem;
        padding: 0.4rem 2rem 0.4rem 0.6rem;
        border-radius: 6px;
        border: 1px solid var(--color-border);
        background-color: var(--color-surface-raised);
        color: var(--color-text);
        cursor: pointer;
        outline: none;
        transition: border-color 0.2s, box-shadow 0.2s;
        max-width: 220px;
        appearance: none;
        -webkit-appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23848bb2' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 0.5rem center;
      }
      .domain-selector select:focus {
        border-color: var(--color-primary);
        box-shadow: 0 0 8px var(--color-glow-primary);
      }
      .domain-selector select option {
        background: var(--color-surface);
        color: var(--color-text);
      }
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
        .header-left {
          flex: 1;
        }
        .domain-selector {
          flex: 1;
        }
        .domain-selector select {
          width: 100%;
          max-width: none;
        }
      }
    `;
    document.head.appendChild(style);
  }

  selectElement = document.createElement('select');
  selectElement.ariaLabel = 'Select Domain';
  
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Choose a domain…';
  placeholder.disabled = true;
  placeholder.selected = true;
  selectElement.appendChild(placeholder);

  const hierarchy = getHierarchy();
  
  hierarchy.forEach(node => {
    const option = document.createElement('option');
    option.value = node.id;
    option.textContent = node.id === 'all' ? 'All (General)' : node.name;
    selectElement.appendChild(option);

    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        const childOption = document.createElement('option');
        childOption.value = child.id;
        childOption.textContent = `\u00A0\u00A0\u00A0${child.name}`;
        selectElement.appendChild(childOption);
      });
    }
  });

  selectElement.addEventListener('change', (e) => {
    if (onDomainSelectCb) {
      onDomainSelectCb(e.target.value);
    }
  });

  container.appendChild(selectElement);

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
  if (resetButton) resetButton.hidden = false;
  if (exportButton) exportButton.hidden = false;
}

/**
 * Create a prominent domain selector for the landing page.
 * @param {HTMLElement} container - The landing wrapper element
 * @param {function} callback - Called with domainId when selection changes
 */
export function createLandingSelector(container, callback) {
  const select = document.createElement('select');
  select.ariaLabel = 'Select knowledge domain';

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Choose an area to explore\u2026';
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  const hierarchy = getHierarchy();

  hierarchy.forEach(node => {
    const option = document.createElement('option');
    option.value = node.id;
    option.textContent = node.id === 'all' ? 'All (General)' : node.name;
    select.appendChild(option);

    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        const childOption = document.createElement('option');
        childOption.value = child.id;
        childOption.textContent = '\u00A0\u00A0\u00A0' + child.name;
        select.appendChild(childOption);
      });
    }
  });

  select.addEventListener('change', (e) => {
    if (e.target.value) callback(e.target.value);
  });

  container.appendChild(select);
}
