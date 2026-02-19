/**
 * Feature detection for unsupported browsers (T066)
 * Detects critical features and shows fallback message if any are missing
 * Runs as a regular script (not type="module") to work even if ES modules fail
 */

(function() {
  'use strict';

  // Feature detection checks
  const features = {
    esModules: () => 'noModule' in HTMLScriptElement.prototype,
    canvas2d: () => {
      try {
        const canvas = document.createElement('canvas');
        return canvas.getContext('2d') !== null;
      } catch (e) {
        return false;
      }
    },
    localStorage: () => {
      try {
        const test = '__feature_test__';
        localStorage.setItem(test, test);
        localStorage.removeItem(test);
        return true;
      } catch (e) {
        return false;
      }
    },
    cssCustomProperties: () => {
      try {
        const el = document.createElement('div');
        el.style.setProperty('--test', '1px');
        return el.style.getPropertyValue('--test') === '1px';
      } catch (e) {
        return false;
      }
    }
  };

  // Check all critical features
  const results = {};
  let allSupported = true;

  for (const [name, check] of Object.entries(features)) {
    try {
      results[name] = check();
      if (!results[name]) {
        allSupported = false;
      }
    } catch (e) {
      results[name] = false;
      allSupported = false;
    }
  }

  // If all features are supported, exit early
  if (allSupported) {
    window.__featureDetectionPassed = true;
    return;
  }

  // Show fallback message for unsupported browsers
  showUnsupportedBrowserFallback(results);

  function showUnsupportedBrowserFallback(results) {
    // Create fallback UI
    const fallback = document.createElement('div');
    fallback.id = 'unsupported-browser-fallback';
    fallback.style.cssText = `
      position: fixed;
      inset: 0;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #f1f5f9;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      padding: 2rem;
      z-index: 99999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      text-align: center;
      overflow-y: auto;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      max-width: 600px;
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(51, 65, 85, 0.6);
      border-radius: 12px;
      padding: 3rem 2rem;
      backdrop-filter: blur(10px);
    `;

    const heading = document.createElement('h1');
    heading.style.cssText = `
      font-size: 2rem;
      margin-bottom: 1rem;
      font-weight: 700;
      color: #ffa00f;
    `;
    heading.textContent = 'Browser Not Supported';

    const message = document.createElement('p');
    message.style.cssText = `
      font-size: 1.1rem;
      margin-bottom: 1.5rem;
      line-height: 1.6;
      color: #e2e8f0;
    `;
    message.textContent = 'Your browser is missing critical features needed to run the Knowledge Mapper.';

    const details = document.createElement('div');
    details.style.cssText = `
      text-align: left;
      background: rgba(15, 23, 42, 0.5);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      font-size: 0.95rem;
      color: #cbd5e1;
    `;

    const detailsList = document.createElement('ul');
    detailsList.style.cssText = `
      list-style: none;
      padding: 0;
      margin: 0;
    `;

    const featureNames = {
      esModules: 'ES Module Support',
      canvas2d: 'Canvas 2D Graphics',
      localStorage: 'Local Storage',
      cssCustomProperties: 'CSS Custom Properties'
    };

    for (const [feature, supported] of Object.entries(results)) {
      const li = document.createElement('li');
      li.style.cssText = `
        padding: 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
      `;

      const status = document.createElement('span');
      status.style.cssText = `
        display: inline-block;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: ${supported ? '#10b981' : '#ef4444'};
        flex-shrink: 0;
        font-weight: bold;
        color: white;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      status.textContent = supported ? '✓' : '✕';

      const label = document.createElement('span');
      label.textContent = featureNames[feature];
      label.style.color = supported ? '#10b981' : '#ef4444';

      li.appendChild(status);
      li.appendChild(label);
      detailsList.appendChild(li);
    }

    details.appendChild(detailsList);

    const recommendation = document.createElement('p');
    recommendation.style.cssText = `
      font-size: 1rem;
      margin-bottom: 1.5rem;
      line-height: 1.6;
      color: #cbd5e1;
    `;
    recommendation.innerHTML = 'Please upgrade to a modern browser:<br><strong>Chrome 90+</strong>, <strong>Firefox 88+</strong>, <strong>Safari 15+</strong>, or <strong>Edge 90+</strong>';

    const button = document.createElement('button');
    button.style.cssText = `
      background: linear-gradient(135deg, #00693e 0%, #1a8a5a 100%);
      color: white;
      border: none;
      padding: 0.75rem 2rem;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 4px 12px rgba(0, 105, 62, 0.3);
    `;
    button.textContent = 'Try Anyway (May Not Work)';
    button.onmouseover = () => {
      button.style.boxShadow = '0 6px 16px rgba(0, 105, 62, 0.5)';
      button.style.transform = 'translateY(-2px)';
    };
    button.onmouseout = () => {
      button.style.boxShadow = '0 4px 12px rgba(0, 105, 62, 0.3)';
      button.style.transform = 'translateY(0)';
    };
    button.onclick = () => {
      fallback.remove();
      window.__featureDetectionPassed = true;
    };

    content.appendChild(heading);
    content.appendChild(message);
    content.appendChild(details);
    content.appendChild(recommendation);
    content.appendChild(button);

    fallback.appendChild(content);
    document.body.appendChild(fallback);

    // Prevent app from loading
    window.__featureDetectionPassed = false;
  }
})();
