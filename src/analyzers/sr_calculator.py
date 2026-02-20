"""Support/Resistance Calculator.

Identifies key price levels using multiple methodologies:
1. Pivot points (swing highs/lows)
2. Volume-confirmed levels
3. Psychological round numbers
4. Moving average clusters

Component 3 per PRD.md specification.
No LLM cost - pure Python/math.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("sr_calculator")


@dataclass
class SRLevel:
    """A support or resistance level."""

    price: float
    level_type: str  # "support", "resistance", or "both"
    source: str  # "swing", "volume", "round_number", "ma_cluster"
    strength: int  # 1-10 significance score
    strength_score: int = 0  # 0-100 composite score
    touches: int = 0  # Number of times price tested this level
    breaks: int = 0  # Number of times price broke through this level
    last_test_date: Optional[datetime] = None
    zone_low: float = 0.0  # Lower bound of the zone
    zone_high: float = 0.0  # Upper bound of the zone
    timeframe: str = ""  # e.g. "5min", "15min", "1h", "daily", "weekly"
    is_confluence: bool = False  # True if level appears on 2+ timeframes
    confluence_timeframes: list[str] = field(default_factory=list)

    @property
    def zone_width(self) -> float:
        return self.zone_high - self.zone_low

    @property
    def strength_label(self) -> str:
        """Classify strength by touch count (intuitive for traders)."""
        if self.touches >= 6:
            return "strong"
        elif self.touches >= 3:
            return "moderate"
        return "weak"

    @property
    def label(self) -> str:
        """Human-readable label like 'Strong (10 touches)'."""
        return f"{self.strength_label.capitalize()} ({self.touches} touches)"

    @property
    def days_since_test(self) -> Optional[int]:
        if self.last_test_date is None:
            return None
        delta = datetime.now() - self.last_test_date
        return delta.days

    @property
    def status(self) -> str:
        if self.breaks == 0:
            return "held"
        elif self.breaks >= self.touches // 2:
            return "broken"
        return "tested"

    def to_dict(self) -> dict:
        days = self.days_since_test
        return {
            "price": round(self.price, 2),
            "type": self.level_type,
            "source": self.source,
            "strength": self.strength,
            "strength_score": self.strength_score,
            "strength_label": self.strength_label,
            "touches": self.touches,
            "breaks": self.breaks,
            "status": self.status,
            "last_test": (
                self.last_test_date.isoformat()
                if isinstance(self.last_test_date, datetime)
                else str(self.last_test_date) if self.last_test_date else None
            ),
            "days_since_test": days,
            "label": self.label,
            "zone": [round(self.zone_low, 2), round(self.zone_high, 2)],
            "timeframe": self.timeframe,
            "is_confluence": self.is_confluence,
            "confluence_timeframes": self.confluence_timeframes,
        }


def calculate_levels(
    df: pd.DataFrame,
    current_price: Optional[float] = None,
    lookback_bars: int = 100,
    swing_window: int = 5,
    sensitivity: str = "medium",
    round_number_interval: float = 10.0,
    timeframe_label: str = "",
) -> list[SRLevel]:
    """Calculate all support and resistance levels.

    Args:
        df: DataFrame with OHLCV data.
        current_price: Current price for context. Uses last close if None.
        lookback_bars: How far back to look for levels.
        swing_window: Bars on each side for swing point detection.
        sensitivity: "low", "medium", or "high" - affects zone width.
        round_number_interval: Spacing for psychological levels.
        timeframe_label: Source timeframe tag (e.g. "5min", "daily", "weekly").

    Returns:
        List of S/R levels sorted by strength.
    """
    if current_price is None:
        current_price = float(df["close"].iloc[-1])

    # Use only the lookback window
    analysis_df = df.tail(lookback_bars).copy()

    # Zone width based on sensitivity
    sensitivity_multipliers = {"low": 0.005, "medium": 0.01, "high": 0.02}
    zone_pct = sensitivity_multipliers.get(sensitivity, 0.01)

    all_levels: list[SRLevel] = []

    # Method 1: Swing points (pivot highs/lows)
    swing_levels = find_swing_points(analysis_df, window=swing_window, zone_pct=zone_pct)
    all_levels.extend(swing_levels)

    # Method 2: Volume-confirmed levels
    if "volume" in df.columns and not df["volume"].isna().all():
        volume_levels = calculate_volume_nodes(analysis_df, zone_pct=zone_pct)
        all_levels.extend(volume_levels)

    # Method 3: Psychological round numbers (daily or unspecified only)
    if timeframe_label in ("daily", ""):
        round_levels = detect_round_numbers(
            current_price, interval=round_number_interval, zone_pct=zone_pct
        )
        all_levels.extend(round_levels)

    # Merge nearby levels
    merged = _merge_nearby_levels(all_levels, current_price, zone_pct)

    # Tag each level with its source timeframe
    for level in merged:
        level.timeframe = timeframe_label

    # Classify as support or resistance based on current price
    for level in merged:
        if level.price < current_price:
            level.level_type = "support"
        elif level.price > current_price:
            level.level_type = "resistance"
        else:
            level.level_type = "both"

    # Calculate touch counts and breaks
    for level in merged:
        level.touches, level.breaks, level.last_test_date = _count_touches(
            analysis_df, level.zone_low, level.zone_high, level.level_type
        )

    # Recalculate strength with touch data
    for level in merged:
        level.strength = _calculate_strength(level, current_price, len(analysis_df))
        level.strength_score = _calculate_strength_score(level, analysis_df)

    # Sort by strength_score (composite 0-100)
    merged.sort(key=lambda x: -x.strength_score)

    logger.info(
        f"Found {len(merged)} S/R levels ({timeframe_label or 'default'}): "
        f"{sum(1 for l in merged if l.level_type == 'support')} support, "
        f"{sum(1 for l in merged if l.level_type == 'resistance')} resistance"
    )

    return merged


def find_swing_points(
    df: pd.DataFrame, window: int = 5, zone_pct: float = 0.01
) -> list[SRLevel]:
    """Find swing high/low pivot points.

    A swing high has the highest high within `window` bars on each side.
    A swing low has the lowest low within `window` bars on each side.
    """
    levels = []
    highs = df["high"].values
    lows = df["low"].values
    times = df["time"].values

    for i in range(window, len(df) - window):
        # Swing high
        if highs[i] == max(highs[i - window : i + window + 1]):
            price = float(highs[i])
            zone_w = price * zone_pct
            levels.append(
                SRLevel(
                    price=price,
                    level_type="resistance",
                    source="swing",
                    strength=5,  # Will be recalculated
                    touches=0,
                    last_test_date=pd.Timestamp(times[i]).to_pydatetime(),
                    zone_low=price - zone_w,
                    zone_high=price + zone_w,
                )
            )

        # Swing low
        if lows[i] == min(lows[i - window : i + window + 1]):
            price = float(lows[i])
            zone_w = price * zone_pct
            levels.append(
                SRLevel(
                    price=price,
                    level_type="support",
                    source="swing",
                    strength=5,
                    touches=0,
                    last_test_date=pd.Timestamp(times[i]).to_pydatetime(),
                    zone_low=price - zone_w,
                    zone_high=price + zone_w,
                )
            )

    return levels


def calculate_volume_nodes(
    df: pd.DataFrame, num_bins: int = 50, zone_pct: float = 0.01
) -> list[SRLevel]:
    """Find price levels with high volume concentration (volume profile).

    Bins price action and finds levels where the most volume traded.
    High volume nodes tend to act as support/resistance.
    """
    if "volume" not in df.columns:
        return []

    price_min = df["low"].min()
    price_max = df["high"].max()
    if price_min == price_max:
        return []

    bin_size = (price_max - price_min) / num_bins
    volume_profile = np.zeros(num_bins)

    for _, row in df.iterrows():
        if pd.isna(row.get("volume", np.nan)):
            continue
        bar_low = row["low"]
        bar_high = row["high"]
        bar_volume = row["volume"]

        low_bin = max(0, int((bar_low - price_min) / bin_size))
        high_bin = min(num_bins - 1, int((bar_high - price_min) / bin_size))

        # Distribute volume across bins the bar spans
        bins_spanned = high_bin - low_bin + 1
        if bins_spanned > 0:
            vol_per_bin = bar_volume / bins_spanned
            for b in range(low_bin, high_bin + 1):
                volume_profile[b] += vol_per_bin

    # Find peaks in volume profile (high volume nodes)
    mean_vol = volume_profile.mean()
    std_vol = volume_profile.std()
    threshold = mean_vol + std_vol  # Levels above 1 std dev

    levels = []
    for i, vol in enumerate(volume_profile):
        if vol > threshold:
            price = price_min + (i + 0.5) * bin_size
            zone_w = price * zone_pct
            levels.append(
                SRLevel(
                    price=round(price, 2),
                    level_type="both",
                    source="volume",
                    strength=5,
                    touches=0,
                    last_test_date=None,
                    zone_low=price - zone_w,
                    zone_high=price + zone_w,
                )
            )

    return levels


def detect_round_numbers(
    current_price: float, interval: float = 10.0, zone_pct: float = 0.01, count: int = 5
) -> list[SRLevel]:
    """Generate psychological round number levels around current price.

    Round numbers ($50, $100, $150) often act as S/R because of human psychology.
    """
    levels = []

    # Find nearest round number below
    base = (current_price // interval) * interval

    # Generate levels above and below
    for i in range(-count, count + 1):
        price = base + (i * interval)
        if price <= 0:
            continue
        zone_w = price * zone_pct
        levels.append(
            SRLevel(
                price=price,
                level_type="support" if price < current_price else "resistance",
                source="round_number",
                strength=3,  # Lower base strength for round numbers
                touches=0,
                last_test_date=None,
                zone_low=price - zone_w,
                zone_high=price + zone_w,
            )
        )

    return levels


def _merge_nearby_levels(
    levels: list[SRLevel], current_price: float, zone_pct: float
) -> list[SRLevel]:
    """Merge levels that are within zone_pct of each other.

    When two levels overlap, keep the stronger one and boost its strength.
    """
    if not levels:
        return []

    # Sort by price
    sorted_levels = sorted(levels, key=lambda x: x.price)
    merged: list[SRLevel] = [sorted_levels[0]]

    merge_threshold = current_price * zone_pct * 2

    for level in sorted_levels[1:]:
        last = merged[-1]
        if abs(level.price - last.price) <= merge_threshold:
            # Merge: keep the one from a better source, boost strength
            source_priority = {"swing": 3, "volume": 2, "round_number": 1, "ma_cluster": 2}
            if source_priority.get(level.source, 0) > source_priority.get(last.source, 0):
                level.strength = min(10, last.strength + 1)
                merged[-1] = level
            else:
                last.strength = min(10, last.strength + 1)
        else:
            merged.append(level)

    return merged


def detect_confluence(
    all_levels: list[SRLevel], threshold_pct: float = 0.005
) -> list[SRLevel]:
    """Merge levels from different timeframes that are within threshold_pct.

    When a daily level at $252.18 and a weekly level at $252.50 are within
    0.5% of each other, they are merged into a single confluence level with
    boosted strength.

    Args:
        all_levels: Combined levels from multiple timeframe runs.
        threshold_pct: Maximum price distance (as fraction) for merging.

    Returns:
        Deduplicated list with confluence levels merged.
    """
    if not all_levels:
        return []

    # Sort by price for efficient pairwise comparison
    sorted_levels = sorted(all_levels, key=lambda x: x.price)
    merged_indices: set[int] = set()
    result: list[SRLevel] = []

    for i, level_a in enumerate(sorted_levels):
        if i in merged_indices:
            continue

        # Collect all levels within threshold from different timeframes
        cluster = [level_a]
        cluster_indices = [i]

        for j in range(i + 1, len(sorted_levels)):
            if j in merged_indices:
                continue
            level_b = sorted_levels[j]

            # Stop scanning once prices diverge beyond threshold
            if level_a.price > 0:
                distance = abs(level_b.price - level_a.price) / level_a.price
            else:
                break
            if distance > threshold_pct * 3:
                break

            # Only merge across different timeframes
            if (
                distance <= threshold_pct
                and level_b.timeframe != level_a.timeframe
            ):
                cluster.append(level_b)
                cluster_indices.append(j)

        if len(cluster) == 1:
            # No confluence — pass through unchanged
            result.append(level_a)
        else:
            # Merge into a single confluence level
            merged_indices.update(cluster_indices)
            avg_price = sum(l.price for l in cluster) / len(cluster)
            total_touches = sum(l.touches for l in cluster)
            total_breaks = sum(l.breaks for l in cluster)
            max_strength = max(l.strength for l in cluster)
            best = max(cluster, key=lambda l: l.strength_score)

            # Collect unique timeframes
            timeframes = sorted(set(l.timeframe for l in cluster if l.timeframe))

            # Zone: widest envelope
            zone_low = min(l.zone_low for l in cluster)
            zone_high = max(l.zone_high for l in cluster)

            # Most recent test date
            test_dates = [l.last_test_date for l in cluster if l.last_test_date]
            last_test = max(test_dates) if test_dates else None

            confluent = SRLevel(
                price=round(avg_price, 2),
                level_type=best.level_type,
                source=best.source,
                strength=min(10, max_strength + 2),
                strength_score=best.strength_score,
                touches=total_touches,
                breaks=total_breaks,
                last_test_date=last_test,
                zone_low=zone_low,
                zone_high=zone_high,
                timeframe=" + ".join(timeframes),
                is_confluence=True,
                confluence_timeframes=timeframes,
            )
            result.append(confluent)

    return result


def _count_touches(
    df: pd.DataFrame, zone_low: float, zone_high: float, level_type: str = "support"
) -> tuple[int, int, Optional[datetime]]:
    """Count how many bars touched a price zone and how many broke through.

    Returns:
        (touches, breaks, last_touch_date)
    """
    touches = 0
    breaks = 0
    last_touch = None

    for _, row in df.iterrows():
        # A bar touches the zone if its range overlaps with the zone
        if row["low"] <= zone_high and row["high"] >= zone_low:
            touches += 1
            last_touch = pd.Timestamp(row["time"]).to_pydatetime()

            # Check if it broke through
            if level_type == "support" and row["close"] < zone_low:
                breaks += 1
            elif level_type == "resistance" and row["close"] > zone_high:
                breaks += 1

    return touches, breaks, last_touch


def _calculate_strength(
    level: SRLevel, current_price: float, total_bars: int
) -> int:
    """Calculate final strength score (1-10) for a level.

    Factors:
    - Number of touches (more = stronger)
    - Source methodology (swing > volume > round)
    - Proximity to current price (closer = more relevant)
    - Recency of last test
    """
    score = 0.0

    # Touch contribution (0-3)
    if level.touches >= 5:
        score += 3.0
    elif level.touches >= 3:
        score += 2.0
    elif level.touches >= 1:
        score += 1.0

    # Source contribution (0-3)
    source_scores = {"swing": 3.0, "volume": 2.5, "ma_cluster": 2.0, "round_number": 1.5}
    score += source_scores.get(level.source, 1.0)

    # Proximity (0-2): levels closer to current price are more actionable
    distance_pct = abs(level.price - current_price) / current_price
    if distance_pct < 0.05:
        score += 2.0
    elif distance_pct < 0.10:
        score += 1.5
    elif distance_pct < 0.20:
        score += 1.0
    else:
        score += 0.5

    # Base strength from merging
    score += level.strength * 0.2

    return max(1, min(10, round(score)))


def _calculate_strength_score(level: SRLevel, df: pd.DataFrame) -> int:
    """Calculate composite strength score (0-100).

    Components:
    - Touch count (0-40): more touches = stronger
    - Volume (0-20): higher volume at level = stronger
    - Recency (0-20): more recent test = stronger
    - Held vs broken (0-20): fewer breaks = stronger
    """
    score = 0

    # Touch count (0-40 points, 4 pts per touch, max 40)
    score += min(level.touches * 4, 40)

    # Volume component (0-20 points)
    # Use volume percentile if available; simplified: source-based proxy
    if "volume" in level.source:
        score += 15
    elif level.source == "swing":
        score += 10
    else:
        score += 5

    # Recency (0-20 points): lose 2 pts per day since last test
    days = level.days_since_test
    if days is not None:
        recency = max(0, 20 - (days * 2))
        score += recency
    else:
        score += 5  # Unknown recency gets partial credit

    # Held vs broken (0-20 points)
    if level.breaks == 0:
        score += 20
    else:
        score += max(0, 20 - (level.breaks * 5))

    return max(0, min(100, score))


def summarize_levels(
    levels: list[SRLevel],
    current_price: float,
    timeframes_analyzed: list[str] | None = None,
    lookback_periods: dict[str, str] | None = None,
) -> dict:
    """Generate a summary of S/R analysis results.

    Args:
        levels: All S/R levels (may include confluence-merged levels).
        current_price: Current price for nearest-level calculations.
        timeframes_analyzed: List of timeframes used (e.g. ["15min", "daily", "weekly"]).
        lookback_periods: Human-readable lookback descriptions per timeframe.
    """
    support = [l for l in levels if l.level_type == "support"]
    resistance = [l for l in levels if l.level_type == "resistance"]

    # Nearest support and resistance
    nearest_support = min(support, key=lambda l: current_price - l.price) if support else None
    nearest_resistance = min(
        resistance, key=lambda l: l.price - current_price
    ) if resistance else None

    # Split into key vs minor levels
    # Key: confluence OR strength >= 8
    # Minor: everything else; round-number-only levels stay minor unless confluence
    key = []
    minor = []
    for level in levels:
        is_key = level.is_confluence or level.strength >= 8
        if level.source == "round_number" and not level.is_confluence:
            is_key = False
        if is_key:
            key.append(level)
        else:
            minor.append(level)

    return {
        "current_price": round(current_price, 2),
        "total_levels": len(levels),
        "support_levels": [l.to_dict() for l in sorted(support, key=lambda x: -x.price)],
        "resistance_levels": [l.to_dict() for l in sorted(resistance, key=lambda x: x.price)],
        "nearest_support": nearest_support.to_dict() if nearest_support else None,
        "nearest_resistance": nearest_resistance.to_dict() if nearest_resistance else None,
        "key_levels": [l.to_dict() for l in key],
        "minor_levels": [l.to_dict() for l in minor],
        "timeframes_analyzed": timeframes_analyzed or [],
        "lookback_periods": lookback_periods or {},
        "explanation": (
            "Key levels are confluence zones (confirmed across multiple timeframes) "
            "or high-strength levels. Minor levels are single-timeframe levels or "
            "psychological round numbers without structural backing."
        ),
    }
