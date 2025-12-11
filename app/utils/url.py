"""URL utilities for handling redirects and URL resolution."""

import httpx

from app.utils import log_to_console


async def resolve_redirect_url(url: str, timeout: float = 10.0) -> str:
    """
    Resolve a redirect URL to its final destination.

    This is useful for job boards like Working Nomads that use redirect URLs
    (e.g., /job/go/123/) that point to the actual job posting page.

    Args:
        url: The URL to resolve (may be a redirect URL)
        timeout: Request timeout in seconds

    Returns:
        The final URL after following redirects, or the original URL if resolution fails
    """
    if not url:
        return url

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.head(url, follow_redirects=False)

            # Check for redirect status codes (301, 302, 303, 307, 308)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if location:
                    log_to_console(f"  🔗 Resolved redirect: {url[:50]}... -> {location[:50]}...")
                    return location

            # No redirect, return original URL
            return url

    except httpx.TimeoutException:
        log_to_console(f"  ⚠️ Timeout resolving URL: {url[:50]}...")
        return url
    except Exception as e:
        log_to_console(f"  ⚠️ Failed to resolve URL: {url[:50]}... - {str(e)}")
        return url
