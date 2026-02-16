"""Gap Analyzer - Detect and classify price gaps.

Identifies gaps between consecutive bars, classifies them by type,
tracks fill status, and ranks by significance.

Component 2 per PRD.md specification.
No LLM cost - pure Python/math.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("gap_analyzer")


@dataclass
class Gap:
    """Represents a detected price gap."""

    date: datetime
    direction: str  # "up" or "down"
    gap_low: float  # Lower bound of gap
    gap_high: float  # Upper bound of gap
    size: float  # Absolute gap size
    size_pct: float  # Gap size as percentage
    gap_type: str  # "common", "breakaway", "runaway", "exhaustion"
    filled: bool
    fill_pct: float  # 0.0 - 1.0, how much has been filled
    fill_date: Optional[datetime]
    bars_since: int  # Bars since gap formed
    severity: int  # 1-10 significance score

    @property
    def is_unfilled(self) -> bool:
        return not self.filled

    @property
    def midpoint(self) -> float:
        return (self.gap_low + self.gap_high) / 2

    @property
    def days_ago(self) -> Optional[int]:
        if self.date is None:
            return None
        try:
            delta = datetime.now() - self.date
            return delta.days
        except Exception:
            return None

    def to_dict(self) -> dict:
        days = self.days_ago
        return {
            "date": self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            "direction": self.direction,
            "gap_low": round(self.gap_low, 2),
            "gap_high": round(self.gap_high, 2),
            "range": f"${self.gap_low:.2f} - ${self.gap_high:.2f}",
            "size": round(self.size, 2),
            "size_pct": round(self.size_pct, 2),
            "gap_type": self.gap_type,
            "filled": self.filled,
            "fill_pct": round(self.fill_pct, 2),
            "fill_date": self.fill_date.isoformat() if self.fill_date else None,
            "bars_since": self.bars_since,
            "days_ago": days,
            "severity": self.severity,
        }


def detect_gaps(
    df: pd.DataFrame,
    min_gap_pct: float = 0.5,
    include_body_gaps: bool = True,
) -> list[Gap]:
    """Detect all price gaps in the data.

    Two detection modes:
    - Wick gaps: current bar's low > previous bar's high (classic true gap)
    - Body gaps: current open vs previous close (more sensitive, catches
      gaps where wicks overlap but bodies don't)

    Args:
        df: DataFrame with columns [time, open, high, low, close, volume].
        min_gap_pct: Minimum gap size as percentage to include (default 0.5%).
        include_body_gaps: Also detect open-vs-close gaps (default True).

    Returns:
        List of detected gaps, sorted by date.
    """
    if len(df) < 2:
        return []

    gaps = []
    seen_dates: set[str] = set()  # Avoid duplicate gaps on same bar

    for i in range(1, len(df)):
        prev_high = df["high"].iloc[i - 1]
        prev_low = df["low"].iloc[i - 1]
        prev_close = df["close"].iloc[i - 1]
        curr_high = df["high"].iloc[i]
        curr_low = df["low"].iloc[i]
        curr_open = df["open"].iloc[i]
        curr_time = df["time"].iloc[i]
        date_key = str(curr_time)

        # --- Wick gaps (classic: no overlap between bars) ---

        # Gap up: current low > previous high
        if curr_low > prev_high:
            size = curr_low - prev_high
            size_pct = (size / prev_close) * 100
            if size_pct >= min_gap_pct:
                gap = _build_gap(df, i, prev_high, curr_low, size, size_pct, "up")
                gaps.append(gap)
                seen_dates.add(date_key)

        # Gap down: current high < previous low
        elif curr_high < prev_low:
            size = prev_low - curr_high
            size_pct = (size / prev_close) * 100
            if size_pct >= min_gap_pct:
                gap = _build_gap(df, i, curr_high, prev_low, size, size_pct, "down")
                gaps.append(gap)
                seen_dates.add(date_key)

        # --- Body gaps (open vs prev close) ---
        elif include_body_gaps and date_key not in seen_dates:
            body_gap = curr_open - prev_close
            body_gap_pct = abs(body_gap / prev_close) * 100

            if body_gap_pct >= min_gap_pct:
                if body_gap > 0:
                    # Body gap up
                    gap = _build_gap(
                        df, i, prev_close, curr_open,
                        abs(body_gap), body_gap_pct, "up",
                    )
                    gaps.append(gap)
                else:
                    # Body gap down
                    gap = _build_gap(
                        df, i, curr_open, prev_close,
                        abs(body_gap), body_gap_pct, "down",
                    )
                    gaps.append(gap)

    logger.info(
        f"Detected {len(gaps)} gaps (min {min_gap_pct}%): "
        f"{sum(1 for g in gaps if g.direction == 'up')} up, "
        f"{sum(1 for g in gaps if g.direction == 'down')} down, "
        f"{sum(1 for g in gaps if g.is_unfilled)} unfilled"
    )

    return gaps


def _build_gap(
    df: pd.DataFrame,
    bar_idx: int,
    gap_low: float,
    gap_high: float,
    size: float,
    size_pct: float,
    direction: str,
) -> Gap:
    """Construct a Gap object with fill check, classification, and severity."""
    curr_time = df["time"].iloc[bar_idx]

    filled, fill_pct, fill_date = _check_fill(
        df, bar_idx, gap_low, gap_high, direction
    )
    gap_type = _classify_gap(df, bar_idx, size_pct, direction)
    bars_since = len(df) - 1 - bar_idx
    severity = _calculate_severity(
        size_pct, gap_type, filled, bars_since, df, bar_idx
    )

    return Gap(
        date=pd.Timestamp(curr_time).to_pydatetime(),
        direction=direction,
        gap_low=gap_low,
        gap_high=gap_high,
        size=size,
        size_pct=size_pct,
        gap_type=gap_type,
        filled=filled,
        fill_pct=fill_pct,
        fill_date=fill_date,
        bars_since=bars_since,
        severity=severity,
    )


def _check_fill(
    df: pd.DataFrame,
    gap_bar_idx: int,
    gap_low: float,
    gap_high: float,
    direction: str,
) -> tuple[bool, float, Optional[datetime]]:
    """Check if a gap has been filled by subsequent price action.

    A gap up is filled when price trades down to gap_low.
    A gap down is filled when price trades up to gap_high.
    """
    max_fill = 0.0
    fill_date = None
    gap_size = gap_high - gap_low

    if gap_size == 0:
        return True, 1.0, None

    for j in range(gap_bar_idx + 1, len(df)):
        if direction == "up":
            # Gap up fills when price drops into the gap
            if df["low"].iloc[j] <= gap_low:
                return True, 1.0, pd.Timestamp(df["time"].iloc[j]).to_pydatetime()
            # Partial fill
            penetration = gap_high - df["low"].iloc[j]
            if penetration > 0:
                fill = penetration / gap_size
                if fill > max_fill:
                    max_fill = fill
                    fill_date = pd.Timestamp(df["time"].iloc[j]).to_pydatetime()
        else:
            # Gap down fills when price rises into the gap
            if df["high"].iloc[j] >= gap_high:
                return True, 1.0, pd.Timestamp(df["time"].iloc[j]).to_pydatetime()
            penetration = df["high"].iloc[j] - gap_low
            if penetration > 0:
                fill = penetration / gap_size
                if fill > max_fill:
                    max_fill = fill
                    fill_date = pd.Timestamp(df["time"].iloc[j]).to_pydatetime()

    return max_fill >= 1.0, min(max_fill, 1.0), fill_date


def _classify_gap(
    df: pd.DataFrame,
    gap_bar_idx: int,
    size_pct: float,
    direction: str,
) -> str:
    """Classify gap type based on context.

    Types:
    - common: Small gap in a trading range, often filled quickly
    - breakaway: Gap out of a consolidation/pattern, high volume
    - runaway (continuation): Gap in the middle of a trend
    - exhaustion: Gap near end of a trend, often reversed
    """
    lookback = min(20, gap_bar_idx)
    if lookback < 5:
        return "common"

    prev_data = df.iloc[gap_bar_idx - lookback : gap_bar_idx]

    # Check for volume spike (if volume available)
    has_volume = "volume" in df.columns and not df["volume"].isna().all()
    volume_spike = False
    if has_volume:
        avg_vol = prev_data["volume"].mean()
        gap_vol = df["volume"].iloc[gap_bar_idx]
        if avg_vol > 0:
            volume_spike = gap_vol > avg_vol * 1.5

    # Calculate prior trend
    price_change = (prev_data["close"].iloc[-1] - prev_data["close"].iloc[0]) / prev_data["close"].iloc[0] * 100

    # Check if price was in a range (consolidation)
    price_range = (prev_data["high"].max() - prev_data["low"].min()) / prev_data["close"].mean() * 100
    in_consolidation = price_range < 15  # Less than 15% range = consolidation

    # Check if trend is extended
    bars_remaining = len(df) - gap_bar_idx - 1
    trend_extended = abs(price_change) > 20

    # Classification logic
    if in_consolidation and volume_spike:
        return "breakaway"
    elif trend_extended and not volume_spike:
        return "exhaustion"
    elif abs(price_change) > 10 and volume_spike:
        return "runaway"
    elif size_pct < 3:
        return "common"
    else:
        # Default classification based on gap characteristics
        if volume_spike and abs(price_change) > 5:
            return "breakaway"
        return "common"


def _calculate_severity(
    size_pct: float,
    gap_type: str,
    filled: bool,
    bars_since: int,
    df: pd.DataFrame,
    gap_bar_idx: int,
) -> int:
    """Calculate gap severity score (1-10).

    Factors:
    - Gap size (larger = more significant)
    - Gap type (breakaway > runaway > exhaustion > common)
    - Fill status (unfilled = more significant)
    - Recency (newer = more significant)
    - Volume context
    """
    score = 0.0

    # Size contribution (0-3 points)
    if size_pct >= 10:
        score += 3.0
    elif size_pct >= 5:
        score += 2.0
    elif size_pct >= 3:
        score += 1.5
    else:
        score += 1.0

    # Type contribution (0-3 points)
    type_scores = {
        "breakaway": 3.0,
        "runaway": 2.5,
        "exhaustion": 1.5,
        "common": 1.0,
    }
    score += type_scores.get(gap_type, 1.0)

    # Fill status (0-2 points)
    if not filled:
        score += 2.0
    else:
        score += 0.5

    # Recency (0-2 points)
    total_bars = len(df)
    if total_bars > 0:
        recency_ratio = 1.0 - (bars_since / total_bars)
        score += recency_ratio * 2.0

    return max(1, min(10, round(score)))


def prioritize_gaps(gaps: list[Gap]) -> list[Gap]:
    """Sort gaps by significance (highest severity first, then unfilled first)."""
    return sorted(gaps, key=lambda g: (-int(g.is_unfilled), -g.severity, -g.size_pct))


def get_unfilled_gaps(gaps: list[Gap]) -> list[Gap]:
    """Filter to only unfilled gaps."""
    return [g for g in gaps if g.is_unfilled]


def summarize_gaps(gaps: list[Gap]) -> dict:
    """Generate a summary of gap analysis results."""
    if not gaps:
        return {
            "total": 0,
            "unfilled": 0,
            "gaps": [],
            "message": "No gaps detected with current threshold.",
            "explanation": (
                "Gaps form when price opens significantly above or below "
                "the previous close. Unfilled gaps often act as magnets — "
                "price tends to return to fill them."
            ),
        }

    unfilled = get_unfilled_gaps(gaps)
    prioritized = prioritize_gaps(gaps)

    type_counts = {}
    for g in gaps:
        type_counts[g.gap_type] = type_counts.get(g.gap_type, 0) + 1

    return {
        "total": len(gaps),
        "unfilled": len(unfilled),
        "by_type": type_counts,
        "by_direction": {
            "up": sum(1 for g in gaps if g.direction == "up"),
            "down": sum(1 for g in gaps if g.direction == "down"),
        },
        "largest_unfilled": prioritized[0].to_dict() if unfilled else None,
        "gaps": [g.to_dict() for g in prioritized],
        "explanation": (
            "Gaps form when price opens significantly above or below "
            "the previous close. Unfilled gaps often act as magnets — "
            "price tends to return to fill them. "
            "Breakaway gaps signal new trends. "
            "Common gaps usually fill quickly."
        ),
    }
