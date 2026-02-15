"""CLI entry point for the Trading Analyzer.

Usage:
    python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv
    python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --tier standard --format html
    python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --output data/reports/WHR_report.md

Options:
    --symbol        Stock ticker symbol (required)
    --csv           Path to TradingView CSV file (required)
    --tier          Analysis tier: lite, standard, premium (default: standard)
    --format        Output format: markdown, json, html (default: markdown)
    --output        Save report to file (optional)
    --min-gap-pct   Minimum gap size percentage (default: 2.0)
    --news-days     Days to look back for news (default: 7)
    --budget        Budget override in USD (optional)
    --quiet         Suppress progress output
"""

import argparse
import sys
from pathlib import Path

from src.orchestrator import TradingAnalysisOrchestrator


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        prog="trading-analyzer",
        description="Multi-asset trading analysis with AI-powered insights.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --symbol WHR --csv data/samples/NYSE_WHR__1M.csv
  %(prog)s --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --tier lite
  %(prog)s --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --format html -o report.html
  %(prog)s --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --tier standard --format json
        """,
    )
    parser.add_argument(
        "--symbol", required=True, help="Stock ticker symbol (e.g., WHR)"
    )
    parser.add_argument(
        "--csv", required=True, help="Path to TradingView CSV file"
    )
    parser.add_argument(
        "--tier",
        default="standard",
        choices=["lite", "standard", "premium"],
        help="Analysis tier (default: standard)",
    )
    parser.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "json", "html"],
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output", "-o", default=None, help="Save report to file path"
    )
    parser.add_argument(
        "--min-gap-pct",
        type=float,
        default=2.0,
        help="Minimum gap size %% (default: 2.0)",
    )
    parser.add_argument(
        "--news-days",
        type=int,
        default=7,
        help="Days to look back for news (default: 7)",
    )
    parser.add_argument(
        "--budget", type=float, default=None, help="Budget override in USD"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress progress output"
    )

    return parser.parse_args()


def main() -> int:
    """Run the CLI analysis pipeline.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = parse_args()

    # Validate CSV exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {args.csv}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Trading Analyzer")
        print(f"  Symbol: {args.symbol}")
        print(f"  CSV:    {args.csv}")
        print(f"  Tier:   {args.tier}")
        print(f"  Format: {args.format}")
        print()

    try:
        orchestrator = TradingAnalysisOrchestrator(
            tier=args.tier,
            budget=args.budget,
        )

        if not args.quiet:
            print("Running analysis pipeline...")

        result = orchestrator.analyze(
            symbol=args.symbol,
            csv_file=str(csv_path),
            min_gap_pct=args.min_gap_pct,
            news_lookback_days=args.news_days,
        )

        report = orchestrator.generate_report(
            result=result,
            format=args.format,
            output_path=args.output,
        )

        if args.output:
            if not args.quiet:
                print(f"\nReport saved to: {args.output}")
        else:
            print(report)

        # Print cost summary
        if not args.quiet:
            cs = result.get("cost_summary", {})
            total = cs.get("total_cost", 0)
            budget = cs.get("budget", 0)
            calls = cs.get("total_calls", 0)
            time_ms = cs.get("execution_time_ms", 0)
            errors = result.get("errors", [])

            print(f"\n--- Cost Summary ---")
            print(f"  Total: ${total:.4f} / ${budget:.2f} budget")
            print(f"  Calls: {calls}")
            print(f"  Time:  {time_ms}ms")
            if errors:
                print(f"  Warnings: {len(errors)}")
                for e in errors:
                    print(f"    - {e}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
