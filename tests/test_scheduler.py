import sys
import unittest
import tempfile
import shutil
import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to the import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data.crawler import Crawler
from src.data.ingest_runner import run_ingestion
from src.data.vector_store import VectorStore
from src.infrastructure.config import Config

class TestSchedulerAndChecksums(unittest.TestCase):
    """Tests the checksum-based change detection and the daily ingestion scheduler logic."""

    def setUp(self):
        # Create temp directories for raw, processed, and vector_db data to avoid messing with local project data
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Patch config paths to point to test temporary directory
        self.raw_patch = patch.object(Config, "RAW_DATA_DIR", self.test_dir / "raw")
        self.processed_patch = patch.object(Config, "PROCESSED_DATA_DIR", self.test_dir / "processed")
        self.vector_patch = patch.object(Config, "VECTOR_DB_DIR", self.test_dir / "vector_db")
        
        self.raw_patch.start()
        self.processed_patch.start()
        self.vector_patch.start()
        
        # Ensure directories exist
        Config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        Config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        Config.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

        # Mock the list of mutual fund URLs to be short for tests
        self.urls_patch = patch("src.data.crawler.MUTUAL_FUND_URLS", [
            "https://groww.in/mutual-funds/groww-large-cap-fund-direct-growth",
            "https://groww.in/mutual-funds/groww-small-cap-fund-direct-growth"
        ])
        self.urls_patch.start()

        # Mock the time.sleep to run tests fast
        self.sleep_patch = patch("time.sleep", return_value=None)
        self.sleep_patch.start()

    def tearDown(self):
        self.raw_patch.stop()
        self.processed_patch.stop()
        self.vector_patch.stop()
        self.urls_patch.stop()
        self.sleep_patch.stop()
        
        # Clean up temporary directories
        shutil.rmtree(self.test_dir)

    @patch.object(Crawler, "fetch_url")
    def test_checksum_generation_and_detection(self, mock_fetch):
        """Verify that Crawler detects content changes and skips unchanged HTML files."""
        crawler = Crawler()
        
        # 1. First crawl: return same initial HTML content for both schemes
        mock_fetch.side_effect = lambda url: f"<html>Initial content for {url}</html>"
        
        results = crawler.crawl_all(force=False, only_modified=True)
        
        # First crawl should identify both pages as modified/new
        self.assertEqual(len(results), 2)
        
        # Check that files were written and checksums database saved
        checksums_file = Config.PROCESSED_DATA_DIR / "checksums.json"
        self.assertTrue(checksums_file.exists())
        with open(checksums_file, "r") as f:
            checksums = json.load(f)
        self.assertEqual(len(checksums), 2)
        
        # 2. Second crawl: content unchanged
        results_unchanged = crawler.crawl_all(force=False, only_modified=True)
        # Results should be empty since nothing changed
        self.assertEqual(len(results_unchanged), 0)
        
        # 3. Third crawl: change content of one URL
        mock_fetch.side_effect = lambda url: (
            f"<html>Modified content for {url}</html>" 
            if "large-cap" in url 
            else f"<html>Initial content for {url}</html>"
        )
        
        results_one_changed = crawler.crawl_all(force=False, only_modified=True)
        
        # Should detect exactly 1 modified file
        self.assertEqual(len(results_one_changed), 1)
        self.assertIn("https://groww.in/mutual-funds/groww-large-cap-fund-direct-growth", results_one_changed)

    @patch.object(Crawler, "fetch_url")
    def test_run_ingestion_returns_only_modified(self, mock_fetch):
        """Verify run_ingestion only parses and returns modified files."""
        # Setup crawler to return basic HTML and patch HTMLParser.parse_file
        mock_fetch.side_effect = lambda url: f"<html>Factual data about {url}</html>"
        
        # Run ingestion once to set initial checksums
        run_ingestion(force=False, only_modified=False)
        
        # Modify only one scheme
        mock_fetch.side_effect = lambda url: (
            f"<html>Factual data about {url} UPDATED</html>" 
            if "small-cap" in url 
            else f"<html>Factual data about {url}</html>"
        )
        
        # Run ingestion with only_modified=True
        parsed_docs = run_ingestion(force=False, only_modified=True)
        
        # Only the modified scheme should be parsed and returned
        self.assertEqual(len(parsed_docs), 1)
        self.assertEqual(parsed_docs[0]["url"], "https://groww.in/mutual-funds/groww-small-cap-fund-direct-growth")

if __name__ == "__main__":
    unittest.main()
