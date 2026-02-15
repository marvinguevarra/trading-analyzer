"""Tier configuration for analysis depth levels.

Defines three tiers that control which agents run, budget limits,
and feature flags for each analysis level.

Tiers:
  - Lite:     Technical + News only (Haiku). Fast and cheap.
  - Standard: Technical + News + SEC + Opus synthesis. Balanced.
  - Premium:  Same as Standard with extended thinking. Maximum depth.
"""

TIER_CONFIGS: dict[str, dict] = {
    "lite": {
        "label": "Lite",
        "models": ["haiku"],
        "include_news": True,
        "include_sec": False,
        "include_synthesis": False,
        "extended_thinking": False,
        "max_cost": 0.50,
        "description": "Technical + News only (Haiku). Fast screening.",
    },
    "standard": {
        "label": "Standard",
        "models": ["haiku", "sonnet", "opus"],
        "include_news": True,
        "include_sec": True,
        "include_synthesis": True,
        "extended_thinking": False,
        "max_cost": 3.00,
        "description": "Full analysis with SEC filings and Opus synthesis.",
    },
    "premium": {
        "label": "Premium",
        "models": ["haiku", "sonnet", "opus"],
        "include_news": True,
        "include_sec": True,
        "include_synthesis": True,
        "extended_thinking": True,
        "max_cost": 7.00,
        "description": "Maximum depth with extended thinking.",
    },
}


def get_tier_config(tier: str) -> dict:
    """Get the configuration for a given tier.

    Args:
        tier: Tier name (lite, standard, premium).

    Returns:
        Tier configuration dict.

    Raises:
        ValueError: If tier name is not recognized.
    """
    tier_lower = tier.lower()
    if tier_lower not in TIER_CONFIGS:
        valid = list(TIER_CONFIGS.keys())
        raise ValueError(f"Unknown tier '{tier}'. Choose from: {valid}")
    return TIER_CONFIGS[tier_lower]


def list_tiers() -> list[dict]:
    """List all available tiers with their descriptions.

    Returns:
        List of tier summary dicts.
    """
    return [
        {
            "name": name,
            "label": cfg["label"],
            "max_cost": cfg["max_cost"],
            "description": cfg["description"],
        }
        for name, cfg in TIER_CONFIGS.items()
    ]
