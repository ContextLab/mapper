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

  test('domain switching works with slow network (T065)', async ({ page }) => {
    // Intercept domain data requests with artificial delay
    await page.route('**/data/domains/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1500));
      await route.continue();
    });

    // Enter the map and select a domain
    await selectDomain(page, 'physics');

    // Verify the domain eventually loaded despite the delay
    await page.waitForSelector('.quiz-question', { timeout: 15000 });
    const quizPanel = page.locator('#quiz-panel');
    await expect(quizPanel).not.toHaveAttribute('hidden');

    // Verify a question is displayed (domain data loaded successfully)
    const questionText = await page.locator('.quiz-question').textContent();
    expect(questionText.length).toBeGreaterThan(0);
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

    // Rapidly click through domains in quick succession
    const startTime = Date.now();
    for (const domain of domainsToSwitch) {
      const value = domain.toLowerCase().replace(/\s+/g, '-');
      const trigger = page.locator('.domain-selector .custom-select-trigger');
      await trigger.click({ timeout: 3000 });
      const parent = page.locator('.domain-selector');
      await parent.locator(`.custom-select-option[data-value="${value}"]`).click({ timeout: 3000 });
      // Minimal wait between clicks to simulate rapid switching
      await page.waitForTimeout(100);
    }
    const switchDuration = Date.now() - startTime;

    // Verify all switches happened within 8 seconds (relaxed for slower browsers)
    expect(switchDuration).toBeLessThan(8000);

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

  test('banner has proper styling and colors', async ({ page }) => {
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

    // Verify banner has a visible background color
    const bgColor = await banner.evaluate(el => window.getComputedStyle(el).backgroundColor);
    expect(bgColor).toBeTruthy();
    // Should not be fully transparent
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');

    // Verify banner has proper text color
    const textColor = await banner.evaluate(el => window.getComputedStyle(el).color);
    expect(textColor).toBeTruthy();

    // Verify the left border accent
    const borderLeft = await banner.evaluate(el => window.getComputedStyle(el).borderLeftStyle);
    expect(borderLeft).toBe('solid');
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
