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
        font-size: 0.9rem;
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        border: 1px solid rgba(0,0,0,0.15);
        background-color: white;
        cursor: pointer;
        outline: none;
        transition: border-color 0.2s;
        max-width: 200px;
      }
      .domain-selector select:focus {
        border-color: var(--color-primary, #3f51b5);
      }
      .control-btn {
        min-height: 36px;
        width: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(0,0,0,0.15);
        border-radius: 4px;
        background: white;
        cursor: pointer;
        color: #555;
        font-size: 1rem;
        transition: background-color 0.2s;
      }
      .control-btn:hover {
        background-color: #f5f5f5;
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
