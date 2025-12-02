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
        screenshot_dir: Optional[Path] = None
    ) -> None:
        """
        Initialize job applier.

        Args:
            profile: User profile with application data
            cv_path: Path to CV PDF file
            dry_run: If True, don't actually submit
            screenshot_dir: Directory to save screenshots
        """
        self.profile = profile
        self.cv_path = cv_path
        self.dry_run = dry_run
        self.screenshot_dir = screenshot_dir or Path("/tmp/zapply_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

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
                headless=True,
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

            # Step 4: Fill the form
            log_to_console("📝 Filling application form...")
            fill_success = await self._fill_form(form_analysis, job)
            if not fill_success:
                return False, "Failed to fill application form", self._get_result_data()

            await self._take_screenshot("03_form_filled")

            # Step 5: Upload CV if needed
            if self.cv_path and self.cv_path.exists():
                log_to_console("📎 Uploading CV...")
                await self._upload_cv()
                await self._take_screenshot("04_cv_uploaded")

            # Step 6: Submit application
            if self.dry_run:
                log_to_console("🔒 DRY RUN - Not submitting application")
                await self._take_screenshot("05_ready_to_submit_dry_run")
                return True, "Dry run completed - form filled but not submitted", self._get_result_data()

            log_to_console("🚀 Submitting application...")
            submit_success = await self._submit_application(form_analysis)
            if not submit_success:
                return False, "Failed to submit application", self._get_result_data()

            await self.page.wait_for_timeout(3000)  # Wait for confirmation
            await self._take_screenshot("06_after_submit")

            # Step 7: Verify submission
            log_to_console("✔️  Verifying submission...")
            verified, evidence = await self._verify_submission()

            if verified is True:
                return True, f"Application submitted successfully ({evidence})", self._get_result_data()
            elif verified is False:
                return False, f"Application may have failed: {evidence}", self._get_result_data()
            else:
                # OPTIMISTIC VERIFICATION: If we clicked submit without errors, assume success
                # Many ATS systems don't show clear confirmation - form disappearance or same page is common
                # Better to assume submitted than to incorrectly mark as failed
                return True, f"Application submitted (no confirmation message, but no errors). {evidence}", self._get_result_data()

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

            html_truncated = html[:80000] if len(html) > 80000 else html

            # Build profile summary for context
            skills_str = ", ".join(self.profile.skills[:20]) if self.profile.skills else "Not specified"

            prompt = f"""Analyze this job application page HTML and identify all form fields that need to be filled.

HTML:
{html_truncated}

USER PROFILE DATA AVAILABLE:
- Full Name: {self.profile.name}
- Email: {self.profile.email}
- Phone: {self.profile.phone or 'Not provided'}
- Location: {self.profile.location}
- LinkedIn: {self.profile.linkedin or 'Not provided'}
- GitHub: {self.profile.github or 'Not provided'}
- Skills: {skills_str}
- Professional Summary: {(self.profile.ai_generated_summary or '')[:500]}

CANDIDATE PREFERENCES (use these to answer questions):
{self.profile.custom_instructions or 'No specific instructions'}

For EACH form field, determine:
1. The CSS selector to target it
2. What type of input it is
3. What value should be filled based on the profile

For custom questions (like "Why do you want to work here?"), generate appropriate professional answers based on the candidate's profile.

Return a JSON object with:
{{
  "form_found": true/false,
  "fields": [
    {{
      "selector": "CSS selector for the input (be specific, use id or name if available)",
      "type": "text|email|tel|textarea|select|file|checkbox|radio",
      "label": "Field label text",
      "required": true/false,
      "profile_field": "name|first_name|last_name|email|phone|location|linkedin|github|cv|custom",
      "custom_value": "The value to enter - REQUIRED for custom fields and select dropdowns"
    }}
  ],
  "submit_selector": "CSS selector for submit button",
  "notes": "Any important observations"
}}

IMPORTANT:
- For name fields, check if it's split into first_name/last_name or a single full name field
- For select/dropdown fields, provide the option text to select in custom_value
- For custom questions, provide thoughtful professional answers in custom_value
- For LinkedIn, use the full URL from the profile
- For location questions, use "{self.profile.location}"
- Be specific with CSS selectors - prefer #id or [name="..."] over generic selectors"""

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
                    await element.fill(value)
                    filled_count += 1
                    # Track human-readable field/value
                    self.fields_filled.append({"field": field_label, "value": value})
                    log_to_console(f"   ✅ Filled {field_label}: {value[:50]}..." if len(str(value)) > 50 else f"   ✅ Filled {field_label}: {value}")

                elif field_type == "textarea":
                    await element.fill(value)
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
                        # Might be a custom dropdown - try clicking and typing
                        log_to_console(f"   ⚠️  Native select failed, trying custom dropdown...")
                        try:
                            await element.click()
                            await self.page.wait_for_timeout(500)
                            # Type the value to search/filter
                            await element.type(value, delay=50)
                            await self.page.wait_for_timeout(500)
                            # Press Enter or click first option
                            await self.page.keyboard.press("Enter")
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

        mapping = {
            "name": self.profile.name,
            "first_name": first_name,
            "last_name": last_name,
            "email": self.profile.email,
            "phone": self.profile.phone,
            "location": self.profile.location,
            "linkedin": self.profile.linkedin,
            "github": self.profile.github,
        }

        if profile_field in mapping:
            return mapping[profile_field]

        return None

    async def _upload_cv(self) -> bool:
        """Upload CV file."""
        if not self.page or not self.cv_path:
            return False

        # Use the application frame if we found one, otherwise use main page
        target = getattr(self, '_application_frame', None) or self.page

        try:
            # Find file input
            file_inputs = await target.query_selector_all('input[type="file"]')

            for file_input in file_inputs:
                try:
                    await file_input.set_input_files(str(self.cv_path))
                    log_to_console(f"   ✅ Uploaded CV: {self.cv_path.name}")
                    self.steps.append({"action": "upload_cv", "success": True})
                    return True
                except Exception:
                    continue

        except Exception as e:
            log_to_console(f"   ❌ CV upload failed: {e}")

        return False

    async def _submit_application(self, form_analysis: Optional[dict[str, Any]] = None) -> bool:
        """Submit the application form."""
        if not self.page:
            return False

        # Use the application frame if we found one, otherwise use main page
        target = getattr(self, '_application_frame', None) or self.page

        # Try Claude's suggested selector first
        if form_analysis and form_analysis.get("submit_selector"):
            try:
                selector = self._fix_css_selector(form_analysis["submit_selector"])
                element = await target.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    log_to_console(f"   ✅ Clicked submit (Claude suggested): {selector}")
                    self.steps.append({"action": "submit", "selector": selector, "source": "claude", "success": True})
                    return True
            except Exception as e:
                log_to_console(f"   ⚠️  Claude's submit selector failed: {e}")

        # Common submit button selectors
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Submit Application")',
            'button:has-text("Apply")',
            'button:has-text("Apply Now")',
            'button:has-text("Send")',
            'button:has-text("Send Application")',
            'button:has-text("Complete")',
            '[class*="submit"]',
            '[data-testid*="submit"]',
        ]

        for selector in submit_selectors:
            try:
                element = await target.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    log_to_console(f"   ✅ Clicked submit: {selector}")
                    self.steps.append({"action": "submit", "selector": selector, "success": True})
                    return True
            except Exception:
                continue

        # Log failure
        self.steps.append({"action": "submit", "success": False, "error": "No submit button found"})
        log_to_console("   ❌ Could not find submit button")
        return False

    async def _verify_submission(self) -> tuple[bool, str]:
        """
        Verify the application was submitted successfully.

        Returns:
            Tuple of (verified, evidence_description)
        """
        if not self.page:
            return False, "No page available"

        try:
            # Wait for page changes
            await self.page.wait_for_timeout(3000)

            # Get current page content
            content = await self.page.content()
            url = self.page.url
            content_lower = content.lower()

            # Check for explicit success indicators (extended list)
            success_patterns = [
                # Generic success messages
                ("thank you for applying", "Thank you message"),
                ("thank you for your application", "Thank you message"),
                ("thanks for applying", "Thanks for applying"),
                ("thanks for your application", "Thanks message"),
                ("application received", "Application received confirmation"),
                ("successfully submitted", "Submission success message"),
                ("application submitted", "Application submitted message"),
                ("we have received your application", "Receipt confirmation"),
                ("your application has been submitted", "Submission confirmation"),
                ("application complete", "Application complete message"),
                ("we'll be in touch", "Follow-up promise"),
                ("we will be in touch", "Follow-up promise"),
                ("we'll review your application", "Review promise"),
                ("we will review your application", "Review promise"),
                # ATS-specific success patterns
                ("your application was submitted", "Submission confirmation"),
                ("application sent", "Application sent"),
                ("you have successfully applied", "Success confirmation"),
                ("your submission has been received", "Submission received"),
                # Greenhouse-specific
                ("your application has been received", "Greenhouse confirmation"),
                ("we've received your application", "Greenhouse confirmation"),
                # Lever-specific
                ("application submitted!", "Lever confirmation"),
                # Ashby-specific
                ("submitted successfully", "Ashby confirmation"),
            ]

            for pattern, description in success_patterns:
                if pattern in content_lower:
                    log_to_console(f"   ✅ Verification: {description}")
                    self.steps.append({
                        "action": "verify_submission",
                        "success": True,
                        "evidence": description,
                        "final_url": url
                    })
                    return True, description

            # Check URL for success indicators
            success_url_patterns = ["success", "thank", "confirm", "submitted", "complete", "received"]
            for pattern in success_url_patterns:
                if pattern in url.lower():
                    evidence = f"URL contains '{pattern}': {url}"
                    log_to_console(f"   ✅ Verification: {evidence}")
                    self.steps.append({
                        "action": "verify_submission",
                        "success": True,
                        "evidence": evidence,
                        "final_url": url
                    })
                    return True, evidence

            # Check for error indicators (explicit failures)
            # Be MORE specific to avoid false positives from static form labels
            # These patterns indicate ACTUAL errors, not just field labels
            error_patterns = [
                # Explicit error messages (not static labels)
                ("an error occurred", "error occurred"),
                ("something went wrong", "something went wrong"),
                ("please try again later", "retry message"),
                ("please correct the errors", "form validation errors"),
                ("please fix the following", "validation errors"),
                # Dynamic validation errors (field name + "is required")
                ("first name is required", "missing first name"),
                ("last name is required", "missing last name"),
                ("email is required", "missing email"),
                ("email address is required", "missing email"),
                ("resume is required", "missing resume"),
                ("phone is required", "missing phone"),
                # Field state errors
                ("can't be blank", "empty required field"),
                ("cannot be blank", "empty required field"),
                ("must not be empty", "empty required field"),
                # Format errors
                ("invalid email address", "invalid email"),
                ("invalid email format", "invalid email"),
                ("invalid phone number", "invalid phone"),
                ("not a valid email", "invalid email"),
                # Submission errors
                ("failed to submit", "submission failed"),
                ("submission failed", "submission failed"),
                ("could not process", "processing failed"),
            ]
            for pattern, description in error_patterns:
                if pattern in content_lower:
                    log_to_console(f"   ❌ Verification: Found error indicator '{pattern}'")
                    self.steps.append({
                        "action": "verify_submission",
                        "success": False,
                        "evidence": f"Error indicator: {description}",
                        "final_url": url
                    })
                    return False, f"Error found: {description}"

            # Check if the form is still visible (might indicate submission didn't happen)
            # Use the application frame if available
            target = getattr(self, '_application_frame', None) or self.page
            form_still_visible = await target.query_selector('form input[type="email"], form input[name="email"]')

            if form_still_visible:
                # Form is still there - check if it looks like the same form
                # This could mean submission didn't work
                log_to_console(f"   ⚠️  Form still visible after submission attempt")

            # No clear success or error - inconclusive
            log_to_console(f"   ⚠️  Verification inconclusive - no clear success/error indicators")
            log_to_console(f"   📍 Final URL: {url}")
            self.steps.append({
                "action": "verify_submission",
                "success": None,  # Inconclusive
                "evidence": "No clear success or error indicators found",
                "final_url": url
            })
            return None, f"Inconclusive - final URL: {url}"

        except Exception as e:
            log_to_console(f"   ❌ Verification failed: {e}")
            self.steps.append({
                "action": "verify_submission",
                "success": False,
                "error": str(e)
            })
            return False, f"Verification error: {e}"

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
