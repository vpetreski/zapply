"""Automated job application using Playwright and Claude AI."""

import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import anthropic
from playwright.async_api import Page, async_playwright, Browser

from app.ai_models import APPLIER_MODEL
from app.config import settings
from app.models import Job, UserProfile
from app.utils import log_to_console


class JobApplier:
    """Apply to jobs automatically using Playwright + Claude AI."""

    @staticmethod
    def _fix_css_selector(selector: str) -> str:
        """
        Fix CSS selectors that have IDs starting with digits.

        CSS IDs starting with digits are technically invalid and need special handling.
        Converts #0abc123 to [id="0abc123"] which works for any ID value.
        """
        if not selector:
            return selector

        # Check if selector starts with # followed by a digit
        if selector.startswith('#') and len(selector) > 1 and selector[1].isdigit():
            # Convert #0abc123 to [id="0abc123"]
            id_value = selector[1:]
            return f'[id="{id_value}"]'

        return selector

    def __init__(
        self,
        profile: UserProfile,
        cv_path: Optional[Path] = None,
        dry_run: bool = False,
        screenshot_dir: Optional[Path] = None,
        headless: bool = True,
        interactive: bool = False
    ) -> None:
        """
        Initialize job applier.

        Args:
            profile: User profile with application data
            cv_path: Path to CV PDF file
            dry_run: If True, don't actually submit
            screenshot_dir: Directory to save screenshots
            headless: If False, show browser window (for debugging)
            interactive: If True, pause before submit for user feedback
        """
        self.profile = profile
        self.cv_path = cv_path
        self.dry_run = dry_run
        self.screenshot_dir = screenshot_dir or Path("/tmp/zapply_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.interactive = interactive

        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Track data for logging
        self.screenshots: list[str] = []
        self.ai_prompts: list[str] = []
        self.ai_responses: list[str] = []
        self.steps: list[dict[str, Any]] = []
        self.fields_filled: list[dict[str, str]] = []  # Human-readable field/value pairs

    async def apply_to_job(
        self, job: Job
    ) -> tuple[bool, Optional[str], Optional[dict[str, Any]]]:
        """
        Apply to a job automatically.

        Args:
            job: Job object to apply to

        Returns:
            Tuple of (success, error_message, application_data)
        """
        playwright = None
        try:
            # Launch browser
            log_to_console("🚀 Launching browser...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
            )
            self.page = await self.browser.new_page()

            # Set a realistic viewport
            await self.page.set_viewport_size({"width": 1280, "height": 800})

            # Step 1: Navigate to job URL
            log_to_console(f"📍 Navigating to job page...")
            success = await self._navigate_to_job(job.url)
            if not success:
                # Extract specific error from steps
                nav_error = "Failed to navigate to job page"
                for step in self.steps:
                    if step.get("action") == "navigate" and step.get("error"):
                        nav_error = step["error"]
                        break
                return False, nav_error, self._get_result_data()

            # Take initial screenshot
            await self._take_screenshot("01_job_page")

            # Check if we're already on an application page (Greenhouse, Lever, etc.)
            current_url = self.page.url.lower()
            # Note: Jobvite /job/ID pages are job details, not application pages
            # Jobvite application pages have /apply in the URL
            is_direct_application = any(ats in current_url for ats in [
                'greenhouse.io', 'lever.co', 'workable.com', 'ashbyhq.com',
                '/apply', '/application'
            ])

            if is_direct_application:
                log_to_console("   📋 Already on application page, skipping Apply button search")
                self.steps.append({"action": "skip_apply_button", "reason": "Direct application page detected", "url": current_url})

                # Special handling for Ashby: Navigate to Application tab if we're on Overview
                if 'ashbyhq.com' in current_url and '/application' not in current_url:
                    log_to_console("   📋 Ashby detected - navigating to Application tab...")
                    # Try to find and click Application tab link
                    app_tab_found = False
                    try:
                        # Look for Application tab link
                        app_tab_selectors = [
                            'a[href*="/application"]',
                            'a:has-text("Application")',
                            '[role="tab"]:has-text("Application")',
                            'button:has-text("Apply for this job")',
                        ]
                        for selector in app_tab_selectors:
                            tab = await self.page.query_selector(selector)
                            if tab:
                                await tab.click()
                                await self.page.wait_for_timeout(2000)
                                log_to_console(f"   ✅ Clicked Application tab: {selector}")
                                self.steps.append({"action": "navigate_ashby_tab", "selector": selector, "success": True})
                                app_tab_found = True
                                break

                        if not app_tab_found:
                            # Try direct URL navigation
                            application_url = current_url.rstrip('/') + '/application'
                            log_to_console(f"   📍 Trying direct URL: {application_url}")
                            await self.page.goto(application_url, wait_until="networkidle", timeout=30000)
                            await self.page.wait_for_timeout(2000)
                            self.steps.append({"action": "navigate_ashby_tab", "url": application_url, "success": True})
                            app_tab_found = True
                    except Exception as e:
                        log_to_console(f"   ⚠️  Could not navigate to Ashby application tab: {e}")
                        self.steps.append({"action": "navigate_ashby_tab", "success": False, "error": str(e)})
            else:
                # Step 2: Find and click Apply button
                log_to_console("🔍 Looking for Apply button...")
                apply_clicked = await self._find_and_click_apply()
                if not apply_clicked:
                    return False, "Could not find Apply button", self._get_result_data()

                # Wait for page to fully load after clicking apply
                await self.page.wait_for_timeout(3000)  # Initial wait

            # Wait for common form elements to appear
            try:
                await self.page.wait_for_selector('form, input[type="text"], input[type="email"], textarea', timeout=15000)
                log_to_console("   ✅ Form elements detected")
            except Exception:
                log_to_console("   ⚠️  No form elements found after waiting, continuing anyway...")

            await self.page.wait_for_timeout(2000)  # Extra time for JS to fully render
            await self._take_screenshot("02_after_apply_click")

            # Step 3: Analyze the application form
            log_to_console("🤖 Analyzing application form with Claude...")
            form_analysis = await self._analyze_form()
            if not form_analysis:
                return False, "Could not analyze application form", self._get_result_data()

            # Track form analysis in steps
            self.steps.append({
                "action": "analyze_form",
                "form_found": form_analysis.get("form_found", False),
                "fields_count": len(form_analysis.get("fields", [])),
                "fields": [{"label": f.get("label"), "type": f.get("type")} for f in form_analysis.get("fields", [])[:10]],
                "submit_selector": form_analysis.get("submit_selector"),
                "notes": form_analysis.get("notes"),
                "success": form_analysis.get("form_found", False)
            })

            # Step 4: Fill the form (initial pass)
            log_to_console("📝 Filling application form...")
            fill_success = await self._fill_form(form_analysis, job)
            if not fill_success:
                return False, "Failed to fill application form", self._get_result_data()

            # Track fields we've already filled for vision analysis
            filled_labels = [f.get("field", "") for f in self.fields_filled]

            # Step 4b: Scroll down and do vision-based analysis for additional fields
            log_to_console("👁️  Checking for additional fields with vision...")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await self.page.wait_for_timeout(1000)
            vision_analysis = await self._analyze_form_with_vision(filled_labels)
            if vision_analysis and vision_analysis.get('additional_fields'):
                additional_filled = await self._fill_additional_fields(vision_analysis, job)
                log_to_console(f"   📝 Filled {additional_filled} additional fields from vision analysis")

            await self._take_screenshot("03_form_filled")

            # Step 5: Upload CV if needed
            if self.cv_path and self.cv_path.exists():
                log_to_console("📎 Uploading CV...")
                await self._upload_cv()
                await self._take_screenshot("04_cv_uploaded")

            # Step 5b: Global validation pass - Tab through all fields to trigger blur validation
            log_to_console("🔄 Running global validation pass...")
            await self._trigger_global_validation()
            await self._take_screenshot("05_after_validation")

            # Step 6: Submit application (with retry on "required field" errors)
            if self.dry_run:
                log_to_console("🔒 DRY RUN - Not submitting application")
                await self._take_screenshot("05_ready_to_submit_dry_run")
                return True, "Dry run completed - form filled but not submitted", self._get_result_data()

            # Interactive mode: pause for user feedback before submit
            if self.interactive:
                await self._take_screenshot("05_ready_to_submit_interactive")
                await self._wait_for_user_feedback()

            max_retries = 2
            for attempt in range(max_retries):
                log_to_console(f"🚀 Submitting application (attempt {attempt + 1}/{max_retries})...")
                submit_success = await self._submit_application(form_analysis)
                if not submit_success:
                    return False, "Failed to submit application", self._get_result_data()

                await self.page.wait_for_timeout(3000)  # Wait for confirmation
                await self._take_screenshot(f"06_after_submit_attempt{attempt + 1}")

                # Step 7: Verify submission
                log_to_console("✔️  Verifying submission...")
                verified, evidence = await self._verify_submission()

                if verified:
                    return True, f"Application submitted successfully ({evidence})", self._get_result_data()

                # Check if it's a "required field" error - if so, try to fill missing fields
                if 'required' in evidence.lower() and attempt < max_retries - 1:
                    log_to_console("🔄 Required field error detected, re-analyzing form...")
                    await self._take_screenshot(f"07_error_state_attempt{attempt + 1}")

                    # Re-analyze with vision to find the missing required fields
                    error_vision = await self._analyze_form_with_vision(filled_labels)
                    if error_vision:
                        error_fields = error_vision.get('error_fields', [])
                        additional = error_vision.get('additional_fields', [])
                        if error_fields:
                            log_to_console(f"   ⚠️  Error fields detected: {error_fields[:3]}")
                        if additional:
                            extra_filled = await self._fill_additional_fields(error_vision, job)
                            log_to_console(f"   📝 Filled {extra_filled} more fields after error")
                            filled_labels.extend([f.get("field", "") for f in self.fields_filled[-extra_filled:]])
                        await self.page.wait_for_timeout(1000)
                        continue  # Retry submit

                # Not a recoverable error, or out of retries
                return False, f"Application failed: {evidence}", self._get_result_data()

        except Exception as e:
            error_msg = f"Application failed: {str(e)}"
            log_to_console(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            await self._take_screenshot("error_state")
            return False, error_msg, self._get_result_data()

        finally:
            if self.browser:
                await self.browser.close()
            if playwright:
                await playwright.stop()

    def _get_result_data(self) -> dict[str, Any]:
        """Get accumulated result data."""
        return {
            "screenshots": self.screenshots,
            "ai_prompts": self.ai_prompts,
            "ai_responses": self.ai_responses,
            "steps": self.steps,
            "fields_filled": self.fields_filled  # Human-readable field/value pairs
        }

    async def _take_screenshot(self, name: str) -> Optional[str]:
        """Take a screenshot and save it."""
        if not self.page:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.png"
            filepath = self.screenshot_dir / filename

            await self.page.screenshot(path=str(filepath), full_page=True)
            self.screenshots.append(str(filepath))
            log_to_console(f"   📸 Screenshot: {filename}")
            return str(filepath)
        except Exception as e:
            log_to_console(f"   ⚠️  Screenshot failed: {e}")
            return None

    async def _navigate_to_job(self, url: str) -> bool:
        """Navigate to job URL, handling redirects and expired jobs."""
        if not self.page:
            return False

        try:
            # Navigate and wait for full page load including network requests
            log_to_console(f"   📍 Loading: {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=60000)

            # Extra wait for JS frameworks to initialize (Greenhouse, Lever, etc.)
            await self.page.wait_for_timeout(5000)

            # Check if we were redirected
            final_url = self.page.url
            if final_url != url:
                log_to_console(f"   ↪️  Redirected to: {final_url}")

            # Check for Working Nomads expired job patterns:
            # Pattern 1: Redirected away from /job/go/ to a listing page
            if "workingnomads.com" in final_url and "/job/go/" not in final_url:
                log_to_console(f"   ❌ Job expired - Working Nomads redirected to listing instead of job")
                self.steps.append({
                    "action": "navigate",
                    "url": url,
                    "final_url": final_url,
                    "success": False,
                    "error": "Job expired - Working Nomads redirect failed (job no longer exists)"
                })
                return False

            # Pattern 2: Still on /job/go/ but page has no content (dead link)
            if "workingnomads.com/job/go/" in final_url:
                page_title = await self.page.title()
                body = await self.page.query_selector("body")
                body_text = await body.text_content() if body else ""
                content_length = len(body_text.strip()) if body_text else 0

                # If page has no title or very little content, it's a dead link
                if not page_title or content_length < 500:
                    log_to_console(f"   ❌ Job expired - Working Nomads link dead (no redirect, empty page)")
                    log_to_console(f"      Title: '{page_title}', Content length: {content_length}")
                    self.steps.append({
                        "action": "navigate",
                        "url": url,
                        "final_url": final_url,
                        "success": False,
                        "error": "Job expired - Working Nomads link dead (no redirect occurred)"
                    })
                    return False

            # Check if page has meaningful content
            body = await self.page.query_selector("body")
            if body:
                text_content = await body.text_content()
                content_length = len(text_content.strip()) if text_content else 0

                # Check for common "job not found" or "expired" messages on the ATS page
                # (not on Working Nomads - that's handled above)
                if text_content and "workingnomads.com" not in final_url:
                    text_lower = text_content.lower()
                    expired_indicators = [
                        "job has been closed",
                        "position has been filled",
                        "no longer accepting applications",
                        "this job is no longer available",
                        "this position has been filled",
                        "this job posting has expired",
                        "this requisition is no longer active",
                    ]
                    for indicator in expired_indicators:
                        if indicator in text_lower:
                            log_to_console(f"   ❌ Job expired on ATS: '{indicator}'")
                            self.steps.append({
                                "action": "navigate",
                                "url": url,
                                "final_url": final_url,
                                "success": False,
                                "error": f"Job expired on ATS: {indicator}"
                            })
                            return False

                log_to_console(f"   ✅ Page loaded ({content_length} chars)")
                self.steps.append({"action": "navigate", "url": url, "final_url": final_url, "success": True})
                return True

            # If no body found, page might still be loading - don't mark as expired
            log_to_console("   ⚠️  No body element found, but continuing anyway")
            self.steps.append({"action": "navigate", "url": url, "final_url": final_url, "success": True, "warning": "No body element"})
            return True

        except Exception as e:
            log_to_console(f"   ❌ Navigation failed: {e}")
            self.steps.append({"action": "navigate", "url": url, "success": False, "error": str(e)})
            return False

    async def _find_and_click_apply(self) -> bool:
        """Find and click the Apply button."""
        if not self.page:
            return False

        # Common apply button selectors
        apply_selectors = [
            'a:has-text("Apply")',
            'button:has-text("Apply")',
            'a:has-text("Apply Now")',
            'button:has-text("Apply Now")',
            'a:has-text("Apply for this job")',
            'button:has-text("Apply for this job")',
            '[class*="apply"]',
            '[id*="apply"]',
            'a[href*="apply"]',
        ]

        for selector in apply_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    log_to_console(f"   ✅ Clicked apply button: {selector}")
                    self.steps.append({"action": "click_apply", "selector": selector, "success": True})
                    return True
            except Exception:
                continue

        # If no button found, try Claude to find it
        log_to_console("   🤖 Using Claude to find Apply button...")
        return await self._find_apply_with_claude()

    async def _find_apply_with_claude(self) -> bool:
        """Use Claude to find and click the Apply button."""
        if not self.page:
            return False

        try:
            # Get page HTML
            html = await self.page.content()
            # Truncate to avoid token limits
            html_truncated = html[:50000] if len(html) > 50000 else html

            prompt = f"""Analyze this job posting HTML and find the Apply button or link.

HTML:
{html_truncated}

Return ONLY a JSON object with:
- "selector": CSS selector to click the apply button
- "confidence": 0-100 how confident you are

Example: {{"selector": "a.apply-button", "confidence": 90}}"""

            self.ai_prompts.append(prompt[:500] + "..." if len(prompt) > 500 else prompt)

            response = self.claude.messages.create(
                model=APPLIER_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            self.ai_responses.append(response_text)

            # Parse JSON
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                selector = data.get("selector")
                if selector:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        log_to_console(f"   ✅ Claude found apply button: {selector}")
                        return True

        except Exception as e:
            log_to_console(f"   ❌ Claude apply search failed: {e}")

        return False

    async def _analyze_form(self) -> Optional[dict[str, Any]]:
        """Analyze the application form using Claude."""
        if not self.page:
            return None

        try:
            # Scroll down to ensure all form fields are loaded (lazy loading)
            log_to_console("   📜 Scrolling to load full form...")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(1500)
            await self.page.evaluate("window.scrollTo(0, 0)")  # Scroll back to top
            await self.page.wait_for_timeout(500)

            # First, check for iframes (common for Greenhouse, Lever, etc.)
            iframes = await self.page.query_selector_all('iframe')
            application_frame = None

            for iframe in iframes:
                src = await iframe.get_attribute('src') or ''
                name = await iframe.get_attribute('name') or ''

                # Skip Google API proxy iframes - these are just auth helpers, not forms
                if 'googleapis' in src.lower() or 'recaptcha' in src.lower():
                    continue

                # Common ATS iframe patterns (only if they contain actual application forms)
                ats_patterns = ['lever', 'workable', 'ashby', 'jobvite']  # Removed 'greenhouse' - their forms are on main page
                if any(ats in src.lower() for ats in ats_patterns):
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            # Wait for iframe content to load
                            await frame.wait_for_load_state('domcontentloaded')
                            await self.page.wait_for_timeout(2000)  # Extra wait for JS
                            application_frame = frame
                            log_to_console(f"   📋 Found application iframe: {src[:50]}...")
                            break
                    except Exception as e:
                        log_to_console(f"   ⚠️  Could not access iframe: {e}")
                        continue

            # If no iframe found by src, check all iframes for form content
            if not application_frame:
                for iframe in iframes:
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            # Check if this iframe has form elements
                            form_check = await frame.query_selector('form, input[type="text"], input[type="email"]')
                            if form_check:
                                application_frame = frame
                                log_to_console("   📋 Found form in iframe (by content)")
                                break
                    except Exception:
                        continue

            # Get HTML from frame or main page
            if application_frame:
                html = await application_frame.content()
                # Store the frame reference for later use
                self._application_frame = application_frame
                log_to_console(f"   📄 Got HTML from iframe: {len(html)} chars")
            else:
                html = await self.page.content()
                self._application_frame = None
                log_to_console(f"   📄 Got HTML from main page: {len(html)} chars")

            # Debug: Check if we have actual content
            if len(html) < 5000:
                log_to_console(f"   ⚠️  HTML content seems too short, page may not have loaded properly")
                log_to_console(f"   HTML snippet: {html[:500]}")

            html_truncated = html[:150000] if len(html) > 150000 else html

            # Build profile summary for context
            skills_str = ", ".join(self.profile.skills[:20]) if self.profile.skills else "Not specified"

            # Extract city/country for the prompt
            location_parts = self.profile.location.split(",") if self.profile.location else [""]
            city = location_parts[0].strip() if location_parts else ""
            country = location_parts[1].strip() if len(location_parts) > 1 else "Colombia"

            prompt = f"""Analyze this job application page HTML and identify ALL form fields that need to be filled.

HTML:
{html_truncated}

USER PROFILE DATA AVAILABLE:
- Full Name: {self.profile.name}
- Email: {self.profile.email}
- Phone (full with country code): {self.profile.phone or 'Not provided'}
- Phone country code (parsed from phone): {'+1' if (self.profile.phone or '').startswith('+1') else (self.profile.phone or '')[:3] if (self.profile.phone or '').startswith('+') else 'N/A'}
- Phone (local, without country code): {(self.profile.phone or '')[2:] if (self.profile.phone or '').startswith('+1') else (self.profile.phone or '')[3:] if (self.profile.phone or '').startswith('+') else self.profile.phone or 'Not provided'}
- Full Location: {self.profile.location}
- City: {city}
- Country: {country}
- LinkedIn URL: {self.profile.linkedin or 'Not provided'}
- GitHub URL: {self.profile.github or 'Not provided'}
- Skills: {skills_str}
- Professional Summary: {(self.profile.ai_generated_summary or '')[:500]}

CANDIDATE WORK PREFERENCES:
- Open to contract work: Yes
- Available for meetings 8-11am PT: Yes (flexible schedule)
- Work authorization: International contractor (no US work auth needed for remote)
- Willing to relocate: No (remote only)
- Years of experience: 20+

ADDITIONAL INSTRUCTIONS:
{self.profile.custom_instructions or 'No specific instructions'}

For EACH form field, determine:
1. The CSS selector to target it
2. What type of input it is
3. What value should be filled based on the profile

CRITICAL: You MUST include ALL fields, especially:
- Location/City fields -> use "{city}"
- Country fields -> use "{country}" or "Colombia"
- LinkedIn fields -> use the full URL: {self.profile.linkedin or 'https://linkedin.com/in/...'}
- Yes/No dropdowns -> select "Yes" for contract work, meeting availability, etc.
- Work authorization -> select options that don't require US citizenship/visa

Return a JSON object with:
{{
  "form_found": true/false,
  "fields": [
    {{
      "selector": "CSS selector for the input (be specific, use id or name if available)",
      "type": "text|email|tel|textarea|select|file|checkbox|radio",
      "label": "Field label text",
      "required": true/false,
      "profile_field": "name|first_name|last_name|email|phone|location|city|country|linkedin|github|cv|custom",
      "custom_value": "The value to enter - REQUIRED for custom fields, select dropdowns, city, country"
    }}
  ],
  "submit_selector": "CSS selector for submit button",
  "notes": "Any important observations"
}}

IMPORTANT RULES:
- For name fields, check if it's split into first_name/last_name or a single full name field
- For Location (City) fields, use profile_field="city" with custom_value="{city}"
- For Country fields, use profile_field="country" with custom_value="{country}"
- For select/dropdown fields, ALWAYS provide custom_value with the option text to select
- For Yes/No questions about availability/contract work, answer "Yes"
- For LinkedIn, use the full URL from the profile
- Be specific with CSS selectors - prefer #id or [name="..."] over generic selectors
- DO NOT skip any visible form fields, even if they seem optional
- PHONE NUMBER CRITICAL:
  - If there is a COUNTRY CODE DROPDOWN (showing flags or +XX codes), use profile_field="phone_country_code" for that dropdown. The value is PARSED FROM THE PHONE NUMBER, NOT the user's location. For phone +12124332699, use "+1" or "United States (+1)" - NOT Colombia!
  - If there is a separate phone number input field (without country code), use profile_field="phone_local"
  - If there is a single phone field with NO country dropdown, use profile_field="phone" (full number with country code)"""

            self.ai_prompts.append(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)

            response = self.claude.messages.create(
                model=APPLIER_MODEL,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            self.ai_responses.append(response_text)

            # Parse JSON - handle potential markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                json_str = json_match.group() if json_match else None

            if json_str:
                data = json.loads(json_str)
                form_found = data.get('form_found', False)
                fields = data.get('fields', [])
                log_to_console(f"   ✅ Form found: {form_found}, {len(fields)} fields identified")
                if data.get('notes'):
                    log_to_console(f"   📝 Notes: {data['notes'][:200]}")
                return data
            else:
                log_to_console(f"   ❌ Could not extract JSON from response")
                log_to_console(f"   Response preview: {response_text[:500]}")

        except json.JSONDecodeError as e:
            log_to_console(f"   ❌ Failed to parse form analysis JSON: {e}")
            log_to_console(f"   JSON string: {json_str[:500] if json_str else 'None'}")
        except Exception as e:
            log_to_console(f"   ❌ Form analysis failed: {e}")
            import traceback
            traceback.print_exc()

        return None

    async def _analyze_form_with_vision(self, existing_fields: list[str] = None) -> Optional[dict[str, Any]]:
        """Analyze the form using screenshot + Claude vision to catch fields that HTML analysis may miss."""
        if not self.page:
            return None

        try:
            # Take full-page screenshot of the form
            target = getattr(self, '_application_frame', None) or self.page
            screenshot = await target.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')

            # Extract city/country for the prompt
            location_parts = self.profile.location.split(",") if self.profile.location else [""]
            city = location_parts[0].strip() if location_parts else ""
            country = location_parts[1].strip() if len(location_parts) > 1 else "Colombia"

            existing_fields_str = ", ".join(existing_fields) if existing_fields else "None"

            prompt = f"""Analyze this screenshot of a job application form and identify ALL form fields visible.

IMPORTANT: Focus on finding fields that are EMPTY or showing validation errors (red borders, "required" text).

ALREADY FILLED FIELDS (skip these): {existing_fields_str}

USER PROFILE DATA:
- Name: {self.profile.name}
- Email: {self.profile.email}
- Phone: {self.profile.phone or 'Not provided'}
- City: {city}
- Country: {country}
- LinkedIn: {self.profile.linkedin or 'Not provided'}
- GitHub: {self.profile.github or 'Not provided'}

CANDIDATE PREFERENCES (for Yes/No questions):
- Open to contract work: Yes
- Available for meetings: Yes
- Work authorization: International contractor (no US work auth)
- Willing to relocate: No (remote only)
- Years of experience: 20+

For each UNFILLED field visible in the screenshot, provide:
1. A description of where it is (e.g., "Education section - School dropdown")
2. The type of field (text, dropdown, textarea, checkbox, radio)
3. What value should be selected/entered
4. A suggested CSS selector to target it

Return a JSON object:
{{
  "additional_fields": [
    {{
      "description": "Education - School Name dropdown",
      "type": "select",
      "value": "Other",
      "selector_hints": ["select near 'School' label", "dropdown in education section"]
    }}
  ],
  "error_fields": ["List of fields showing validation errors"],
  "notes": "Any observations about the form state"
}}"""

            self.ai_prompts.append("Vision form analysis prompt (see screenshot)")

            response = self.claude.messages.create(
                model=APPLIER_MODEL,
                max_tokens=4000,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}},
                    {"type": "text", "text": prompt}
                ]}]
            )

            response_text = response.content[0].text
            self.ai_responses.append(response_text)

            # Parse JSON response
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                json_str = json_match.group() if json_match else None

            if json_str:
                data = json.loads(json_str)
                additional = data.get('additional_fields', [])
                errors = data.get('error_fields', [])
                log_to_console(f"   👁️  Vision analysis: {len(additional)} additional fields, {len(errors)} errors")
                if data.get('notes'):
                    log_to_console(f"   📝 Vision notes: {data['notes'][:150]}")
                return data

        except Exception as e:
            log_to_console(f"   ⚠️  Vision analysis failed: {e}")

        return None

    async def _fill_additional_fields(self, vision_analysis: dict[str, Any], job: Job) -> int:
        """Fill additional fields identified by vision analysis."""
        if not self.page or not vision_analysis:
            return 0

        target = getattr(self, '_application_frame', None) or self.page
        filled_count = 0
        additional_fields = vision_analysis.get('additional_fields', [])

        for field in additional_fields:
            try:
                field_desc = field.get('description', '')
                field_type = field.get('type', 'text')
                field_value = field.get('value', '')
                selector_hints = field.get('selector_hints', [])

                if not field_value:
                    continue

                # Try to find the element using various strategies
                element = None

                # Build potential selectors from hints
                potential_selectors = []
                for hint in selector_hints:
                    # Common patterns
                    if 'school' in hint.lower():
                        potential_selectors.extend([
                            'select[name*="school" i]', 'select[id*="school" i]',
                            '[data-field*="school" i] select', 'label:has-text("School") + select',
                            'label:has-text("School") ~ select'
                        ])
                    if 'degree' in hint.lower():
                        potential_selectors.extend([
                            'select[name*="degree" i]', 'select[id*="degree" i]',
                            '[data-field*="degree" i] select', 'label:has-text("Degree") + select'
                        ])
                    if 'discipline' in hint.lower() or 'major' in hint.lower():
                        potential_selectors.extend([
                            'select[name*="discipline" i]', 'select[id*="discipline" i]',
                            'select[name*="major" i]', 'label:has-text("Discipline") + select'
                        ])
                    if 'linkedin' in hint.lower():
                        potential_selectors.extend([
                            'input[name*="linkedin" i]', 'input[id*="linkedin" i]',
                            'input[placeholder*="linkedin" i]'
                        ])
                    if 'salary' in hint.lower() or 'compensation' in hint.lower():
                        potential_selectors.extend([
                            'input[name*="salary" i]', 'input[id*="salary" i]',
                            'input[name*="compensation" i]', 'textarea[name*="salary" i]'
                        ])
                    if 'authorization' in hint.lower() or 'visa' in hint.lower():
                        potential_selectors.extend([
                            'select[name*="authorization" i]', 'select[id*="visa" i]',
                            '[data-field*="authorization" i] select'
                        ])

                # Try each potential selector
                for selector in potential_selectors:
                    try:
                        element = await target.query_selector(selector)
                        if element and await element.is_visible():
                            break
                        element = None
                    except Exception:
                        continue

                if not element:
                    log_to_console(f"   ⚠️  Could not find element for: {field_desc[:50]}")
                    continue

                # Fill based on type
                if field_type == 'select':
                    try:
                        await element.select_option(label=field_value)
                        filled_count += 1
                        log_to_console(f"   ✅ Vision fill: {field_desc[:40]} = {field_value}")
                    except Exception:
                        # Try clicking and typing
                        await element.click()
                        await self.page.wait_for_timeout(300)
                        await element.type(field_value, delay=50)
                        await self.page.keyboard.press("Enter")
                        filled_count += 1
                        log_to_console(f"   ✅ Vision fill (custom): {field_desc[:40]} = {field_value}")

                elif field_type in ['text', 'textarea']:
                    await element.fill(field_value)
                    filled_count += 1
                    log_to_console(f"   ✅ Vision fill: {field_desc[:40]} = {field_value[:30]}")

            except Exception as e:
                log_to_console(f"   ⚠️  Failed to fill {field.get('description', 'unknown')}: {e}")

        return filled_count

    async def _fill_form(self, form_analysis: dict[str, Any], job: Job) -> bool:
        """Fill the application form based on analysis."""
        if not self.page:
            log_to_console("   ❌ No page available")
            return False

        if not form_analysis.get("form_found"):
            log_to_console("   ❌ No form found in analysis")
            self.steps.append({
                "action": "fill_form",
                "success": False,
                "error": "No form found in analysis"
            })
            return False

        fields = form_analysis.get("fields", [])

        if not fields:
            log_to_console("   ❌ No fields found in form analysis")
            self.steps.append({
                "action": "fill_form",
                "success": False,
                "error": "No fields found in form analysis"
            })
            return False
        log_to_console(f"   📋 Processing {len(fields)} fields...")
        filled_count = 0

        # Use the application frame if we found one, otherwise use main page
        target = getattr(self, '_application_frame', None) or self.page

        for field in fields:
            try:
                selector = field.get("selector")
                field_type = field.get("type", "text")
                profile_field = field.get("profile_field")

                if not selector:
                    continue

                # Fix CSS selectors with IDs starting with digits
                selector = self._fix_css_selector(selector)

                element = await target.query_selector(selector)
                if not element:
                    log_to_console(f"   ⚠️  Field not found: {selector} (label: {field.get('label', 'unknown')})")
                    self.steps.append({
                        "action": "fill_field",
                        "selector": selector,
                        "label": field.get("label"),
                        "success": False,
                        "error": "Element not found"
                    })
                    continue

                # Determine value to fill
                value = self._get_field_value(field, job)
                if not value and field_type != "file":
                    log_to_console(f"   ⚠️  No value for field: {field.get('label', selector)}")
                    continue

                # Fill based on type
                field_label = field.get('label') or selector

                if field_type in ["text", "email", "tel"]:
                    # Check if this is an autocomplete field (location fields often are)
                    is_autocomplete = await element.get_attribute('autocomplete') or ''
                    aria_autocomplete = await element.get_attribute('aria-autocomplete') or ''
                    field_label_lower = field_label.lower()
                    is_location_field = any(x in field_label_lower for x in ['location', 'city', 'address'])

                    if is_location_field or 'on' in is_autocomplete or aria_autocomplete:
                        # Location autocomplete - special handling for Google Places
                        autocomplete_value = value
                        if is_location_field:
                            # Extract city name for autocomplete search
                            if ',' in value:
                                autocomplete_value = value.split(',')[0].strip()
                            elif value.lower() in ['colombia', 'remote']:
                                autocomplete_value = "Medellin, Colombia"
                            log_to_console(f"   🔍 Location autocomplete: typing '{autocomplete_value}'")

                        # Clear and focus the field
                        await element.click()
                        await self.page.wait_for_timeout(200)
                        await element.fill('')
                        await self.page.wait_for_timeout(100)

                        # Type slowly to trigger autocomplete
                        await element.type(autocomplete_value, delay=100)
                        await self.page.wait_for_timeout(2500)  # Wait longer for Google Places

                        # CRITICAL: For Google Places, use pac-item selector
                        pac_item_clicked = False
                        try:
                            # Google Places API dropdown items
                            pac_items = await self.page.query_selector_all('.pac-container .pac-item')
                            for pac_item in pac_items:
                                if await pac_item.is_visible():
                                    await pac_item.click()
                                    pac_item_clicked = True
                                    log_to_console(f"   ✅ Clicked Google Places suggestion")
                                    break
                        except Exception as e:
                            log_to_console(f"   ⚠️  Google Places click failed: {e}")

                        if not pac_item_clicked:
                            # Try generic dropdown selectors
                            dropdown_selectors = [
                                '[role="listbox"] [role="option"]',
                                '[class*="autocomplete"] [class*="option"]',
                                '[class*="dropdown"] li:not([class*="disabled"])',
                                'ul[class*="suggestion"] li',
                            ]
                            for sel in dropdown_selectors:
                                try:
                                    options = await self.page.query_selector_all(sel)
                                    for opt in options:
                                        if await opt.is_visible():
                                            await opt.click()
                                            pac_item_clicked = True
                                            log_to_console(f"   ✅ Clicked dropdown option")
                                            break
                                    if pac_item_clicked:
                                        break
                                except Exception:
                                    continue

                        if not pac_item_clicked:
                            # Last resort: ArrowDown + Enter
                            log_to_console(f"   🔄 Using ArrowDown+Enter for location...")
                            await element.focus()
                            await self.page.wait_for_timeout(300)
                            await self.page.keyboard.press("ArrowDown")
                            await self.page.wait_for_timeout(200)
                            await self.page.keyboard.press("Enter")
                            await self.page.wait_for_timeout(500)

                        # Wait and check if value was set
                        await self.page.wait_for_timeout(500)
                        final_value = await element.get_attribute("value") or ""
                        if final_value:
                            log_to_console(f"   ✅ Location set to: {final_value[:40]}")
                        else:
                            # If still empty, set value directly and trigger React events
                            log_to_console(f"   🔄 Setting location value directly via JS...")
                            await self._set_react_input_value(element, autocomplete_value)

                        # Trigger blur for validation
                        await element.evaluate("el => el.blur()")
                        await self.page.wait_for_timeout(200)
                    else:
                        # Normal text field - use React-compatible value setting
                        await element.click()
                        await self.page.wait_for_timeout(100)

                        # Use React-compatible input value setter
                        await self._set_react_input_value(element, value)

                        await self.page.wait_for_timeout(100)

                    filled_count += 1
                    # Track human-readable field/value
                    self.fields_filled.append({"field": field_label, "value": value})
                    log_to_console(f"   ✅ Filled {field_label}: {value[:50]}..." if len(str(value)) > 50 else f"   ✅ Filled {field_label}: {value}")

                elif field_type == "textarea":
                    await element.click()
                    await self.page.wait_for_timeout(100)
                    await element.fill(value)
                    # Dispatch events for frameworks
                    await element.evaluate("""el => {
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""")
                    await element.evaluate("el => el.blur()")
                    filled_count += 1
                    # Track human-readable field/value (truncate long text for display)
                    display_value = value[:100] + "..." if len(value) > 100 else value
                    self.fields_filled.append({"field": field_label, "value": display_value})
                    log_to_console(f"   ✅ Filled textarea {field_label}")

                elif field_type == "select":
                    try:
                        # Try native select first
                        await element.select_option(label=value)
                        filled_count += 1
                        self.fields_filled.append({"field": field_label, "value": value})
                        log_to_console(f"   ✅ Selected {field_label}: {value}")
                    except Exception as select_err:
                        # Might be a custom dropdown (react-select, Greenhouse custom, etc.)
                        log_to_console(f"   ⚠️  Native select failed, trying custom dropdown...")
                        custom_success = False
                        try:
                            # Step 1: Click to open the dropdown
                            await element.click()
                            await self.page.wait_for_timeout(500)

                            # Step 2: Look for dropdown options container
                            option_selectors = [
                                # React-select style
                                f'[class*="option"]:has-text("{value}")',
                                f'[id*="option"]:has-text("{value}")',
                                f'.select__option:has-text("{value}")',
                                # Greenhouse style
                                f'[class*="dropdown"] li:has-text("{value}")',
                                f'[class*="menu"] [class*="option"]:has-text("{value}")',
                                f'[role="option"]:has-text("{value}")',
                                f'[role="listbox"] div:has-text("{value}")',
                                # Generic
                                f'li:has-text("{value}")',
                                f'div[class*="option"]:has-text("{value}")',
                            ]

                            # Step 3: Try to find and click the option
                            for opt_sel in option_selectors:
                                try:
                                    option = await self.page.query_selector(opt_sel)
                                    if option and await option.is_visible():
                                        await option.click()
                                        await self.page.wait_for_timeout(300)
                                        custom_success = True
                                        log_to_console(f"   ✅ Clicked option: {value}")
                                        break
                                except Exception:
                                    continue

                            # Step 4: If no option found, try typing + ArrowDown + Enter
                            if not custom_success:
                                log_to_console(f"   🔄 Trying type + ArrowDown + Enter...")
                                await element.type(value, delay=50)
                                await self.page.wait_for_timeout(500)
                                await self.page.keyboard.press("ArrowDown")
                                await self.page.wait_for_timeout(200)
                                await self.page.keyboard.press("Enter")
                                await self.page.wait_for_timeout(300)
                                custom_success = True

                            if custom_success:
                                filled_count += 1
                                self.fields_filled.append({"field": field_label, "value": value})
                                log_to_console(f"   ✅ Custom dropdown selected: {value}")
                        except Exception as custom_err:
                            log_to_console(f"   ⚠️  Custom dropdown also failed: {custom_err}")
                            self.steps.append({
                                "action": "fill_field",
                                "selector": selector,
                                "type": field_type,
                                "label": field_label,
                                "success": False,
                                "error": f"Select failed: {str(select_err)}"
                            })
                            continue

                elif field_type == "checkbox" and value:
                    is_checked = await element.is_checked()
                    if not is_checked:
                        await element.click()
                    filled_count += 1
                    self.fields_filled.append({"field": field_label, "value": "Checked"})
                    log_to_console(f"   ✅ Checked {field_label}")

                self.steps.append({
                    "action": "fill_field",
                    "selector": selector,
                    "type": field_type,
                    "label": field.get("label"),
                    "value_used": str(value)[:200] if value else None,
                    "success": True
                })

            except Exception as e:
                log_to_console(f"   ⚠️  Error filling field: {e}")
                self.steps.append({
                    "action": "fill_field",
                    "selector": field.get("selector"),
                    "success": False,
                    "error": str(e)
                })

        return filled_count > 0

    def _get_field_value(self, field: dict[str, Any], job: Job) -> Optional[str]:
        """Get the value to fill for a field."""
        profile_field = field.get("profile_field", "")
        custom_value = field.get("custom_value")

        # If custom_value is provided, always use it (Claude's recommendation)
        if custom_value:
            return custom_value

        # Split name into parts for first_name/last_name fields
        name_parts = self.profile.name.split() if self.profile.name else ["", ""]
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        # Extract city from location (format: "City, Country" or just "City")
        location_parts = self.profile.location.split(",") if self.profile.location else [""]
        city = location_parts[0].strip() if location_parts else ""
        country = location_parts[1].strip() if len(location_parts) > 1 else "Colombia"

        # Phone handling - parse country code from the actual phone number
        phone_full = self.profile.phone or ""
        phone_local = phone_full
        phone_country_code = ""

        # Parse country code from phone number prefix
        if phone_full.startswith('+'):
            # Common country codes by length
            if phone_full.startswith('+1'):
                phone_country_code = "+1"
                phone_local = phone_full[2:]
            elif phone_full.startswith('+44'):
                phone_country_code = "+44"
                phone_local = phone_full[3:]
            elif phone_full.startswith('+57'):
                phone_country_code = "+57"
                phone_local = phone_full[3:]
            elif phone_full.startswith('+49'):
                phone_country_code = "+49"
                phone_local = phone_full[3:]
            elif phone_full.startswith('+33'):
                phone_country_code = "+33"
                phone_local = phone_full[3:]
            else:
                # Generic: assume +XX format for 2-digit codes
                phone_country_code = phone_full[:3]
                phone_local = phone_full[3:]
        elif phone_full.startswith('1') and len(phone_full) == 11:
            phone_country_code = "+1"
            phone_local = phone_full[1:]

        mapping = {
            "name": self.profile.name,
            "first_name": first_name,
            "last_name": last_name,
            "email": self.profile.email,
            "phone": phone_full,
            "phone_local": phone_local,  # Phone without country code (for forms with country dropdown)
            "phone_country_code": phone_country_code,  # Just the country code (e.g., "+1")
            "location": self.profile.location,
            "city": city,
            "country": country,
            "linkedin": self.profile.linkedin,
            "github": self.profile.github,
        }

        if profile_field in mapping:
            return mapping[profile_field]

        return None

    async def _upload_cv(self) -> bool:
        """Upload CV file and wait for upload to complete."""
        if not self.page or not self.cv_path:
            return False

        # Use the application frame if we found one, otherwise use main page
        target = getattr(self, '_application_frame', None) or self.page

        try:
            # Try the direct #resume selector first (known to work on Greenhouse)
            resume_input = await target.query_selector('#resume')
            if resume_input:
                try:
                    log_to_console(f"   📎 Found #resume input, uploading directly...")
                    await resume_input.set_input_files(str(self.cv_path))
                    log_to_console(f"   ✅ Uploaded CV via #resume: {self.cv_path.name}")
                    await self.page.wait_for_timeout(2000)
                    # Trigger validation events after upload
                    await self._trigger_validation_after_upload(resume_input)
                    self.steps.append({"action": "upload_cv", "success": True, "method": "resume_id"})
                    return True
                except Exception as e:
                    log_to_console(f"   ⚠️  #resume upload failed: {e}")

            # First try: Set file directly on any visible or hidden file input (before clicking buttons)
            file_inputs = await target.query_selector_all('input[type="file"]')
            log_to_console(f"   🔍 Found {len(file_inputs)} file inputs")

            for file_input in file_inputs:
                try:
                    # Check if this is a resume/CV input by looking at nearby elements
                    input_id = await file_input.get_attribute('id') or ''
                    input_name = await file_input.get_attribute('name') or ''
                    input_accept = await file_input.get_attribute('accept') or ''

                    # Prefer resume/CV inputs, but try all of them
                    is_resume_input = any(x in (input_id + input_name).lower() for x in ['resume', 'cv', 'file', 'document'])

                    log_to_console(f"   📎 Trying file input: id={input_id}, name={input_name}, accept={input_accept}")
                    await file_input.set_input_files(str(self.cv_path))
                    log_to_console(f"   ✅ Uploaded CV via file input: {self.cv_path.name}")
                    await self.page.wait_for_timeout(2000)
                    # Trigger validation events after upload
                    await self._trigger_validation_after_upload(file_input)
                    self.steps.append({"action": "upload_cv", "success": True, "method": "file_input"})
                    return True
                except Exception as e:
                    log_to_console(f"   ⚠️  File input failed: {e}")
                    continue

            # Second try: Click upload button and handle filechooser event
            # Greenhouse-specific: Find the Resume/CV section first, then get the Attach button
            upload_button_selectors = [
                # Greenhouse: Resume section's first button (Attach)
                '#resume-input-section button:first-of-type',
                '#resume_input button:first-of-type',
                '[id*="resume"] button:has-text("Attach")',
                '[id*="resume"] a:has-text("Attach")',
                # Greenhouse: Look in field group containing "resume" label
                'div:has(label:has-text("Resume")) button:first-of-type',
                'div:has(label:has-text("CV")) button:first-of-type',
                # Generic Attach button (but be careful of Dropbox/Google Drive)
                'button:text-is("Attach")', 'a:text-is("Attach")',
                'button:has-text("Attach")', 'a:has-text("Attach")',
                '[data-testid*="attach"]', '[class*="attach"]',
                'button:has-text("Upload")', 'a:has-text("Upload")',
                '[class*="upload-button"]', '[class*="file-upload"]',
                'label[for*="resume"]', 'label[for*="cv"]',
                '[class*="resume"] button', '[class*="cv"] button',
                # Greenhouse-specific selectors
                '[data-source="attach"]', '.attach-or-paste button'
            ]

            for button_sel in upload_button_selectors:
                try:
                    button = await target.query_selector(button_sel)
                    if button and await button.is_visible():
                        log_to_console(f"   🔘 Trying upload button with filechooser: {button_sel}")

                        # Set up filechooser handler before clicking
                        async with self.page.expect_file_chooser(timeout=5000) as fc_info:
                            await button.click()
                            file_chooser = await fc_info.value
                            await file_chooser.set_files(str(self.cv_path))
                            log_to_console(f"   ✅ Uploaded CV via filechooser: {self.cv_path.name}")
                            await self.page.wait_for_timeout(2000)
                            # Trigger validation events after upload
                            await self._trigger_validation_after_upload()
                            self.steps.append({"action": "upload_cv", "success": True, "method": "filechooser"})
                            return True
                except Exception as e:
                    log_to_console(f"   ⚠️  Filechooser method failed for {button_sel}: {e}")
                    continue

            # Third try: Just click buttons and hope file input gets revealed
            for button_sel in upload_button_selectors:
                try:
                    button = await target.query_selector(button_sel)
                    if button and await button.is_visible():
                        log_to_console(f"   🔘 Clicking upload button: {button_sel}")
                        await button.click()
                        await self.page.wait_for_timeout(1000)

                        # Check for new file inputs after clicking
                        new_file_inputs = await target.query_selector_all('input[type="file"]')
                        for fi in new_file_inputs:
                            try:
                                await fi.set_input_files(str(self.cv_path))
                                log_to_console(f"   ✅ Uploaded CV after clicking button: {self.cv_path.name}")
                                await self.page.wait_for_timeout(2000)
                                # Trigger validation events after upload
                                await self._trigger_validation_after_upload(fi)
                                self.steps.append({"action": "upload_cv", "success": True, "method": "click_then_input"})
                                return True
                            except Exception:
                                continue
                        break
                except Exception:
                    continue

            # If all methods fail, look for file inputs one more time
            file_inputs = await target.query_selector_all('input[type="file"]')

            for file_input in file_inputs:
                try:
                    await file_input.set_input_files(str(self.cv_path))
                    log_to_console(f"   ✅ Uploaded CV: {self.cv_path.name}")

                    # Wait for upload to complete - check for various indicators
                    log_to_console("   ⏳ Waiting for upload to complete...")

                    # Wait up to 15 seconds for upload indicators to appear/disappear
                    for i in range(15):
                        await self.page.wait_for_timeout(1000)

                        # Check for "uploading" indicators that should disappear
                        uploading_indicators = await target.query_selector_all(
                            '[class*="uploading"], [class*="loading"], [class*="progress"], '
                            '[aria-busy="true"], [data-uploading="true"], .spinner'
                        )

                        # Check for "upload complete" indicators
                        complete_indicators = await target.query_selector_all(
                            '[class*="uploaded"], [class*="complete"], [class*="success"], '
                            f'[title*="{self.cv_path.name}"], [title*="Resume"], '
                            f':text("{self.cv_path.name}")'
                        )

                        # If we see completion indicators and no uploading indicators, we're done
                        uploading_visible = any([await el.is_visible() for el in uploading_indicators] if uploading_indicators else [False])
                        complete_visible = any([await el.is_visible() for el in complete_indicators] if complete_indicators else [False])

                        if complete_visible and not uploading_visible:
                            log_to_console(f"   ✅ Upload complete (detected at {i+1}s)")
                            break

                        if i == 14:
                            log_to_console("   ⚠️  Upload timeout, proceeding anyway...")

                    # Extra wait for any async processing
                    await self.page.wait_for_timeout(2000)

                    # Trigger validation events on the file input and form
                    await self._trigger_validation_after_upload(file_input)

                    self.steps.append({"action": "upload_cv", "success": True})
                    return True
                except Exception:
                    continue

        except Exception as e:
            log_to_console(f"   ❌ CV upload failed: {e}")

        return False

    async def _set_react_input_value(self, element, value: str) -> None:
        """Set input value using React-compatible native value setter.

        React overrides the value property setter, so normal DOM manipulation
        doesn't update React's internal state. This method uses the native
        HTMLInputElement value setter to bypass React's override and properly
        trigger React's onChange handlers.
        """
        try:
            # Use JavaScript to set value via native setter and dispatch proper events
            await element.evaluate("""(el, newValue) => {
                // Get the native value setter from HTMLInputElement prototype
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value'
                ).set;

                // Use the appropriate setter based on element type
                if (el.tagName === 'TEXTAREA') {
                    nativeTextAreaValueSetter.call(el, newValue);
                } else {
                    nativeInputValueSetter.call(el, newValue);
                }

                // Dispatch events that React listens for
                el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));

                // Also trigger focus/blur for validation
                el.focus();
                el.dispatchEvent(new FocusEvent('focus', { bubbles: true }));

                // Small delay then blur to trigger validation
                setTimeout(() => {
                    el.dispatchEvent(new FocusEvent('blur', { bubbles: true }));
                }, 50);
            }""", value)

            await self.page.wait_for_timeout(100)
        except Exception as e:
            # Fallback to regular fill + type if native setter fails
            log_to_console(f"   ⚠️  Native setter failed, using fallback: {e}")
            await element.fill('')
            await element.type(value, delay=30)
            await element.evaluate("""el => {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }""")

    async def _trigger_validation_after_upload(self, file_input=None) -> None:
        """Trigger form validation events after CV upload to clear red validation indicators."""
        target = getattr(self, '_application_frame', None) or self.page

        try:
            # Step 1: Dispatch events on the file input itself
            if file_input:
                try:
                    await file_input.evaluate("""el => {
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                    }""")
                    log_to_console("   ✅ Dispatched events on file input")
                except Exception:
                    pass

            # Step 2: Find the resume/CV section and trigger validation on parent containers
            resume_section_selectors = [
                '[id*="resume"]', '[id*="cv"]',
                '[class*="resume"]', '[class*="cv"]',
                '[data-field*="resume"]', '[data-field*="cv"]',
                'label:has-text("Resume")', 'label:has-text("CV")'
            ]
            for sel in resume_section_selectors:
                try:
                    section = await target.query_selector(sel)
                    if section:
                        # Trigger on element and all parents
                        await section.evaluate("""el => {
                            let current = el;
                            while (current && current !== document.body) {
                                current.dispatchEvent(new Event('change', { bubbles: true }));
                                current.dispatchEvent(new Event('input', { bubbles: true }));
                                current = current.parentElement;
                            }
                        }""")
                        break
                except Exception:
                    continue

            # Step 3: Click on a different field to trigger blur validation
            try:
                focus_targets = [
                    'input[type="text"]:not([readonly])',
                    'input[type="email"]',
                    'textarea',
                    'h1', 'h2', '.form-header'
                ]
                for ft_sel in focus_targets:
                    try:
                        ft = await target.query_selector(ft_sel)
                        if ft and await ft.is_visible():
                            await ft.click()
                            await self.page.wait_for_timeout(100)
                            # Click away to trigger blur
                            await self.page.keyboard.press("Tab")
                            await self.page.wait_for_timeout(100)
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # Step 4: Trigger React/Vue/Angular form validation via JavaScript
            try:
                await target.evaluate("""() => {
                    // Trigger validation on all forms
                    const forms = document.querySelectorAll('form');
                    forms.forEach(form => {
                        form.dispatchEvent(new Event('change', { bubbles: true }));
                        if (form.checkValidity) form.checkValidity();
                    });

                    // Find and trigger validation on resume-related containers
                    const resumeContainers = document.querySelectorAll('[class*="resume"], [class*="cv"], [id*="resume"], [id*="cv"]');
                    resumeContainers.forEach(el => {
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    });

                    // Force React/Vue state update by simulating user interaction
                    const fileInputs = document.querySelectorAll('input[type="file"]');
                    fileInputs.forEach(input => {
                        if (input.files && input.files.length > 0) {
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    });
                }""")
            except Exception:
                pass

            # Step 5: Wait for validation UI to update
            await self.page.wait_for_timeout(500)

            log_to_console("   ✅ Validation events triggered after upload")

        except Exception as e:
            log_to_console(f"   ⚠️  Validation trigger failed: {e}")

    async def _trigger_global_validation(self) -> None:
        """Tab through all fields to trigger blur validation on LinkedIn, Other, and remaining fields."""
        if not self.page:
            return

        target = getattr(self, '_application_frame', None) or self.page

        try:
            log_to_console("   🔄 Running global validation pass (Tab through fields)...")

            # Use JavaScript to get all visible, focusable form elements
            field_count = await target.evaluate("""() => {
                const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select');
                let count = 0;
                for (const el of inputs) {
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null) {
                        count++;
                    }
                }
                return count;
            }""")

            log_to_console(f"   📋 Found {field_count} focusable fields")

            # Focus the first visible input and Tab through all of them
            first_focused = await target.evaluate("""() => {
                const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select');
                for (const el of inputs) {
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null) {
                        el.focus();
                        return true;
                    }
                }
                return false;
            }""")

            if first_focused:
                # Tab through all fields to trigger blur validation
                for _ in range(min(field_count + 5, 30)):  # Max 30 tabs to avoid infinite loop
                    await self.page.keyboard.press("Tab")
                    await self.page.wait_for_timeout(50)

                # Trigger blur on the currently focused element
                await target.evaluate("""() => {
                    if (document.activeElement) {
                        document.activeElement.blur();
                    }
                }""")

            # Wait for validation UI to update
            await self.page.wait_for_timeout(300)

            log_to_console("   ✅ Global validation pass complete")

        except Exception as e:
            log_to_console(f"   ⚠️  Global validation failed: {e}")

    async def _submit_application(self, form_analysis: Optional[dict[str, Any]] = None) -> bool:
        """Submit the application form using multiple strategies."""
        if not self.page:
            return False

        # Use the application frame if we found one, otherwise use main page
        target = getattr(self, '_application_frame', None) or self.page

        # Wait for reCAPTCHA to load if present (it needs time to initialize)
        try:
            recaptcha = await self.page.query_selector('[class*="recaptcha"], [id*="recaptcha"], iframe[src*="recaptcha"]')
            if recaptcha:
                log_to_console("   ⏳ reCAPTCHA detected, waiting for it to load...")
                await self.page.wait_for_timeout(2000)
        except Exception:
            pass

        async def try_submit_strategies(element, selector: str, source: str) -> bool:
            """Try multiple submit strategies in order of reliability."""
            try:
                await element.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(300)

                # Strategy 1: Regular click (best for JS-handled forms)
                try:
                    log_to_console(f"   🖱️  Trying regular click: {selector}")
                    await element.click(timeout=5000)
                    await self.page.wait_for_timeout(2000)

                    # Check if something changed (early success detection)
                    submit_still_visible = await element.is_visible()
                    if not submit_still_visible:
                        log_to_console(f"   ✅ Submit button disappeared after click")
                        self.steps.append({"action": "submit", "selector": selector, "source": source, "method": "click", "success": True})
                        return True
                except Exception as e:
                    log_to_console(f"   ⚠️  Regular click blocked: {e}")

                # Strategy 2: JavaScript click (bypasses overlay issues)
                try:
                    log_to_console(f"   🖱️  Trying JavaScript click...")
                    await element.evaluate("el => el.click()")
                    await self.page.wait_for_timeout(2000)
                except Exception as e:
                    log_to_console(f"   ⚠️  JS click failed: {e}")

                # Strategy 3: Dispatch click event (most realistic)
                try:
                    log_to_console(f"   🖱️  Trying dispatchEvent click...")
                    await element.evaluate("""el => {
                        el.dispatchEvent(new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }));
                    }""")
                    await self.page.wait_for_timeout(2000)
                except Exception as e:
                    log_to_console(f"   ⚠️  dispatchEvent failed: {e}")

                # Strategy 4: Focus and Enter key (form submission)
                try:
                    log_to_console(f"   ⌨️  Trying focus + Enter...")
                    await element.focus()
                    await self.page.keyboard.press("Enter")
                    await self.page.wait_for_timeout(2000)
                except Exception as e:
                    log_to_console(f"   ⚠️  Enter key failed: {e}")

                # Strategy 5: Force click as last resort
                try:
                    log_to_console(f"   🖱️  Trying force click...")
                    await element.click(force=True)
                    await self.page.wait_for_timeout(2000)
                except Exception as e:
                    log_to_console(f"   ⚠️  Force click failed: {e}")

                # Wait for any network activity to settle
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

                self.steps.append({"action": "submit", "selector": selector, "source": source, "method": "multi-strategy", "success": True})
                return True

            except Exception as e:
                log_to_console(f"   ❌ All submit strategies failed for {selector}: {e}")
                return False

        # Collect all potential submit buttons
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit Application")',
            'button:has-text("Submit")',
            'button:has-text("Apply Now")',
            'button:has-text("Apply")',
            'button:has-text("Send Application")',
            'button:has-text("Send")',
            'button:has-text("Complete")',
            '[class*="submitButton"]',
            '[class*="submit-button"]',
            '[data-testid*="submit"]',
        ]

        # Try Claude's suggested selector first
        if form_analysis and form_analysis.get("submit_selector"):
            selector = self._fix_css_selector(form_analysis["submit_selector"])
            submit_selectors.insert(0, selector)

        # Find and try all submit buttons
        for selector in submit_selectors:
            try:
                element = await target.query_selector(selector)
                if element and await element.is_visible():
                    if await try_submit_strategies(element, selector, "selector"):
                        return True
            except Exception:
                continue

        # Strategy 6: Try to submit the form directly via JavaScript
        log_to_console("   📝 Trying direct form.submit()...")
        try:
            form_submitted = await target.evaluate("""() => {
                const forms = document.querySelectorAll('form');
                for (const form of forms) {
                    if (form.querySelector('button[type="submit"], input[type="submit"]')) {
                        form.submit();
                        return true;
                    }
                }
                return false;
            }""")
            if form_submitted:
                await self.page.wait_for_timeout(3000)
                self.steps.append({"action": "submit", "method": "form.submit()", "success": True})
                return True
        except Exception as e:
            log_to_console(f"   ⚠️  form.submit() failed: {e}")

        # Log failure
        self.steps.append({"action": "submit", "success": False, "error": "All submit strategies failed"})
        log_to_console("   ❌ Could not submit application - all strategies failed")
        return False

    async def _verify_submission(self) -> tuple[bool, str]:
        """
        Verify the application was submitted successfully using AI analysis.

        Returns:
            Tuple of (verified, evidence_description)
        """
        if not self.page:
            return False, "No page available"

        try:
            # Wait for page to settle after submit
            await self.page.wait_for_timeout(3000)

            # Get current state
            url = self.page.url
            content = await self.page.content()
            content_lower = content.lower()

            # First check for error/failure indicators (these take priority)
            error_patterns = [
                "couldn't submit your application", "could not submit",
                "flagged as possible spam", "flagged as spam",
                "application failed", "submission failed",
                "error submitting", "unable to submit",
                "please try again", "something went wrong",
                "validation error", "required field"
            ]

            for pattern in error_patterns:
                if pattern in content_lower:
                    log_to_console(f"   ❌ Verification: Error found '{pattern}'")
                    self.steps.append({
                        "action": "verify_submission",
                        "success": False,
                        "evidence": f"Error pattern: {pattern}",
                        "final_url": url
                    })
                    return False, f"Error indicator: {pattern}"

            # Quick check for obvious success indicators
            success_patterns = [
                "thank you for applying", "thank you for your application",
                "thanks for applying", "application received",
                "successfully submitted", "application submitted",
                "we have received your application", "your application has been submitted",
                "application complete", "we'll be in touch", "we will be in touch",
                "submitted successfully", "application sent"
            ]

            for pattern in success_patterns:
                if pattern in content_lower:
                    log_to_console(f"   ✅ Verification: Found '{pattern}'")
                    self.steps.append({
                        "action": "verify_submission",
                        "success": True,
                        "evidence": f"Text pattern: {pattern}",
                        "final_url": url
                    })
                    return True, f"Success indicator: {pattern}"

            # Check URL for success indicators
            success_url_patterns = ["success", "thank", "confirm", "submitted", "complete", "received"]
            for pattern in success_url_patterns:
                if pattern in url.lower():
                    log_to_console(f"   ✅ Verification: URL contains '{pattern}'")
                    self.steps.append({
                        "action": "verify_submission",
                        "success": True,
                        "evidence": f"URL pattern: {pattern}",
                        "final_url": url
                    })
                    return True, f"URL indicates success: {pattern}"

            # Check if submit button is still visible - if so, form likely didn't submit
            target = getattr(self, '_application_frame', None) or self.page
            submit_button = await target.query_selector(
                'button[type="submit"], button:has-text("Submit Application"), button:has-text("Submit")'
            )

            # Always use AI vision to verify - error messages may appear after form disappears
            # (e.g., Ashby shows spam errors after the button is gone)
            log_to_console("   🤖 Using AI vision to verify submission result...")
            return await self._ai_verify_submission(url)

        except Exception as e:
            log_to_console(f"   ❌ Verification error: {e}")
            self.steps.append({
                "action": "verify_submission",
                "success": False,
                "error": str(e)
            })
            return False, f"Verification error: {e}"

    async def _ai_verify_submission(self, url: str) -> tuple[bool, str]:
        """Use Claude AI to analyze post-submit screenshot and determine if submission worked."""
        try:
            # Take a fresh screenshot for AI analysis
            screenshot = await self.page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')

            prompt = """Analyze this screenshot of a job application page AFTER the submit button was clicked.

Determine if the application was SUCCESSFULLY SUBMITTED or if it FAILED.

Signs of SUCCESS:
- Thank you / confirmation message
- "Application received" or similar text
- The form has been replaced with a success message
- A new page showing confirmation

Signs of FAILURE:
- The same application form is still visible with a Submit button
- Error messages (red text, validation errors)
- Form fields are still editable and visible
- Nothing appears to have changed

IMPORTANT: If the form and Submit button are still clearly visible and the page looks the same as before clicking submit, that means the click DID NOT WORK and the application was NOT submitted.

Respond with ONLY one of these exact responses:
- "SUCCESS: [brief reason]" if the application was submitted
- "FAILED: [brief reason]" if the form is still there or there are errors"""

            response = self.claude.messages.create(
                model=APPLIER_MODEL,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )

            ai_response = response.content[0].text.strip()
            log_to_console(f"   🤖 AI verification: {ai_response}")

            self.ai_prompts.append("verify_submission")
            self.ai_responses.append(ai_response)

            if ai_response.upper().startswith("SUCCESS"):
                self.steps.append({
                    "action": "verify_submission",
                    "success": True,
                    "evidence": f"AI verified: {ai_response}",
                    "final_url": url
                })
                return True, ai_response
            else:
                self.steps.append({
                    "action": "verify_submission",
                    "success": False,
                    "evidence": f"AI determined failure: {ai_response}",
                    "final_url": url
                })
                return False, ai_response

        except Exception as e:
            log_to_console(f"   ❌ AI verification failed: {e}")
            # If AI fails, assume failure since submit button was still visible
            self.steps.append({
                "action": "verify_submission",
                "success": False,
                "evidence": f"AI verification failed, submit button still visible: {e}",
                "final_url": url
            })
            return False, f"Verification uncertain, submit button still visible"

    async def _answer_custom_question(
        self, question: str, job: Job
    ) -> str:
        """Answer a custom question using Claude AI."""
        try:
            prompt = f"""You are helping {self.profile.name} apply for a job.

JOB DETAILS:
- Title: {job.title}
- Company: {job.company}
- Description: {job.description[:2000] if job.description else 'Not available'}

CANDIDATE PROFILE:
- Name: {self.profile.name}
- Location: {self.profile.location}
- Skills: {', '.join(self.profile.skills or [])}
- Summary: {self.profile.ai_generated_summary or 'Not available'}

CUSTOM INSTRUCTIONS FROM CANDIDATE:
{self.profile.custom_instructions or 'None provided'}

QUESTION TO ANSWER:
{question}

Provide a professional, concise answer (2-4 sentences) that highlights relevant experience and enthusiasm for the role. Be authentic and specific."""

            self.ai_prompts.append(prompt)

            response = self.claude.messages.create(
                model=APPLIER_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            answer = response.content[0].text.strip()
            self.ai_responses.append(answer)

            return answer

        except Exception as e:
            log_to_console(f"   ❌ Question answering failed: {e}")
            return ""

    async def _wait_for_user_feedback(self) -> None:
        """
        Wait for user feedback in interactive mode.

        Uses a file-based signaling mechanism:
        - Writes WAITING to /tmp/zapply_screenshots/interactive_status.txt
        - Waits for user to create /tmp/zapply_screenshots/proceed.txt
        - Deletes signal files after proceeding
        """
        import os

        status_file = self.screenshot_dir / "interactive_status.txt"
        proceed_file = self.screenshot_dir / "proceed.txt"

        # Clean up any stale signal files
        if proceed_file.exists():
            proceed_file.unlink()

        # Print fields that were filled
        log_to_console("\n" + "=" * 60)
        log_to_console("INTERACTIVE MODE - FORM FILLED, WAITING FOR YOUR REVIEW")
        log_to_console("=" * 60)
        log_to_console(f"\nScreenshot saved to: {self.screenshot_dir}")
        log_to_console(f"\nFields filled ({len(self.fields_filled)}):")
        for field_info in self.fields_filled:
            field_name = field_info.get("field", "unknown")
            field_value = field_info.get("value", "")
            # Truncate long values
            if len(field_value) > 50:
                field_value = field_value[:50] + "..."
            log_to_console(f"  - {field_name}: {field_value}")

        log_to_console("\n" + "-" * 60)
        log_to_console("TO PROCEED: Create the file /tmp/zapply_screenshots/proceed.txt")
        log_to_console("  Example: touch /tmp/zapply_screenshots/proceed.txt")
        log_to_console("-" * 60)

        # Write status file
        with open(status_file, "w") as f:
            f.write("WAITING")

        # Wait for proceed signal (check every 2 seconds, timeout after 10 minutes)
        max_wait = 600  # 10 minutes
        waited = 0
        while waited < max_wait:
            if proceed_file.exists():
                log_to_console("✅ Proceed signal received, continuing with submission...")
                # Clean up signal files
                proceed_file.unlink()
                if status_file.exists():
                    status_file.unlink()
                return
            await self.page.wait_for_timeout(2000)  # 2 second check interval
            waited += 2

        # Timeout - clean up and continue anyway
        log_to_console("⏰ Timeout waiting for user input, continuing with submission...")
        if status_file.exists():
            status_file.unlink()
