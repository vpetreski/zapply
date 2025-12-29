"""Initialize user profile with CV for matching.

DEPRECATED: This script is deprecated. Use the Profile UI instead:
1. Go to http://localhost:3000/profile
2. Upload your CV
3. Provide custom instructions
4. Generate profile with AI

This script is kept for reference only.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))


async def init_user_profile():
    """Initialize user profile from environment settings.

    DEPRECATED: This function is deprecated.
    Use the Profile UI instead.
    """
    print("=" * 60)
    print("DEPRECATED SCRIPT")
    print("=" * 60)
    print()
    print("This script is deprecated and no longer functional.")
    print()
    print("Please use the Profile UI instead:")
    print("  1. Start the backend: just dev-backend")
    print("  2. Start the frontend: just dev-frontend")
    print("  3. Go to: http://localhost:3000/profile")
    print("  4. Upload your CV (PDF)")
    print("  5. Add custom instructions")
    print("  6. Click 'Generate with AI' to create your profile")
    print()
    print("The UI provides better profile management with AI-powered")
    print("summary generation based on your CV content.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(init_user_profile())
