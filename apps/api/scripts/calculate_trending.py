#!/usr/bin/env python3
"""
Standalone script to calculate trending scores for all stores.

This script can be run as a cron job to keep trending scores up-to-date.

Usage:
    python scripts/calculate_trending.py [--limit N] [--verbose]

Options:
    --limit N       Process only N stores (useful for testing)
    --verbose       Enable detailed logging
    --all           Process all stores including inactive ones
    --min-score M   Only show score changes >= M points
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.trending_service import TrendingService
from app.config import settings


# Configure logging
def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("trending_calculation.log"),
        ],
    )


def print_banner() -> None:
    """Print script banner."""
    print("=" * 70)
    print("  E-Commerce Intelligence SaaS - Trending Score Calculator")
    print("=" * 70)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()


def print_progress_bar(
    iteration: int, total: int, prefix: str = "", suffix: str = "", length: int = 50
) -> None:
    """
    Print a progress bar to console.

    Args:
        iteration: Current iteration
        total: Total iterations
        prefix: Prefix string
        suffix: Suffix string
        length: Character length of bar
    """
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_length = int(length * iteration // total)
    bar = "█" * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end="", flush=True)
    if iteration == total:
        print()


async def calculate_scores(
    limit: Optional[int] = None,
    only_active: bool = True,
    min_score_change: float = 5.0,
    verbose: bool = False,
) -> None:
    """
    Calculate trending scores for all stores.

    Args:
        limit: Optional limit on number of stores
        only_active: Only process active stores
        min_score_change: Minimum score change to display
        verbose: Enable verbose output
    """
    logger = logging.getLogger(__name__)

    try:
        print("\n🚀 Starting trending score calculation...")
        print(f"   Mode: {'Active stores only' if only_active else 'All stores'}")
        if limit:
            print(f"   Limit: {limit} stores")
        print()

        # Run batch calculation
        print("📊 Calculating scores...")
        stats = await TrendingService.batch_calculate_trending_scores(
            limit=limit, only_active=only_active
        )

        # Print progress summary
        print("\n" + "=" * 70)
        print("  CALCULATION COMPLETE")
        print("=" * 70)
        print(f"  Total stores processed: {stats['total']}")
        print(f"  Successfully updated:   {stats['updated']}")
        print(f"  Errors encountered:     {stats['errors']}")
        print("=" * 70)

        # Print significant score changes
        significant_changes = [
            change
            for change in stats["score_changes"]
            if abs(change["change"]) >= min_score_change
        ]

        if significant_changes:
            print(f"\n📈 Significant Score Changes (>= {min_score_change} points):")
            print("-" * 70)

            # Sort by absolute change
            significant_changes.sort(key=lambda x: abs(x["change"]), reverse=True)

            for i, change in enumerate(significant_changes[:20], 1):  # Show top 20
                direction = "📈" if change["change"] > 0 else "📉"
                print(
                    f"{i:2d}. {direction} {change['domain']:<40} "
                    f"{change['old_score']:5.1f} → {change['new_score']:5.1f} "
                    f"({change['change']:+6.1f})"
                )

            if len(significant_changes) > 20:
                print(f"\n   ... and {len(significant_changes) - 20} more changes")
        else:
            print("\n✅ No significant score changes detected")

        # Print success rate
        if stats["total"] > 0:
            success_rate = (stats["updated"] / stats["total"]) * 100
            print(f"\n✨ Success rate: {success_rate:.1f}%")

        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Calculation interrupted by user")
        logger.warning("Calculation interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n❌ Error during calculation: {str(e)}")
        logger.error(f"Calculation failed: {str(e)}", exc_info=True)
        sys.exit(1)


async def show_top_trending(limit: int = 10) -> None:
    """
    Show top trending stores.

    Args:
        limit: Number of stores to show
    """
    from app.database import AsyncSessionLocal

    print(f"\n🔥 Top {limit} Trending Stores:")
    print("-" * 70)

    try:
        async with AsyncSessionLocal() as db:
            stores = await TrendingService.get_trending_stores_by_score(
                db=db, min_score=0.0, limit=limit
            )

            if not stores:
                print("   No stores found")
                return

            for i, store in enumerate(stores, 1):
                print(
                    f"{i:2d}. {store.domain:<40} "
                    f"Score: {store.trending_score:5.1f} | "
                    f"Products: {store.product_count:4d} | "
                    f"Category: {store.category.value}"
                )

    except Exception as e:
        print(f"   Error fetching trending stores: {str(e)}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate trending scores for e-commerce stores",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate for all active stores
  python scripts/calculate_trending.py

  # Calculate for first 100 stores (testing)
  python scripts/calculate_trending.py --limit 100

  # Calculate for all stores with verbose logging
  python scripts/calculate_trending.py --all --verbose

  # Show only major changes
  python scripts/calculate_trending.py --min-score 10
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only N stores (useful for testing)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable detailed logging"
    )

    parser.add_argument(
        "--all", action="store_true", help="Process all stores including inactive ones"
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=5.0,
        metavar="M",
        help="Only show score changes >= M points (default: 5.0)",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=0,
        metavar="N",
        help="Show top N trending stores after calculation",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate scores but don't save to database",
    )

    return parser.parse_args()


async def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    # Print banner
    print_banner()

    # Validate environment
    if not settings.database_url:
        print("❌ Error: DATABASE_URL not configured")
        print("   Please check your .env file")
        sys.exit(1)

    if not settings.redis_url:
        print("⚠️  Warning: REDIS_URL not configured")
        print("   Some features may not work correctly")

    # Run calculation
    await calculate_scores(
        limit=args.limit,
        only_active=not args.all,
        min_score_change=args.min_score,
        verbose=args.verbose,
    )

    # Show top trending stores if requested
    if args.top > 0:
        await show_top_trending(limit=args.top)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
