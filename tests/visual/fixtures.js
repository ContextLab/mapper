/**
 * Shared Playwright fixtures for all visual tests.
 * Auto-dismisses the tutorial overlay so it doesn't block test interactions.
 */
import { test as base } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    // Pre-dismiss tutorial before every test navigation
    await page.addInitScript(() => {
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: false, dismissed: true, step: 1, subStep: 1,
        hasSkippedQuestion: false, skipToastShown: false, returningUser: false,
      }));
    });
    await use(page);
  },
});

export { expect } from '@playwright/test';
