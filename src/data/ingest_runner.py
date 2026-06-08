import sys
from pathlib import Path

# Add project root to the import path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.infrastructure.logger import logger
from src.data.crawler import Crawler
from src.data.parser import HTMLParser

def run_ingestion(force: bool = False, only_modified: bool = False) -> list[dict]:
    """Ties together crawl and parse operations to download and clean the corpus.
    
    Returns a list of parsed scheme data dictionaries that were processed in this run.
    """
    logger.info("Starting ingestion runner...")
    
    # Step 1: Crawl URLs
    crawler = Crawler()
    raw_files = crawler.crawl_all(force=force, only_modified=only_modified)
    
    # Step 2: Parse and Chunk HTML files
    parser = HTMLParser()
    parsed_results = []
    
    for url, file_path in raw_files.items():
        try:
            raw_path = Path(file_path)
            parsed_data = parser.parse_file(raw_path, url)
            parsed_results.append(parsed_data)
        except Exception as e:
            logger.error(f"Failed to parse context for {url}: {e}")
            
    logger.info(f"Ingestion pipeline run finished. Scraped and parsed: {len(parsed_results)} schemes.")
    return parsed_results

def main():
    """Default entry point to ingest all schemes."""
    run_ingestion(force=False, only_modified=False)

if __name__ == "__main__":
    main()
