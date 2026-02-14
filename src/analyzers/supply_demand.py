"""Supply/Demand Zone Identifier.

Identifies institutional accumulation (demand) and distribution (supply) zones
using price action and volume analysis.

Key patterns:
- Rally-Base-Rally (RBR): Demand zone continuation
- Drop-Base-Drop (DBD): Supply zone continuation
- Rally-Base-Drop (RBD): Supply zone reversal
- Drop-Base-Rally (DBR): Demand zone reversal

Component 4 per PRD.md specification.
No LLM cost - pure Python/math.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("supply_demand")


@dataclass
class Zone:
    """A supply or demand zone."""

    zone_type: str  # "supply" or "demand"
    pattern: str  # "RBR", "DBD", "RBD", "DBR"
    price_low: float
    price_high: float
    start_date: datetime
    end_date: datetime  # When the base ended
    strength: int  # 1-10
    fresh: bool  # Has price returned to test this zone?
    test_count: int  # Number of times price returned to zone
    volume_confirmed: bool  # Was there a volume spike?
    move_size_pct: float  # Size of the explosive move from the zone

    @property
    def midpoint(self) -> float:
        return (self.price_low + self.price_high) / 2

    @property
    def width(self) -> float:
        return self.price_high - self.price_low

    @property
    def width_pct(self) -> float:
        if self.midpoint == 0:
            return 0
        return (self.width / self.midpoint) * 100

    def to_dict(self) -> dict:
        return {
            "type": self.zone_type,
            "pattern": self.pattern,
            "price_low": round(self.price_low, 2),
            "price_high": round(self.price_high, 2),
            "midpoint": round(self.midpoint, 2),
            "width_pct": round(self.width_pct, 2),
            "start_date": self.start_date.isoformat() if isinstance(self.start_date, datetime) else str(self.start_date),
            "end_date": self.end_date.isoformat() if isinstance(self.end_date, datetime) else str(self.end_date),
            "strength": self.strength,
            "fresh": self.fresh,
            "test_count": self.test_count,
            "volume_confirmed": self.volume_confirmed,
            "move_size_pct": round(self.move_size_pct, 2),
        }


def identify_zones(
    df: pd.DataFrame,
    min_move_pct: float = 3.0,
    consolidation_bars: int = 5,
    volume_threshold: float = 1.5,
) -> list[Zone]:
    """Identify supply and demand zones.

    Logic:
    1. Find explosive price moves (>min_move_pct in a single bar or few bars)
    2. Look for the base (consolidation) before the move
    3. The base zone becomes a supply or demand zone
    4. Track if the zone has been tested

    Args:
        df: DataFrame with OHLCV data.
        min_move_pct: Minimum move percentage to qualify as explosive.
        consolidation_bars: Maximum bars for a base/consolidation.
        volume_threshold: Volume multiplier above average for confirmation.

    Returns:
        List of supply and demand zones sorted by strength.
    """
    if len(df) < 5:
        return []

    zones: list[Zone] = []

    # Calculate bar-to-bar moves
    df = df.copy()
    df["bar_move_pct"] = ((df["close"] - df["open"]) / df["open"] * 100).abs()
    df["bar_direction"] = np.where(df["close"] > df["open"], 1, -1)

    has_volume = "volume" in df.columns and not df["volume"].isna().all()
    avg_volume = df["volume"].mean() if has_volume else 0

    # Find explosive moves
    explosive_indices = df.index[df["bar_move_pct"] >= min_move_pct].tolist()

    for idx in explosive_indices:
        pos = df.index.get_loc(idx)
        if pos < 2:
            continue

        move_direction = int(df["bar_direction"].iloc[pos])
        move_size_pct = float(df["bar_move_pct"].iloc[pos])

        # Look for base zone before the explosive move
        base = _find_base_zone(df, pos, consolidation_bars)
        if base is None:
            continue

        base_start_pos, base_end_pos = base
        base_start = df.iloc[base_start_pos]
        base_end = df.iloc[base_end_pos]

        # Determine base range
        base_slice = df.iloc[base_start_pos : base_end_pos + 1]
        zone_low = float(base_slice["low"].min())
        zone_high = float(base_slice["high"].max())

        # Determine zone type and pattern
        # Check move before the base
        pre_direction = _get_pre_move_direction(df, base_start_pos)

        if move_direction > 0:  # Explosive move up
            zone_type = "demand"
            if pre_direction > 0:
                pattern = "RBR"  # Rally-Base-Rally
            else:
                pattern = "DBR"  # Drop-Base-Rally
        else:  # Explosive move down
            zone_type = "supply"
            if pre_direction < 0:
                pattern = "DBD"  # Drop-Base-Drop
            else:
                pattern = "RBD"  # Rally-Base-Drop

        # Volume confirmation
        volume_confirmed = False
        if has_volume and avg_volume > 0:
            explosive_volume = float(df["volume"].iloc[pos])
            volume_confirmed = explosive_volume > avg_volume * volume_threshold

        # Check freshness and test count
        fresh, test_count = _check_zone_freshness(
            df, pos, zone_low, zone_high, zone_type
        )

        # Calculate strength
        strength = _calculate_zone_strength(
            move_size_pct=move_size_pct,
            volume_confirmed=volume_confirmed,
            fresh=fresh,
            test_count=test_count,
            pattern=pattern,
            width_pct=(zone_high - zone_low) / ((zone_high + zone_low) / 2) * 100 if zone_high + zone_low > 0 else 0,
        )

        start_dt = pd.Timestamp(base_start["time"]).to_pydatetime()
        end_dt = pd.Timestamp(base_end["time"]).to_pydatetime()

        zones.append(
            Zone(
                zone_type=zone_type,
                pattern=pattern,
                price_low=zone_low,
                price_high=zone_high,
                start_date=start_dt,
                end_date=end_dt,
                strength=strength,
                fresh=fresh,
                test_count=test_count,
                volume_confirmed=volume_confirmed,
                move_size_pct=move_size_pct,
            )
        )

    # Remove duplicate/overlapping zones
    zones = _deduplicate_zones(zones)

    # Sort by strength
    zones.sort(key=lambda z: -z.strength)

    logger.info(
        f"Found {len(zones)} zones: "
        f"{sum(1 for z in zones if z.zone_type == 'demand')} demand, "
        f"{sum(1 for z in zones if z.zone_type == 'supply')} supply, "
        f"{sum(1 for z in zones if z.fresh)} fresh"
    )

    return zones


def _find_base_zone(
    df: pd.DataFrame, explosive_pos: int, max_bars: int
) -> Optional[tuple[int, int]]:
    """Find the consolidation base before an explosive move.

    A base is a narrow range of bars with small moves preceding the explosion.
    """
    # Look backward from the explosive bar
    base_end_pos = explosive_pos - 1
    if base_end_pos < 0:
        return None

    base_start_pos = base_end_pos

    # Walk backward looking for small bars (consolidation)
    for i in range(base_end_pos, max(0, base_end_pos - max_bars), -1):
        bar_range = (df["high"].iloc[i] - df["low"].iloc[i])
        bar_mid = (df["high"].iloc[i] + df["low"].iloc[i]) / 2
        if bar_mid == 0:
            break
        bar_range_pct = (bar_range / bar_mid) * 100

        # If bar range is less than half the explosive move, it's part of the base
        explosive_range_pct = float(df["bar_move_pct"].iloc[explosive_pos])
        if bar_range_pct < explosive_range_pct * 0.7:
            base_start_pos = i
        else:
            break

    # Must have at least 1 bar in the base
    if base_start_pos == base_end_pos and base_end_pos > 0:
        base_start_pos = base_end_pos - 1

    if base_start_pos < 0:
        return None

    return base_start_pos, base_end_pos


def _get_pre_move_direction(df: pd.DataFrame, base_start_pos: int) -> int:
    """Determine the price direction leading into the base zone."""
    lookback = min(5, base_start_pos)
    if lookback < 1:
        return 0

    pre_close = float(df["close"].iloc[base_start_pos - lookback])
    base_close = float(df["close"].iloc[base_start_pos])

    if base_close > pre_close:
        return 1  # Was rallying into base
    elif base_close < pre_close:
        return -1  # Was dropping into base
    return 0


def _check_zone_freshness(
    df: pd.DataFrame,
    explosive_pos: int,
    zone_low: float,
    zone_high: float,
    zone_type: str,
) -> tuple[bool, int]:
    """Check if a zone has been revisited since its creation.

    A fresh zone has never been tested - price hasn't returned to it.
    """
    test_count = 0
    fresh = True

    for i in range(explosive_pos + 1, len(df)):
        bar_low = df["low"].iloc[i]
        bar_high = df["high"].iloc[i]

        # Check if price entered the zone
        if bar_low <= zone_high and bar_high >= zone_low:
            test_count += 1
            fresh = False

    return fresh, test_count


def _calculate_zone_strength(
    move_size_pct: float,
    volume_confirmed: bool,
    fresh: bool,
    test_count: int,
    pattern: str,
    width_pct: float,
) -> int:
    """Calculate zone strength (1-10).

    Factors:
    - Move size: Bigger explosive move = stronger zone
    - Volume: Volume confirmation adds strength
    - Freshness: Untested zones are stronger
    - Pattern: Reversal patterns (DBR, RBD) stronger than continuation
    - Width: Tighter zones are stronger (more precise institutional orders)
    """
    score = 0.0

    # Move size (0-3)
    if move_size_pct >= 8:
        score += 3.0
    elif move_size_pct >= 5:
        score += 2.0
    elif move_size_pct >= 3:
        score += 1.5
    else:
        score += 1.0

    # Volume (0-2)
    if volume_confirmed:
        score += 2.0

    # Freshness (0-2)
    if fresh:
        score += 2.0
    elif test_count <= 1:
        score += 1.0
    # Tested 2+ times = less reliable, no points

    # Pattern (0-2)
    pattern_scores = {"DBR": 2.0, "RBD": 2.0, "RBR": 1.5, "DBD": 1.5}
    score += pattern_scores.get(pattern, 1.0)

    # Width (0-1): tighter is better
    if width_pct < 2:
        score += 1.0
    elif width_pct < 5:
        score += 0.5

    return max(1, min(10, round(score)))


def _deduplicate_zones(zones: list[Zone]) -> list[Zone]:
    """Remove overlapping zones, keeping the stronger one."""
    if len(zones) <= 1:
        return zones

    # Sort by price
    zones.sort(key=lambda z: z.price_low)
    result = [zones[0]]

    for zone in zones[1:]:
        prev = result[-1]
        # Check overlap
        overlap = min(prev.price_high, zone.price_high) - max(prev.price_low, zone.price_low)
        min_width = min(prev.width, zone.width)

        if min_width > 0 and overlap / min_width > 0.5:
            # Significant overlap - keep the stronger one
            if zone.strength > prev.strength:
                result[-1] = zone
        else:
            result.append(zone)

    return result


def summarize_zones(zones: list[Zone], current_price: float) -> dict:
    """Generate a summary of supply/demand analysis."""
    demand = [z for z in zones if z.zone_type == "demand"]
    supply = [z for z in zones if z.zone_type == "supply"]

    # Find nearest zones
    demand_below = [z for z in demand if z.price_high <= current_price]
    supply_above = [z for z in supply if z.price_low >= current_price]

    nearest_demand = max(demand_below, key=lambda z: z.price_high) if demand_below else None
    nearest_supply = min(supply_above, key=lambda z: z.price_low) if supply_above else None

    return {
        "current_price": round(current_price, 2),
        "total_zones": len(zones),
        "demand_zones": [z.to_dict() for z in sorted(demand, key=lambda x: -x.price_high)],
        "supply_zones": [z.to_dict() for z in sorted(supply, key=lambda x: x.price_low)],
        "nearest_demand": nearest_demand.to_dict() if nearest_demand else None,
        "nearest_supply": nearest_supply.to_dict() if nearest_supply else None,
        "fresh_zones": [z.to_dict() for z in zones if z.fresh],
    }
