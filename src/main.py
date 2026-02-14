"""Trading Analyzer - CLI entry point.

Multi-asset trading analysis with AI orchestration using Claude models.
Uses Evidence Scorecard + Checklist Method for thesis validation.
"""

import argparse
import sys
from pathlib import Path

from src.orchestrator import Orchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trading Analyzer - AI-powered multi-asset trading analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze AAPL --timeframe 1d
  %(prog)s analyze BTCUSD --asset-class crypto
  %(prog)s analyze EURUSD --asset-class forex --output json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a trading instrument")
    analyze_parser.add_argument("symbol", type=str, help="Ticker symbol to analyze")
    analyze_parser.add_argument(
        "--asset-class",
        choices=["equities", "options", "futures", "forex", "crypto"],
        default="equities",
        help="Asset class (default: equities)",
    )
    analyze_parser.add_argument(
        "--timeframe",
        choices=["1d", "4h", "1h", "15m"],
        default="1d",
        help="Analysis timeframe (default: 1d)",
    )
    analyze_parser.add_argument(
        "--thesis",
        type=str,
        default=None,
        help="Trading thesis to validate (e.g., 'bullish breakout above 150')",
    )
    analyze_parser.add_argument(
        "--output",
        choices=["markdown", "json", "html"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    analyze_parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to config file",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.command:
        print("Error: No command specified. Use --help for usage information.")
        return 1

    if args.command == "analyze":
        orchestrator = Orchestrator(config_path=args.config)
        result = orchestrator.run(
            symbol=args.symbol,
            asset_class=args.asset_class,
            timeframe=args.timeframe,
            thesis=args.thesis,
            output_format=args.output,
        )
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
