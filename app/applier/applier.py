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
                args=['--no-sandbox', '--disable-setuid-sandbox']
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

            # Step 2: Find and click Apply button
            log_to_console("🔍 Looking for Apply button...")
            apply_clicked = await self._find_and_click_apply()
            if not apply_clicked:
                return False, "Could not find Apply button", self._get_result_data()

            await self.page.wait_for_timeout(2000)  # Wait for page/modal to load
            await self._take_screenshot("02_after_apply_click")

            # Step 3: Analyze the application form
            log_to_console("🤖 Analyzing application form with Claude...")
            form_analysis = await self._analyze_form()
            if not form_analysis:
                return False, "Could not analyze application form", self._get_result_data()

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
            submit_success = await self._submit_application()
            if not submit_success:
                return False, "Failed to submit application", self._get_result_data()

            await self.page.wait_for_timeout(3000)  # Wait for confirmation
            await self._take_screenshot("06_after_submit")

            # Step 7: Verify submission
            log_to_console("✔️  Verifying submission...")
            verified = await self._verify_submission()

            if verified:
                return True, "Application submitted successfully", self._get_result_data()
            else:
                return False, "Could not verify submission success", self._get_result_data()

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
            "steps": self.steps
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
            # Navigate with domcontentloaded first (faster), then wait for JS redirects
            log_to_console(f"   📍 Loading: {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for potential JS redirects
            await self.page.wait_for_timeout(3000)

            # Check if we were redirected
            final_url = self.page.url
            if final_url != url:
                log_to_console(f"   ↪️  Redirected to: {final_url}")

            # Check for Working Nomads expired job patterns:
            # 1. Redirects to job listing page (e.g., /remote-development-jobs)
            if "workingnomads.com/" in final_url:
                if "/job/go/" not in final_url and "/jobs" not in final_url:
                    # Redirected to category page like /remote-development-jobs
                    log_to_console("   ❌ Job appears to be expired (redirected to category listing)")
                    self.steps.append({
                        "action": "navigate",
                        "url": url,
                        "final_url": final_url,
                        "success": False,
                        "error": "Job expired - redirected to category listing"
                    })
                    return False
                if "workingnomads.com/jobs" in final_url and "/job/" not in final_url:
                    log_to_console("   ❌ Job appears to be expired (redirected to job listing)")
                    self.steps.append({
                        "action": "navigate",
                        "url": url,
                        "final_url": final_url,
                        "success": False,
                        "error": "Job expired - redirected to job listing"
                    })
                    return False

            # Check if page has meaningful content
            body = await self.page.query_selector("body")
            if body:
                text_content = await body.text_content()

                # If page is empty or nearly empty, it's likely expired
                if not text_content or len(text_content.strip()) < 100:
                    log_to_console(f"   ❌ Page is empty or has minimal content ({len(text_content.strip()) if text_content else 0} chars)")
                    self.steps.append({
                        "action": "navigate",
                        "url": url,
                        "final_url": final_url,
                        "success": False,
                        "error": "Job expired - page returned empty content"
                    })
                    return False

                # Check for common "job not found" or "expired" messages
                text_lower = text_content.lower()
                expired_indicators = [
                    "job has been closed",
                    "position has been filled",
                    "no longer accepting",
                    "job not found",
                    "this job is no longer available",
                    "position is no longer available",
                    "this position has been filled",
                    "job has expired",
                    "no longer available",
                    "this job posting has expired",
                ]
                for indicator in expired_indicators:
                    if indicator in text_lower:
                        log_to_console(f"   ❌ Job appears to be expired: '{indicator}'")
                        self.steps.append({
                            "action": "navigate",
                            "url": url,
                            "final_url": final_url,
                            "success": False,
                            "error": f"Job expired: {indicator}"
                        })
                        return False

                log_to_console(f"   ✅ Page loaded ({len(text_content)} chars)")
                self.steps.append({"action": "navigate", "url": url, "final_url": final_url, "success": True})
                return True

            # If no body found at all
            log_to_console("   ❌ No body element found on page")
            self.steps.append({
                "action": "navigate",
                "url": url,
                "final_url": final_url,
                "success": False,
                "error": "No body element found"
            })
            return False

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
            # First, check for iframes (common for Greenhouse, Lever, etc.)
            iframes = await self.page.query_selector_all('iframe')
            application_frame = None

            for iframe in iframes:
                src = await iframe.get_attribute('src') or ''
                # Common ATS iframe patterns
                if any(ats in src.lower() for ats in ['greenhouse', 'lever', 'workable', 'ashby', 'jobvite']):
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            application_frame = frame
                            log_to_console(f"   📋 Found application iframe: {src[:50]}...")
                            break
                    except Exception as e:
                        log_to_console(f"   ⚠️  Could not access iframe: {e}")

            # Get HTML from frame or main page
            if application_frame:
                html = await application_frame.content()
                # Store the frame reference for later use
                self._application_frame = application_frame
            else:
                html = await self.page.content()
                self._application_frame = None

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
            return False

        fields = form_analysis.get("fields", [])
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
                if field_type in ["text", "email", "tel"]:
                    await element.fill(value)
                    filled_count += 1
                    log_to_console(f"   ✅ Filled {field.get('label', selector)}")

                elif field_type == "textarea":
                    await element.fill(value)
                    filled_count += 1
                    log_to_console(f"   ✅ Filled textarea {field.get('label', selector)}")

                elif field_type == "select":
                    await element.select_option(label=value)
                    filled_count += 1

                elif field_type == "checkbox" and value:
                    is_checked = await element.is_checked()
                    if not is_checked:
                        await element.click()
                    filled_count += 1

                self.steps.append({
                    "action": "fill_field",
                    "selector": selector,
                    "type": field_type,
                    "label": field.get("label"),
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

    async def _submit_application(self) -> bool:
        """Submit the application form."""
        if not self.page:
            return False

        # Use the application frame if we found one, otherwise use main page
        target = getattr(self, '_application_frame', None) or self.page

        # Common submit button selectors
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Submit Application")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
            '[class*="submit"]',
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

        return False

    async def _verify_submission(self) -> bool:
        """Verify the application was submitted successfully."""
        if not self.page:
            return False

        try:
            # Wait for page changes
            await self.page.wait_for_timeout(2000)

            # Get current page content
            content = await self.page.content()
            url = self.page.url

            # Check for success indicators
            success_patterns = [
                "thank you",
                "application received",
                "successfully submitted",
                "application submitted",
                "we have received",
                "confirmation",
            ]

            content_lower = content.lower()
            for pattern in success_patterns:
                if pattern in content_lower:
                    log_to_console(f"   ✅ Found success indicator: '{pattern}'")
                    return True

            # Check URL for success indicators
            if "success" in url.lower() or "thank" in url.lower() or "confirm" in url.lower():
                log_to_console(f"   ✅ Success URL detected: {url}")
                return True

            log_to_console("   ⚠️  Could not confirm submission success")
            return False

        except Exception as e:
            log_to_console(f"   ❌ Verification failed: {e}")
            return False

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
