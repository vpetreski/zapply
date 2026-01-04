// @ts-check
import { test, expect } from '@playwright/test';

// JWT token generated for testing (valid for 24 hours)
// This token is for vanja@petreski.co
const AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2YW5qYUBwZXRyZXNraS5jbyIsImV4cCI6MTc2NzYyNDI4NX0.CKWyf24J9WTGuWtLFRPy44K20sfoGwlkKrx36aTI4A8';

test.describe('Interviews Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Inject auth token directly into localStorage
    await page.goto('http://localhost:3000');
    await page.evaluate((token) => {
      localStorage.setItem('auth_token', token);
    }, AUTH_TOKEN);

    // Navigate to interviews page
    await page.goto('http://localhost:3000/interviews');
    await page.waitForLoadState('networkidle');
  });

  test('should display interviews page', async ({ page }) => {
    // Check page title
    await expect(page.locator('h2')).toContainText('Interviews');

    // Check that New Interview button exists
    await expect(page.locator('button:has-text("New Interview")')).toBeVisible();

    // Check status filter exists
    await expect(page.locator('select#status-filter')).toBeVisible();
  });

  test('should create a new interview', async ({ page }) => {
    // Click New Interview button
    await page.click('button:has-text("New Interview")');

    // Wait for modal to appear
    await expect(page.locator('.interview-modal')).toBeVisible();

    // Fill in title
    const testTitle = `Test Interview ${Date.now()}`;
    await page.fill('#interview-title', testTitle);

    // Fill in description using the rich text editor
    await page.click('.editor-content');
    await page.keyboard.type('This is a test interview description with some details.');

    // Click Create button
    await page.click('button:has-text("Create")');

    // Wait for modal to close
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Verify the new interview appears in the list
    await expect(page.locator(`.interview-card:has-text("${testTitle}")`)).toBeVisible();
  });

  test('should edit an existing interview', async ({ page }) => {
    // First create an interview to edit
    await page.click('button:has-text("New Interview")');
    await expect(page.locator('.interview-modal')).toBeVisible();

    const originalTitle = `Edit Test ${Date.now()}`;
    await page.fill('#interview-title', originalTitle);
    await page.click('.editor-content');
    await page.keyboard.type('Original description');
    await page.click('button:has-text("Create")');
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Now click on the interview card to edit it
    await page.click(`.interview-card:has-text("${originalTitle}")`);
    await expect(page.locator('.interview-modal')).toBeVisible();

    // Verify it's in edit mode
    await expect(page.locator('.modal-header h2')).toHaveText('Edit Interview');

    // Change the title
    const updatedTitle = `Updated ${originalTitle}`;
    await page.fill('#interview-title', updatedTitle);

    // Change status to closed
    await page.selectOption('#interview-status', 'closed');

    // Click Update button
    await page.click('button:has-text("Update")');

    // Wait for modal to close
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Switch filter to show closed interviews
    await page.selectOption('#status-filter', 'closed');

    // Verify the updated interview appears
    await expect(page.locator(`.interview-card:has-text("${updatedTitle}")`)).toBeVisible();
    await expect(page.locator(`.interview-card:has-text("${updatedTitle}") .badge-closed`)).toBeVisible();
  });

  test('should delete an interview', async ({ page }) => {
    // First create an interview to delete
    await page.click('button:has-text("New Interview")');
    await expect(page.locator('.interview-modal')).toBeVisible();

    const deleteTitle = `Delete Test ${Date.now()}`;
    await page.fill('#interview-title', deleteTitle);
    await page.click('.editor-content');
    await page.keyboard.type('This will be deleted');
    await page.click('button:has-text("Create")');
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Click on the interview to open edit modal
    await page.click(`.interview-card:has-text("${deleteTitle}")`);
    await expect(page.locator('.interview-modal')).toBeVisible();

    // Click Delete button
    await page.click('.interview-modal button:has-text("Delete")');

    // Confirm deletion in the dialog
    await expect(page.locator('.dialog-container')).toBeVisible();
    await page.click('.dialog-container button:has-text("Delete")');

    // Wait for dialogs to close
    await expect(page.locator('.dialog-container')).not.toBeVisible({ timeout: 5000 });
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Verify the interview is no longer in the list
    await expect(page.locator(`.interview-card:has-text("${deleteTitle}")`)).not.toBeVisible();
  });

  test('should filter interviews by status', async ({ page }) => {
    // Create an active interview
    await page.click('button:has-text("New Interview")');
    const activeTitle = `Active Filter Test ${Date.now()}`;
    await page.fill('#interview-title', activeTitle);
    await page.click('.editor-content');
    await page.keyboard.type('Active interview');
    await page.click('button:has-text("Create")');
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Verify it shows in Active filter (default)
    await expect(page.locator(`.interview-card:has-text("${activeTitle}")`)).toBeVisible();

    // Switch to Closed filter
    await page.selectOption('#status-filter', 'closed');
    await page.waitForTimeout(500); // Wait for filter to apply

    // The active interview should not be visible
    await expect(page.locator(`.interview-card:has-text("${activeTitle}")`)).not.toBeVisible();

    // Switch to All filter
    await page.selectOption('#status-filter', '');
    await page.waitForTimeout(500);

    // The active interview should be visible again
    await expect(page.locator(`.interview-card:has-text("${activeTitle}")`)).toBeVisible();
  });

  test('should display rich text content correctly', async ({ page }) => {
    // Create an interview with rich text
    await page.click('button:has-text("New Interview")');
    await expect(page.locator('.interview-modal')).toBeVisible();

    const richTextTitle = `Rich Text Test ${Date.now()}`;
    await page.fill('#interview-title', richTextTitle);

    // Use rich text editor features
    await page.click('.editor-content');
    await page.keyboard.type('Normal text. ');

    // Bold text
    await page.click('.editor-toolbar button:has-text("B")');
    await page.keyboard.type('Bold text. ');
    await page.click('.editor-toolbar button:has-text("B")');

    // Create bullet list
    await page.click('.editor-toolbar button:has-text("List")');
    await page.keyboard.type('First item');
    await page.keyboard.press('Enter');
    await page.keyboard.type('Second item');

    await page.click('button:has-text("Create")');
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Verify the interview was created
    await expect(page.locator(`.interview-card:has-text("${richTextTitle}")`)).toBeVisible();
  });

  test('should upload CV when creating interview', async ({ page }) => {
    // Click New Interview button
    await page.click('button:has-text("New Interview")');
    await expect(page.locator('.interview-modal')).toBeVisible();

    // Fill in title
    const cvTestTitle = `CV Test ${Date.now()}`;
    await page.fill('#interview-title', cvTestTitle);

    // Fill in description
    await page.click('.editor-content');
    await page.keyboard.type('Interview with custom CV attached.');

    // Upload CV
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/test.pdf');

    // Verify file is selected (button text or indicator changes)
    await expect(page.locator('.cv-upload')).toContainText('test.pdf');

    // Click Create button
    await page.click('button:has-text("Create")');

    // Wait for modal to close
    await expect(page.locator('.interview-modal')).not.toBeVisible({ timeout: 5000 });

    // Verify the interview appears in the list with CV indicator (Download CV link)
    await expect(page.locator(`.interview-card:has-text("${cvTestTitle}")`)).toBeVisible();
    await expect(page.locator(`.interview-card:has-text("${cvTestTitle}") .cv-link`)).toBeVisible();
  });
});
