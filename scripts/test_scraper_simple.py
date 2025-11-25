"""Simplified test to identify correct selectors."""

import asyncio
import os
import re

from dotenv import load_dotenv
from playwright.async_api import async_playwright


async def main():
    load_dotenv()
    email = os.getenv("WORKING_NOMADS_USERNAME")
    password = os.getenv("WORKING_NOMADS_PASSWORD")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()

        # Login
        await page.goto("https://www.workingnomads.com/users/sign_in")
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('input[type="submit"]')
        await page.wait_for_load_state("networkidle")

        # Go to filtered jobs
        await page.goto("https://www.workingnomads.com/jobs?category=development&location=anywhere,colombia")
        await page.wait_for_load_state("networkidle")

        print("\n🔍 Analyzing page structure...\n")

        # Get page HTML and inspect
        # Find all clickable job titles - they should navigate to job detail
        all_links = await page.query_selector_all('a')

        job_links = []
        for link in all_links[:50]:  # Check first 50 links
            href = await link.get_attribute('href')
            text = await link.inner_text()

            # Skip empty, very short, or navigation links
            if not text or len(text.strip()) < 5:
                continue
            if not href or href in ['/', '/jobs', '/companies']:
                continue

            # Check if this looks like a job title
            if len(text) > 10 and len(text) < 100:
                print(f"Link text: {text[:60]}")
                print(f"Href: {href}")

                # Check if this is a job detail link
                # Format: /jobs/middle-java-developer-gr8-tech
                if href.startswith('/jobs/') and href != '/jobs':
                    # Extract slug from URL
                    slug = href.replace('/jobs/', '')
                    if slug and '/' not in slug:  # Make sure it's a slug, not a path
                        job_links.append({
                            'text': text.strip(),
                            'href': href,
                            'slug': slug,
                            'element': link
                        })
                        print(f"  ✅ JOB FOUND! Slug: {slug}\n")

        print(f"\n📊 Found {len(job_links)} job links total")

        if len(job_links) > 0:
            # Click on first job
            first_job = job_links[0]
            print(f"\n🖱️  Clicking on: {first_job['text']}")
            print(f"Slug: {first_job['slug']}")

            await first_job['element'].click()
            await page.wait_for_load_state("networkidle")

            print(f"URL after click: {page.url}")
            await page.screenshot(path="job_detail_page.png")
            print("📸 Screenshot: job_detail_page.png")

            # Now extract details from job detail page
            print("\n📝 Extracting job details...")

            title = await page.query_selector('h1, h2')
            if title:
                title_text = await title.inner_text()
                print(f"Title: {title_text}")

            # Find company name
            # Try common selectors
            company_selectors = ['[class*="company"]', '.text-gray-600', 'h3', 'h4']
            for sel in company_selectors:
                elem = await page.query_selector(sel)
                if elem:
                    text = await elem.inner_text()
                    if text and 5 < len(text) < 50:
                        print(f"Company (via {sel}): {text}")
                        break

            # Find apply button
            apply = await page.query_selector('a:has-text("Apply"), button:has-text("Apply")')
            if apply:
                apply_href = await apply.get_attribute('href')
                apply_text = await apply.inner_text()
                print(f"Apply button: {apply_text}")
                print(f"Apply URL: {apply_href}")

        print("\nWaiting 15 seconds...")
        await asyncio.sleep(15)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
