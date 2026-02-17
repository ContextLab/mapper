import { test, expect } from '@playwright/test';

test.describe('Accessibility (FR-023)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });
  });

  test('ARIA attributes present on key elements', async ({ page }) => {
    await expect(page.locator('#map-container')).toHaveAttribute('aria-label');
    await expect(page.locator('#quiz-panel')).toHaveAttribute('aria-label');
    await expect(page.locator('#about-modal')).toHaveAttribute('role', 'dialog');
    await expect(page.locator('#about-modal')).toHaveAttribute('aria-modal', 'true');
    await expect(page.locator('#aria-live')).toHaveAttribute('aria-live');
  });

  test('Escape key closes about modal', async ({ page }) => {
    await page.locator('#about-btn').click();
    await page.waitForSelector('#about-modal:not([hidden])', { timeout: 3000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('#about-modal')).toBeHidden();
  });

  test('skip-to-content link appears on focus', async ({ page }) => {
    await page.keyboard.press('Tab');
    const skipLink = page.locator('.skip-link');
    await expect(skipLink).toBeFocused();
  });

  test('about button is keyboard accessible', async ({ page }) => {
    await page.locator('#about-btn').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#about-modal')).not.toBeHidden();
  });
});
