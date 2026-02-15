"""File-based analysis result cache.

Caches analysis results by symbol + tier + date to avoid redundant
API calls. Each result is stored as a JSON file in data/cache/.

Cache key format: {SYMBOL}_{tier}_{YYYY-MM-DD}.json
TTL: 6 hours (configurable).
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.utils.logger import get_logger

logger = get_logger("cache")


class AnalysisCache:
    """File-based cache for analysis results.

    Args:
        cache_dir: Directory for cache files.
        ttl_hours: Time-to-live in hours. Cached results older than
                   this are treated as expired.
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        ttl_hours: int = 6,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours

    def _cache_key(self, symbol: str, tier: str) -> str:
        """Build cache key: SYMBOL_tier_YYYY-MM-DD."""
        date = datetime.now().strftime("%Y-%m-%d")
        return f"{symbol.upper()}_{tier.lower()}_{date}"

    def _cache_path(self, symbol: str, tier: str) -> Path:
        key = self._cache_key(symbol, tier)
        return self.cache_dir / f"{key}.json"

    # ── Public API ────────────────────────────────────────────

    def get(self, symbol: str, tier: str) -> Optional[dict]:
        """Return cached result or None if miss/expired.

        On a hit, injects ``cached``, ``cache_time``, and
        ``cache_age_hours`` into the returned dict.
        """
        path = self._cache_path(symbol, tier)

        if not path.exists():
            logger.info(f"Cache MISS: {symbol.upper()} {tier}")
            return None

        mtime = path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600

        if age_hours > self.ttl_hours:
            logger.info(
                f"Cache expired: {symbol.upper()} {tier} "
                f"(age: {age_hours:.1f}h > {self.ttl_hours}h)"
            )
            path.unlink(missing_ok=True)
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Cache read error for {path.name}: {e}")
            path.unlink(missing_ok=True)
            return None

        cache_time = datetime.fromtimestamp(mtime).isoformat()
        data["cached"] = True
        data["cache_time"] = cache_time
        data["cache_age_hours"] = round(age_hours, 1)

        logger.info(
            f"Cache HIT: {symbol.upper()} {tier} (age: {age_hours:.1f}h)"
        )
        return data

    def set(self, symbol: str, tier: str, result: dict) -> None:
        """Store an analysis result in the cache."""
        path = self._cache_path(symbol, tier)

        # Shallow copy so we don't mutate the caller's dict
        to_store = dict(result)
        to_store["cached"] = False
        to_store["cache_time"] = datetime.now().isoformat()

        try:
            path.write_text(
                json.dumps(to_store, indent=2, default=str),
                encoding="utf-8",
            )
            logger.info(f"Cache SET: {symbol.upper()} {tier} → {path.name}")
        except OSError as e:
            logger.warning(f"Cache write error: {e}")

    def clear(self, symbol: Optional[str] = None) -> int:
        """Delete cached files. If *symbol* is given, only that symbol."""
        pattern = f"{symbol.upper()}_*.json" if symbol else "*.json"
        files = list(self.cache_dir.glob(pattern))
        for f in files:
            f.unlink(missing_ok=True)
        logger.info(f"Cache cleared: {len(files)} file(s)")
        return len(files)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        files = list(self.cache_dir.glob("*.json"))
        total_bytes = sum(f.stat().st_size for f in files)

        # Count per-symbol
        symbols: dict[str, int] = {}
        for f in files:
            sym = f.stem.split("_")[0]
            symbols[sym] = symbols.get(sym, 0) + 1

        return {
            "total_cached": len(files),
            "total_size_mb": round(total_bytes / (1024 * 1024), 3),
            "symbols": symbols,
            "cache_dir": str(self.cache_dir),
            "ttl_hours": self.ttl_hours,
        }
