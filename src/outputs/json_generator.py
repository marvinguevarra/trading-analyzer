"""JSON report generator for trading analysis results.

Exports the analysis result as clean, structured JSON.
Handles numpy type serialization and optional pretty-printing.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class JSONGenerator:
    """Generate JSON reports from analysis results.

    Args:
        result: Complete analysis result dict from TradingAnalysisOrchestrator.
    """

    def __init__(self, result: dict):
        self.result = result

    def generate(self, pretty: bool = True) -> str:
        """Generate JSON report string.

        Args:
            pretty: If True, indent with 2 spaces. If False, compact.

        Returns:
            JSON string.
        """
        output = {
            **self.result,
            "_report_metadata": {
                "format": "json",
                "generated_at": datetime.now().isoformat(),
                "generator": "trading-analyzer",
                "version": "0.1.0",
            },
        }
        indent = 2 if pretty else None
        return json.dumps(output, indent=indent, default=_json_serializer)

    def save(self, path: str, pretty: bool = True) -> str:
        """Generate and save JSON report to file.

        Args:
            path: Output file path.
            pretty: If True, indent with 2 spaces.

        Returns:
            The path the file was saved to.
        """
        content = self.generate(pretty=pretty)
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)


def _json_serializer(obj):
    """Custom JSON serializer for types not handled by default."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "__float__"):
        return float(obj)
    if hasattr(obj, "__int__"):
        return int(obj)
    return str(obj)


def generate_json(result: dict, pretty: bool = True) -> str:
    """Convenience function to generate a JSON report.

    Args:
        result: Complete analysis result dict.
        pretty: If True, indent with 2 spaces.

    Returns:
        JSON report string.
    """
    return JSONGenerator(result).generate(pretty=pretty)
