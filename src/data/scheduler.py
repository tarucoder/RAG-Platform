import sys
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add project root to the import path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from src.infrastructure.logger import logger
from src.data.ingest_runner import run_ingestion
from src.data.vector_store import VectorStore

def run_scheduled_indexing():
    """Scheduled task that checks for website updates and updates the vector database."""
    logger.info("Executing scheduled ingestion check...")
    try:
        # Step 1: Run crawl and parse only modified files
        parsed_docs = run_ingestion(force=False, only_modified=True)
        
        # Step 2: Update Vector Store
        store = VectorStore.get_instance()
        chunks_added = 0
        chunks_purged = 0
        schemes_updated = len(parsed_docs)
        
        for doc in parsed_docs:
            url = doc["url"]
            scheme_name = doc["scheme_name"]
            title = doc["title"]
            chunks = doc["chunks"]
            
            logger.info(f"Updating vector index for modified scheme: {scheme_name} ({url})")
            
            # Count existing chunks to report in purged log
            try:
                existing = store.collection.get(where={"url": url})
                if existing and "ids" in existing:
                    chunks_purged += len(existing["ids"])
            except Exception as e:
                logger.debug(f"Failed to query existing chunks for count: {e}")
            
            # Update collection (add_document_chunks handles purging internally)
            store.add_document_chunks(url, scheme_name, title, chunks)
            chunks_added += len(chunks)
            
        logger.info(
            f"Scheduled ingestion complete. "
            f"Schemes updated: {schemes_updated}. "
            f"Chunks added/updated: {chunks_added}. "
            f"Old chunks purged: {chunks_purged}."
        )
    except Exception as e:
        logger.error(f"Scheduled ingestion task failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Daily Ingestion Scheduler Component")
    parser.add_argument(
        "--run-once", 
        action="store_true", 
        help="Run the ingestion checks immediately once and exit."
    )
    parser.add_argument(
        "--test-interval", 
        type=int, 
        metavar="MINUTES",
        help="Run scheduler on a recurring minute interval for local testing."
    )
    args = parser.parse_args()

    if args.run_once:
        logger.info("Running ingestion once immediately...")
        run_scheduled_indexing()
        sys.exit(0)

    scheduler = BlockingScheduler()
    tz = ZoneInfo("Asia/Kolkata")

    if args.test_interval:
        minutes = args.test_interval
        logger.info(f"Starting test scheduler. Running every {minutes} minute(s).")
        # Run immediately on startup, then at intervals
        scheduler.add_job(
            run_scheduled_indexing, 
            "interval", 
            minutes=minutes, 
            next_run_time=datetime.now(tz=tz)
        )
    else:
        # Standard Daily Ingestion Job at 10:00 AM IST
        logger.info("Starting daily ingestion scheduler. Scheduled for 10:00 AM IST daily.")
        scheduler.add_job(
            run_scheduled_indexing, 
            "cron", 
            hour=10, 
            minute=0, 
            timezone=tz
        )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    main()
