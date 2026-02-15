"""Tier configuration for analysis depth levels.

Single source of truth for tier definitions. Both the backend
orchestrator and the frontend (via GET /config/tiers) read from here.

Tiers:
  - Lite:     Technical + News only (Haiku). Fast and cheap.
  - Standard: Technical + News + SEC + Synthesis (Haiku + Sonnet).
  - Premium:  Same agents but Opus for synthesis. Maximum depth.
"""

from typing import Any

TIER_CONFIGS: dict[str, dict[str, Any]] = {
    "lite": {
        # ── Backend fields (used by orchestrator) ──
        "label": "Lite",
        "models": ["haiku"],
        "include_news": True,
        "include_sec": False,
        "include_synthesis": False,
        "extended_thinking": False,
        "max_cost": 0.50,
        # ── Frontend display fields ──
        "description": "Technical analysis + AI news sentiment",
        "use_case": "Quick checks, learning the platform",
        "price_display": "~$0.01",
        "cost_range": [0.00, 0.02],
        "speed_estimate": "~5 seconds",
        "popular": False,
        "agents": {
            "news": True,
            "fundamental": False,
            "synthesis": False,
        },
        "agent_models": {
            "news": "haiku",
        },
        "features": [
            "Price gap analysis",
            "Support/Resistance levels",
            "Supply/Demand zones",
            "AI news sentiment (Haiku)",
        ],
    },
    "standard": {
        "label": "Standard",
        "models": ["haiku", "sonnet"],
        "include_news": True,
        "include_sec": True,
        "include_synthesis": True,
        "extended_thinking": False,
        "max_cost": 3.00,
        "description": "Complete analysis with SEC filings and AI synthesis",
        "use_case": "Swing trades, informed decisions",
        "price_display": "~$0.28",
        "cost_range": [0.15, 0.40],
        "speed_estimate": "~35 seconds",
        "popular": True,
        "agents": {
            "news": True,
            "fundamental": True,
            "synthesis": True,
        },
        "agent_models": {
            "news": "haiku",
            "fundamental": "sonnet",
            "synthesis": "sonnet",
        },
        "features": [
            "Everything in Lite",
            "SEC 10-K filing analysis (Sonnet)",
            "Financial health assessment",
            "Bull/Bear thesis with AI verdict",
            "Risk/reward analysis",
        ],
    },
    "premium": {
        "label": "Premium",
        "models": ["haiku", "sonnet", "opus"],
        "include_news": True,
        "include_sec": True,
        "include_synthesis": True,
        "extended_thinking": True,
        "max_cost": 7.00,
        "description": "Advanced analysis with Opus-powered deep reasoning",
        "use_case": "High-stakes trades, large positions",
        "price_display": "~$0.45",
        "cost_range": [0.30, 0.60],
        "speed_estimate": "~45 seconds",
        "popular": False,
        "agents": {
            "news": True,
            "fundamental": True,
            "synthesis": True,
        },
        "agent_models": {
            "news": "haiku",
            "fundamental": "sonnet",
            "synthesis": "opus",
        },
        "features": [
            "Everything in Standard",
            "Opus-powered deep reasoning",
            "Higher quality synthesis",
            "Extended thinking for complex setups",
        ],
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
    """List all available tiers (summary format for GET /tiers).

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


def list_tiers_detailed() -> list[dict]:
    """Full tier config for frontend consumption (GET /config/tiers).

    Returns a frontend-friendly list with all display metadata,
    feature lists, pricing, and agent info.
    """
    tiers = []
    for tier_id, cfg in TIER_CONFIGS.items():
        tiers.append({
            "id": tier_id,
            "name": cfg["label"],
            "description": cfg["description"],
            "use_case": cfg["use_case"],
            "price_display": cfg["price_display"],
            "price_min": cfg["cost_range"][0],
            "price_max": cfg["cost_range"][1],
            "max_budget": cfg["max_cost"],
            "speed_estimate": cfg["speed_estimate"],
            "popular": cfg.get("popular", False),
            "features": {
                "technical": True,
                "news": cfg["agents"]["news"],
                "fundamental": cfg["agents"]["fundamental"],
                "synthesis": cfg["agents"]["synthesis"],
            },
            "feature_list": cfg["features"],
            "models": cfg["agent_models"],
        })
    return tiers
