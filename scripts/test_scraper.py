"""Test script to debug and fix the Working Nomads scraper."""

import asyncio
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright


async def test_working_nomads():
    """Test Working Nomads scraping interactively."""

    # Load credentials from .env
    load_dotenv()
    email = os.getenv("WORKING_NOMADS_USERNAME")
    password = os.getenv("WORKING_NOMADS_PASSWORD")

    if not email or not password:
        print("❌ Missing WORKING_NOMADS_USERNAME or WORKING_NOMADS_PASSWORD in .env")
        return

    print(f"🔑 Using credentials: {email}")

    async with async_playwright() as p:
        # Launch browser in headful mode to see what's happening
        print("🚀 Launching browser (visible mode)...")
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()

        print("🚀 Testing Working Nomads scraper...")

        try:
            # Step 1: Navigate to login page
            print("\n1. Navigating to login page...")
            await page.goto("https://www.workingnomads.com/users/sign_in")
            await page.wait_for_load_state("networkidle")

            # Take screenshot
            await page.screenshot(path="step1_login_page.png")
            print("   📸 Screenshot saved: step1_login_page.png")

            # Look for email input
            print("\n2. Looking for email input field...")
            email_input = await page.query_selector('input[type="email"]')
            if email_input:
                print("   ✅ Found input[type='email']")
                await email_input.fill(email)
            else:
                print("   ❌ input[type='email'] not found")
                # Try alternative
                email_input = await page.query_selector('input#user_email')
                if email_input:
                    print("   ✅ Found input#user_email")
                    await email_input.fill(email)
                else:
                    print("   ❌ Could not find email field at all!")
                    await page.screenshot(path="error_no_email_field.png")
                    return

            # Look for password input
            print("\n3. Looking for password input field...")
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                print("   ✅ Found input[type='password']")
                await password_input.fill(password)
            else:
                print("   ❌ input[type='password'] not found")
                await page.screenshot(path="error_no_password_field.png")
                return

            await page.screenshot(path="step2_filled_form.png")
            print("   📸 Screenshot saved: step2_filled_form.png")

            # Look for submit button
            print("\n4. Looking for submit button...")
            submit_selectors = [
                'button:has-text("Sign in")',
                'button[type="submit"]',
                'input[type="submit"]',
            ]

            submit_button = None
            for selector in submit_selectors:
                submit_button = await page.query_selector(selector)
                if submit_button:
                    button_text = await submit_button.inner_text()
                    print(f"   ✅ Found submit button with {selector}: '{button_text}'")
                    break

            if submit_button:
                # Click and wait for navigation
                print("   🖱️  Clicking submit button...")
                await submit_button.click()
                await page.wait_for_load_state("networkidle")

                current_url = page.url
                print(f"   📍 After login, URL: {current_url}")

                await page.screenshot(path="step3_after_login.png")
                print("   📸 Screenshot saved: step3_after_login.png")
            else:
                print("   ❌ Submit button not found")
                await page.screenshot(path="error_no_submit_button.png")
                return

            # Step 5: Navigate to jobs with filters
            print("\n5. Navigating to jobs with filters...")
            filter_url = "https://www.workingnomads.com/jobs?category=development&location=anywhere,colombia"
            await page.goto(filter_url)
            await page.wait_for_load_state("networkidle")

            await page.screenshot(path="step4_jobs_filtered.png")
            print("   📸 Screenshot saved: step4_jobs_filtered.png")

            # Count visible jobs
            job_cards = await page.query_selector_all('.job, [class*="job-card"], article')
            print(f"   📊 Visible job cards: {len(job_cards)}")

            # Step 6: Find "Show more" button
            print("\n6. Looking for 'Show more jobs' button...")
            show_more_selectors = [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'a:has-text("Show more")',
                'button.load-more',
                '[class*="load-more"]',
            ]

            show_more = None
            for selector in show_more_selectors:
                show_more = await page.query_selector(selector)
                if show_more:
                    print(f"   ✅ Found show more button with: {selector}")
                    is_visible = await show_more.is_visible()
                    print(f"   Visible: {is_visible}")
                    break

            if not show_more:
                print("   ❌ 'Show more jobs' button not found")

            # Step 7: Find job clickable elements
            print("\n7. Looking for job clickable elements...")

            # Let's try clicking on the first job container
            job_containers = await page.query_selector_all('[class*="job"]')
            print(f"   Found {len(job_containers)} elements with 'job' in class")

            if len(job_containers) > 0:
                first_job = job_containers[0]

                # Get all text from first job to see what it contains
                job_text = await first_job.inner_text()
                print(f"   First job text preview: {job_text[:100]}...")

                # Try to click on it
                print("\n8. Clicking on first job...")
                try:
                    await first_job.click()
                    await page.wait_for_timeout(2000)  # Wait a bit

                    current_url = page.url
                    print(f"   URL after click: {current_url}")

                    # Check if URL contains job parameter
                    if 'job=' in current_url:
                        match = re.search(r'job=([^&]+)', current_url)
                        if match:
                            slug = match.group(1)
                            print(f"   ✅ Job slug from URL: {slug}")

                    await page.screenshot(path="step5_job_detail.png")
                    print("   📸 Screenshot saved: step5_job_detail.png")

                    # Extract job details
                    print("\n9. Extracting job details...")

                    # Title
                    title_elem = await page.query_selector('h1, h2, h3')
                    if title_elem:
                        title = await title_elem.inner_text()
                        print(f"   Title: {title[:80]}...")

                    # Company - try multiple selectors
                    company_text = None
                    company_selectors = [
                        '.company-name',
                        '[class*="company"]',
                        'h2',
                        'h3',
                    ]
                    for selector in company_selectors:
                        company_elem = await page.query_selector(selector)
                        if company_elem:
                            company_text = await company_elem.inner_text()
                            if company_text and len(company_text) < 100:  # Reasonable company name length
                                print(f"   Company (via {selector}): {company_text[:50]}")
                                break

                    # Description
                    desc_elems = await page.query_selector_all('p')
                    print(f"   Found {len(desc_elems)} paragraph elements")

                    # Look for apply button
                    apply_selectors = [
                        'a:has-text("Apply")',
                        'button:has-text("Apply")',
                        'a[href*="apply"]',
                        '[class*="apply"]',
                    ]

                    for selector in apply_selectors:
                        apply_button = await page.query_selector(selector)
                        if apply_button:
                            apply_url = await apply_button.get_attribute('href')
                            apply_text = await apply_button.inner_text()
                            print(f"   Apply button (via {selector}): '{apply_text}'")
                            print(f"   Apply URL: {apply_url}")
                            break

                except Exception as e:
                    print(f"   ❌ Failed to click job: {str(e)}")

            print("\n✅ Test complete! Check screenshots for details.")
            print("\nWaiting 10 seconds before closing browser...")
            await asyncio.sleep(10)

        except Exception as e:
            print(f"\n❌ Error during test: {str(e)}")
            await page.screenshot(path="error_exception.png")
            print("   📸 Screenshot saved: error_exception.png")

        finally:
            await browser.close()
            print("🔒 Browser closed")


if __name__ == "__main__":
    asyncio.run(test_working_nomads())
