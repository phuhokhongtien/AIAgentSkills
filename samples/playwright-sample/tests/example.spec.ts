import { test, expect } from '@playwright/test';

const PAGE = `
  <!DOCTYPE html>
  <html>
    <body>
      <h1 id="title">Testing Explorer Demo</h1>
      <button id="go" onclick="document.getElementById('out').textContent='clicked'">Go</button>
      <div id="out">idle</div>
    </body>
  </html>`;

test.describe('demo page', () => {
  test('shows the title', async ({ page }) => {
    await page.setContent(PAGE);
    await expect(page.locator('#title')).toHaveText('Testing Explorer Demo');
  });

  test('button updates output', async ({ page }) => {
    await page.setContent(PAGE);
    await page.locator('#go').click();
    await expect(page.locator('#out')).toHaveText('clicked');
  });

  // Demo FAILURE: asserts the wrong text → exercises failure root-cause + re-run.
  test('output starts as ready (intentionally failing)', async ({ page }) => {
    await page.setContent(PAGE);
    await expect(page.locator('#out')).toHaveText('ready');
  });
});
