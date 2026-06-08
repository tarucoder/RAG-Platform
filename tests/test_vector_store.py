import sys
import unittest
import shutil
from pathlib import Path

# Add src to the path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data.vector_store import VectorStore

class TestVectorStore(unittest.TestCase):
    """Unit tests for the local persistent vector store client."""
    
    def setUp(self):
        # Create a test-specific temporary DB folder inside the workspace data directory
        self.test_db_dir = Path(__file__).resolve().parent.parent / "data" / "test_vector_db"
        self.test_db_dir.mkdir(parents=True, exist_ok=True)
        self.store = VectorStore(persist_dir=str(self.test_db_dir))
        
    def tearDown(self):
        # Remove Chroma test folder files and directory
        if self.test_db_dir.exists():
            shutil.rmtree(self.test_db_dir, ignore_errors=True)

    def test_indexing_and_retrieval(self):
        """Test adding document chunks to the collection and retrieving them via similarity search."""
        url = "https://groww.in/mutual-funds/test-scheme-direct-growth"
        scheme_name = "Test Scheme Direct Growth"
        title = "Test Scheme Direct Growth - NAV, Performance"
        chunks = [
            "Groww Large Cap Fund has an exit load of 1.00% if redeemed within 1 year.",
            "ELSS Tax Saver funds have a strict statutory lock-in period of 3 years.",
            "Fund managers Shridatta Bhandwaldar and Vishal Mishra manage this portfolio."
        ]
        
        self.store.add_document_chunks(url, scheme_name, title, chunks)
        
        # Query 1: Exit load
        results = self.store.query_instance("exit load", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("exit load of 1.00%", results[0]["document"])
        self.assertEqual(results[0]["metadata"]["url"], url)
        self.assertEqual(results[0]["metadata"]["scheme_name"], scheme_name)
        
        # Query 2: Lock-in period
        results = self.store.query_instance("ELSS statutory lock-in", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("lock-in period of 3 years", results[0]["document"])
        
    def test_purging_on_reindex(self):
        """Test that re-indexing a URL purges old chunks to prevent duplicates/orphans."""
        url = "https://groww.in/mutual-funds/purge-scheme"
        scheme_name = "Purge Scheme"
        title = "Purge Scheme title"
        
        # Index initial 3 chunks
        chunks_v1 = ["Chunk 1 content here.", "Chunk 2 content here.", "Chunk 3 content here."]
        self.store.add_document_chunks(url, scheme_name, title, chunks_v1)
        
        # Verify collection size is at least 3
        results = self.store.collection.get(where={"url": url})
        self.assertEqual(len(results["ids"]), 3)
        
        # Re-index with only 1 chunk
        chunks_v2 = ["Updated single chunk content."]
        self.store.add_document_chunks(url, scheme_name, title, chunks_v2)
        
        # Verify old chunks were purged and only 1 remains
        results_after = self.store.collection.get(where={"url": url})
        self.assertEqual(len(results_after["ids"]), 1)
        self.assertEqual(results_after["documents"][0], "Updated single chunk content.")

if __name__ == "__main__":
    unittest.main()
