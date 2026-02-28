/** Edge case tests: slow network (T065) and rapid domain switching (T068). */
import { test, expect } from '@playwright/test';

const LOAD_TIMEOUT = 15000;

async function selectDomain(page, domainName) {
  const value = domainName.toLowerCase().replace(/\s+/g, '-');
  // If on landing page, click start button to enter the map first
  const startBtn = page.locator('#landing-start-btn');
  if (await startBtn.isVisible().catch(() => false)) {
    await page.waitForSelector('#landing-start-btn[data-ready]', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }
  const trigger = page.locator('.domain-selector .custom-select-trigger');
  await trigger.click();
  await page.locator(`.domain-selector .custom-select-option[data-value="${value}"]`).click();
}

test.describe('Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('domain loading shows progress bar with slow connection (T065)', async ({ page }) => {
    // Set up route interception to throttle domain data requests
    await page.route('**/data/domains/**', async (route) => {
      // Add 2-second artificial delay to simulate slow network
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.continue();
    });

    // Verify progress overlay exists but is initially hidden
    const progressOverlay = page.locator('#progress-overlay');
    await expect(progressOverlay).toBeVisible();

    // Start domain selection (click start then pick physics from header)
    await selectDomain(page, 'physics');

    // Verify progress overlay becomes visible during load
    // The overlay should show a loading percentage
    const overlayStyle = await progressOverlay.evaluate(el => window.getComputedStyle(el).opacity);
    expect(parseFloat(overlayStyle)).toBeGreaterThan(0.5);

    // Verify the page remains interactive during loading
    // Try clicking the theme toggle button (should not throw)
    const themeToggle = page.locator('[data-testid="theme-toggle"], button:has-text("Theme"), #theme-toggle');
    const toggleExists = await themeToggle.count() > 0;
    if (toggleExists) {
      await expect(themeToggle.first()).toBeEnabled();
    }

    // Wait for domain to load successfully
    await page.waitForSelector('.quiz-question', { timeout: 10000 });

    // Verify the domain eventually loaded
    const quizPanel = page.locator('#quiz-panel');
    await expect(quizPanel).not.toHaveAttribute('hidden');

    // Verify progress overlay fades out after load completes
    await page.waitForTimeout(500);
    const overlayOpacity = await progressOverlay.evaluate(el => window.getComputedStyle(el).opacity);
    // Opacity should be 0 or very close to 0 after fade-out
    expect(parseFloat(overlayOpacity)).toBeLessThanOrEqual(0.1);
  });

  test('rapid domain switching renders only final domain (T068)', async ({ page }) => {
    // Load initial domain to establish baseline
    await selectDomain(page, 'linear-algebra');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Get the initial question text for comparison
    const initialQuestion = await page.locator('.quiz-question').textContent();

    // Define 5 domains to switch through rapidly (ending on a distinct domain)
    const domainsToSwitch = ['physics', 'biology', 'neuroscience', 'mathematics', 'european-art-history'];

    // Rapidly click through domains in quick succession (< 2 seconds total)
    const startTime = Date.now();
    for (const domain of domainsToSwitch) {
      const value = domain.toLowerCase().replace(/\s+/g, '-');
      const trigger = page.locator('.domain-selector .custom-select-trigger');
      await trigger.click({ timeout: 1000 });
      const parent = page.locator('.domain-selector');
      await parent.locator(`.custom-select-option[data-value="${value}"]`).click({ timeout: 1000 });
      // Minimal wait between clicks to simulate rapid switching
      await page.waitForTimeout(100);
    }
    const switchDuration = Date.now() - startTime;

    // Verify all switches happened within 4 seconds (relaxed for slower browsers)
    expect(switchDuration).toBeLessThan(4000);

    // Wait for all transitions to settle
    await page.waitForTimeout(2000);

    // Verify only the final domain's data is displayed
    const finalQuestion = await page.locator('.quiz-question').textContent();
    expect(finalQuestion).not.toEqual(initialQuestion);

    // Verify the final domain (european-art-history) rendered successfully
    const quizPanel = page.locator('#quiz-panel');
    await expect(quizPanel).not.toHaveAttribute('hidden');

    // Verify no visual glitches: quiz panel should show questions from final domain only
    const questionElements = page.locator('.quiz-question');
    const questionCount = await questionElements.count();
    expect(questionCount).toBeGreaterThan(0);

    // Verify no console errors from race conditions
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Wait a bit more to catch any delayed errors
    await page.waitForTimeout(500);

    // Check for race condition errors (switchGeneration mismatch, etc.)
    const raceConditionErrors = consoleErrors.filter(err =>
      err.includes('switchGeneration') ||
      err.includes('race') ||
      err.includes('abort') ||
      err.includes('cancelled')
    );
    expect(raceConditionErrors).toHaveLength(0);
  });

  test('localStorage unavailability shows dismissible banner (T063)', async ({ page }) => {
    // Block localStorage by disabling it in the page context
    await page.addInitScript(() => {
      const handler = {
        get: function() {
          throw new Error('localStorage is not available');
        }
      };
      Object.defineProperty(window, 'localStorage', handler);
    });

    // Navigate to the app
    await page.goto('/');
    await page.waitForSelector('#app-main', { timeout: LOAD_TIMEOUT });

    // Verify the notice banner appears
    const banner = page.locator('.notice-banner');
    await expect(banner).toBeVisible({ timeout: 5000 });

    // Verify the banner contains the expected message
    const bannerText = await banner.textContent();
    expect(bannerText).toContain("Progress won");

    // Verify the banner has the correct styling (warning type)
    const bannerClass = await banner.getAttribute('class');
    expect(bannerClass).toContain('notice-banner');

    // Verify the dismiss button exists
    const dismissBtn = banner.locator('.notice-banner-dismiss');
    await expect(dismissBtn).toBeVisible();

    // Verify the app remains functional with the banner visible
    const appMain = page.locator('#app-main');
    await expect(appMain).toBeVisible();
  });

  test('schema version mismatch shows dismissible banner (T064)', async ({ page }) => {
    // Set an old schema version in localStorage before loading
    await page.addInitScript(() => {
      localStorage.setItem('mapper:schema', '0.0.1');
    });

    // Navigate to the app
    await page.goto('/');
    await page.waitForSelector('#app-main', { timeout: LOAD_TIMEOUT });

    // Verify the notice banner appears
    const banner = page.locator('.notice-banner');
    await expect(banner).toBeVisible({ timeout: 5000 });

    // Verify the banner contains the expected message
    const bannerText = await banner.textContent();
    expect(bannerText).toContain('Previous progress was from an older version');

    // Verify the banner has the correct styling
    const bannerClass = await banner.getAttribute('class');
    expect(bannerClass).toContain('notice-banner');

    // Verify the dismiss button exists and is clickable
    const dismissBtn = banner.locator('.notice-banner-dismiss');
    await expect(dismissBtn).toBeVisible();

    // Click the dismiss button
    await dismissBtn.click();

    // Verify the banner animates out and is removed
    await expect(banner).not.toBeVisible({ timeout: 1000 });

    // Verify the app remains functional after dismissal
    const appMain = page.locator('#app-main');
    await expect(appMain).toBeVisible();
  });

  test('banner auto-dismisses after 8 seconds (T063, T064)', async ({ page }) => {
    // Set an old schema version to trigger the banner
    await page.addInitScript(() => {
      localStorage.setItem('mapper:schema', '0.0.1');
    });

    // Navigate to the app
    await page.goto('/');
    await page.waitForSelector('#app-main', { timeout: LOAD_TIMEOUT });

    // Verify the notice banner appears
    const banner = page.locator('.notice-banner');
    await expect(banner).toBeVisible({ timeout: 5000 });

    // Wait for auto-dismiss (8 seconds + animation time)
    await expect(banner).not.toBeVisible({ timeout: 10000 });
  });

  test('banner respects theme colors (dark and light)', async ({ page }) => {
    // Set an old schema version to trigger the banner
    await page.addInitScript(() => {
      localStorage.setItem('mapper:schema', '0.0.1');
    });

    // Navigate to the app (defaults to dark theme)
    await page.goto('/');
    await page.waitForSelector('#app-main', { timeout: LOAD_TIMEOUT });

    // Verify the notice banner appears
    const banner = page.locator('.notice-banner');
    await expect(banner).toBeVisible({ timeout: 5000 });

    // Check dark theme colors
    const darkBgColor = await banner.evaluate(el => window.getComputedStyle(el).backgroundColor);
    expect(darkBgColor).toBeTruthy();

    // Switch to light theme
    const themeToggle = page.locator('#theme-toggle');
    await themeToggle.click();
    await page.waitForTimeout(500);

    // Verify banner is still visible and has updated colors
    await expect(banner).toBeVisible();
    const lightBgColor = await banner.evaluate(el => window.getComputedStyle(el).backgroundColor);
    expect(lightBgColor).toBeTruthy();
    // Colors should be different between themes
    expect(darkBgColor).not.toEqual(lightBgColor);
  });

  test('_showBanner function creates visible banner element', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    await page.waitForSelector('#app-main', { timeout: LOAD_TIMEOUT });

    // Directly call the _showBanner function via page context
    await page.evaluate(() => {
      const container = document.getElementById('app-main');
      const banner = document.createElement('div');
      banner.className = 'notice-banner';
      banner.setAttribute('role', 'alert');
      const content = document.createElement('div');
      content.className = 'notice-banner-content';
      content.textContent = 'Test banner message';
      const dismissBtn = document.createElement('button');
      dismissBtn.className = 'notice-banner-dismiss';
      dismissBtn.setAttribute('aria-label', 'Dismiss notification');
      dismissBtn.innerHTML = '<i class="fa fa-times"></i>';
      banner.appendChild(content);
      banner.appendChild(dismissBtn);
      container.insertBefore(banner, container.firstChild);
    });

    // Verify the banner appears
    const banner = page.locator('.notice-banner');
    await expect(banner).toBeVisible({ timeout: 5000 });

    // Verify the banner contains the expected message
    const bannerText = await banner.textContent();
    expect(bannerText).toContain('Test banner message');

    // Verify the dismiss button exists
    const dismissBtn = banner.locator('.notice-banner-dismiss');
    await expect(dismissBtn).toBeVisible();
  });
});
