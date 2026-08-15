#!/usr/bin/env python3
"""
Batch Generate Intelligence Reports for Multiple Tickers
=========================================================
Generates reports for 100+ tickers to create training data for embeddings fine-tuning.

Features:
- Parallel batch generation with configurable concurrency
- Progress tracking with status file
- Resume capability (skips already generated)
- Rate limiting to avoid API throttling
- Scheduled start time support

Usage:
    # Test with 1 report in 1 minute
    python scripts/batch_generate_reports.py --test --delay 60

    # Generate all reports immediately
    python scripts/batch_generate_reports.py --batch-size 5 --delay 30

    # Generate specific tickers
    python scripts/batch_generate_reports.py --tickers "AAPL,MSFT,GOOGL"

    # Schedule batch for specific time
    python scripts/batch_generate_reports.py --start-at "2026-08-14 22:00:00"

    # Resume from previous run
    python scripts/batch_generate_reports.py --resume
"""

import argparse
import concurrent.futures
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Directories
SCRIPTS_DIR = Path(__file__).parent
API_DIR = SCRIPTS_DIR.parent
REPORTS_DIR = API_DIR.parent / "reports"
EXPORTS_DIR = API_DIR / "exports"
STATUS_FILE = EXPORTS_DIR / "batch_generation_status.json"

# Comprehensive list of 200+ tickers for training data
ALL_TICKERS = [
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # Semiconductors
    "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC",
    "MRVL", "ADI", "NXPI", "ON", "MCHP", "SNPS", "CDNS", "TSM", "ASML",
    # Software & Cloud
    "CRM", "ORCL", "IBM", "NOW", "INTU", "ADBE", "SNOW", "DDOG", "MDB",
    "NET", "ZS", "CRWD", "PANW", "FTNT", "OKTA", "DOCU", "ZM", "PLTR",
    # Fintech & Payments
    "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "AXP",
    # Banks & Finance
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "USB", "PNC",
    "TFC", "BK", "STT", "COF", "CME", "ICE",
    # Insurance
    "AIG", "MET", "PRU", "ALL", "TRV", "CB",
    # Healthcare & Pharma
    "JNJ", "PFE", "ABBV", "MRK", "LLY", "BMY", "AMGN", "GILD", "BIIB",
    "REGN", "VRTX", "MRNA", "ZTS",
    # Medical Devices
    "DHR", "TMO", "SYK", "ISRG", "MDT", "BSX", "EW", "BDX", "IDXX", "A", "IQV",
    # Defense & Aerospace
    "LMT", "RTX", "BA", "NOC", "GD", "LHX", "HII",
    # Industrials
    "GE", "HON", "CAT", "DE", "MMM", "EMR", "ETN", "ROK", "CMI", "PH", "ITW", "AME",
    # Consumer
    "PG", "KO", "PEP", "COST", "WMT", "HD", "NKE", "MCD", "SBUX",
    # Retail & E-commerce
    "AMZN", "SHOP", "UBER", "ABNB", "DIS", "NFLX", "CHTR", "CMCSA",
    # Social & Media
    "SNAP", "PINS", "RBLX", "DKNG",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PSX", "MPC", "VLO",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED", "WEC", "ES", "AWK",
    # REITs
    "AMT", "CCI", "PLD", "EQIX", "PSA", "SPG", "O", "WELL", "DLR",
    "AVB", "EQR", "VTR", "ARE", "MAA", "UDR", "ESS", "CPT",
    # Telecom
    "T", "VZ", "TMUS",
    # International
    "SAP", "TM", "SONY", "NVO", "AZN", "SHEL", "BP", "RIO", "BHP",
    # Pipelines
    "KMI", "WMB",
    # Additional High-Profile
    "UNH", "ABT", "ACN", "SMCI", "AI", "PATH",
]

# Test tickers (subset for quick testing)
TEST_TICKERS = ["AAPL", "MSFT", "NVDA"]


