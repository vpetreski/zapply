"""AI model constants for different use cases.

Each feature uses the appropriate model based on its requirements:
- Sonnet: Fast, cost-effective, good for structured analysis
- Opus: Maximum intelligence, for complex reasoning tasks
"""

# Sonnet 4.5 - Best balance of intelligence, speed, and cost
# $3/MTok input, $15/MTok output
CLAUDE_SONNET = "claude-sonnet-4-5-20250929"

# Opus 4.5 - Maximum intelligence, premium performance
# $5/MTok input, $25/MTok output
CLAUDE_OPUS = "claude-opus-4-5-20251101"

# =============================================================================
# Model assignments per feature
# =============================================================================

# Job matching - structured analysis with clear criteria
# Sonnet is fast and accurate enough for MATCH/REJECT decisions
MATCHING_MODEL = CLAUDE_SONNET

# Profile generation from CV - structured extraction
# Sonnet handles JSON extraction well
PROFILE_GENERATION_MODEL = CLAUDE_SONNET