def load_status() -> Dict:
    """Load generation status from file."""
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {
        "started_at": None,
        "completed_at": None,
        "total_tickers": 0,
        "completed": [],
        "failed": [],
        "in_progress": [],
        "pending": [],
    }


def save_status(status: Dict):
    """Save generation status to file."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2, default=str)


def get_existing_reports() -> set:
    """Get set of tickers that already have reports."""
    existing = set()
    if REPORTS_DIR.exists():
        for f in REPORTS_DIR.glob("*_Intelligence_Data_*.json"):
            # Extract ticker from filename like NVIDIA_CORP_Intelligence_Data_...
            name = f.stem.split("_Intelligence_Data_")[0]
            # Try to match to ticker (reverse lookup would be better)
            existing.add(name)
    return existing


def generate_single_report(ticker: str, timeout: int = 1800) -> Dict:
    """Generate report for a single ticker."""
    script_path = SCRIPTS_DIR / "generate_intelligence_report.py"

    # Use venv Python if available (check project root venv first, then apps/api venv)
    project_root = API_DIR.parent.parent  # Finance-Advanced-Research-Platform
    venv_python = project_root / "venv" / "bin" / "python3"
    if not venv_python.exists():
        venv_python = API_DIR / "venv" / "bin" / "python3"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    result = {
        "ticker": ticker,
        "status": "pending",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "output_files": {},
        "error": None,
    }

    try:
        logger.info(f"Starting report generation for {ticker}")

        proc = subprocess.run(
            [python_cmd, str(script_path), "--ticker", ticker],
            cwd=str(API_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if proc.returncode == 0:
            result["status"] = "completed"
            # Try to parse output files from stdout
            try:
                output_files = json.loads(proc.stdout.strip().split("\n")[-1])
                result["output_files"] = output_files
            except:
                pass
        else:
            result["status"] = "failed"
            result["error"] = proc.stderr[:500] if proc.stderr else "Unknown error"

    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["error"] = f"Timeout after {timeout}s"
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)

    result["completed_at"] = datetime.now().isoformat()
    return result


def run_batch(
    tickers: List[str],
    batch_size: int = 3,
    delay_between_batches: int = 30,
    resume: bool = True,
) -> Dict:
    """Run batch generation with parallel execution."""
    status = load_status() if resume else {
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total_tickers": len(tickers),
        "completed": [],
        "failed": [],
        "in_progress": [],
        "pending": list(tickers),
    }

    if not status.get("started_at"):
        status["started_at"] = datetime.now().isoformat()

    # Filter out already completed tickers
    completed_set = set(status.get("completed", []))
    remaining = [t for t in tickers if t not in completed_set]

    logger.info(f"Starting batch generation: {len(remaining)} tickers remaining")
    logger.info(f"Batch size: {batch_size}, Delay: {delay_between_batches}s")

    # Process in batches
    for i in range(0, len(remaining), batch_size):
        batch = remaining[i:i + batch_size]
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing batch {i//batch_size + 1}: {batch}")
        logger.info(f"{'='*60}")

        # Update status
        status["in_progress"] = batch
        status["pending"] = remaining[i + batch_size:]
        save_status(status)

        # Run batch in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_ticker = {
                executor.submit(generate_single_report, ticker): ticker
                for ticker in batch
            }

            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    if result["status"] == "completed":
                        status["completed"].append(ticker)
                        logger.info(f"✓ {ticker} completed")
                    else:
                        status["failed"].append(ticker)
                        logger.error(f"✗ {ticker} failed: {result.get('error', 'Unknown')}")
                except Exception as e:
                    status["failed"].append(ticker)
                    logger.error(f"✗ {ticker} exception: {e}")

        # Update status
        status["in_progress"] = []
        save_status(status)

        # Delay between batches (rate limiting)
        if i + batch_size < len(remaining):
            logger.info(f"Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)

    status["completed_at"] = datetime.now().isoformat()
    save_status(status)

    return status


def schedule_start(start_time: datetime):
    """Wait until start time."""
    now = datetime.now()
    if start_time > now:
        wait_seconds = (start_time - now).total_seconds()
        logger.info(f"Scheduled start at {start_time}")
        logger.info(f"Waiting {wait_seconds:.0f} seconds...")
        time.sleep(wait_seconds)


def run_triplet_extraction():
    """Run triplet extraction after report generation."""
    logger.info("\n" + "="*60)
    logger.info("Running triplet extraction...")
    logger.info("="*60)

    # Use venv Python
    project_root = API_DIR.parent.parent
    venv_python = project_root / "venv" / "bin" / "python3"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    try:
        result = subprocess.run(
            [
                python_cmd, "-m", "app.scripts.extract_embedding_pairs",
                "--output", str(EXPORTS_DIR / "embedding_triplets.jsonl"),
                "--add-cross-entity",
            ],
            cwd=str(API_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            logger.info("Triplet extraction completed successfully")
            # Count triplets
            triplet_file = EXPORTS_DIR / "embedding_triplets.jsonl"
            if triplet_file.exists():
                with open(triplet_file) as f:
                    count = sum(1 for _ in f)
                logger.info(f"Total triplets extracted: {count:,}")
        else:
            logger.error(f"Triplet extraction failed: {result.stderr}")

    except Exception as e:
        logger.error(f"Triplet extraction error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Batch Generate Intelligence Reports")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: generate 1 report only")
    parser.add_argument("--delay", type=int, default=0,
                        help="Delay in seconds before starting (for scheduling)")
    parser.add_argument("--start-at", type=str, default=None,
                        help="Start at specific time (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated list of tickers to generate")
    parser.add_argument("--batch-size", type=int, default=3,
                        help="Number of parallel reports per batch")
    parser.add_argument("--batch-delay", type=int, default=30,
                        help="Delay between batches in seconds")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from previous run (skip completed)")
    parser.add_argument("--extract-triplets", action="store_true", default=True,
                        help="Run triplet extraction after generation")
    parser.add_argument("--list-tickers", action="store_true",
                        help="List all available tickers and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show current status and exit")
    args = parser.parse_args()

    # List tickers and exit
    if args.list_tickers:
        print(f"Available tickers ({len(ALL_TICKERS)}):")
        for i, ticker in enumerate(ALL_TICKERS):
            print(f"  {i+1:3d}. {ticker}")
        return 0

    # Show status and exit
    if args.status:
        status = load_status()
        print(json.dumps(status, indent=2))
        return 0

    # Determine tickers to generate
    if args.test:
        tickers = TEST_TICKERS[:1]  # Just one for testing
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = ALL_TICKERS

    logger.info(f"Batch Report Generation")
    logger.info(f"Tickers to process: {len(tickers)}")

    # Handle scheduling
    if args.delay > 0:
        logger.info(f"Waiting {args.delay} seconds before starting...")
        time.sleep(args.delay)

    if args.start_at:
        start_time = datetime.strptime(args.start_at, "%Y-%m-%d %H:%M:%S")
        schedule_start(start_time)

    # Run batch generation
    try:
        status = run_batch(
            tickers=tickers,
            batch_size=args.batch_size,
            delay_between_batches=args.batch_delay,
            resume=args.resume,
        )

        # Summary
        logger.info("\n" + "="*60)
        logger.info("BATCH GENERATION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total: {status['total_tickers']}")
        logger.info(f"Completed: {len(status['completed'])}")
        logger.info(f"Failed: {len(status['failed'])}")
        if status['failed']:
            logger.info(f"Failed tickers: {status['failed']}")

        # Run triplet extraction
        if args.extract_triplets and len(status['completed']) > 0:
            run_triplet_extraction()

        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Progress saved.")
        return 1
    except Exception as e:
        logger.error(f"Batch generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
