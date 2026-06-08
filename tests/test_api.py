import sys
import unittest
from pathlib import Path

# Add project root to import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data.vector_store import VectorStore

import tempfile
# Create a test-specific temporary DB folder to isolate tests and avoid SQLite locks
test_db_dir = Path(tempfile.mkdtemp())
test_db_dir.mkdir(parents=True, exist_ok=True)

# Save the original singleton BEFORE overriding so we can restore it after tests
_original_vs_instance = VectorStore._instance

# Initialize and set the global singleton instance before importing api/app
test_store = VectorStore(persist_dir=str(test_db_dir))

# Seed it with a mock document so the database is populated for retriever queries
url = "https://groww.in/mutual-funds/groww-large-cap-fund-direct-growth"
test_store.add_document_chunks(
    url=url,
    scheme_name="Groww Large Cap Fund Direct Growth",
    title="Groww Large Cap Fund - NAV, Performance",
    chunks=["Groww Large Cap Fund has an exit load of 1.00% if redeemed within 1 year."]
)

VectorStore._instance = test_store

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from src.presentation.api import app

class TestAPIGateway(unittest.TestCase):
    """Integration tests for the REST API Gateway (health checks, queries, PII filters)."""
    
    @classmethod
    def tearDownClass(cls):
        # Restore the original VectorStore singleton to prevent poisoning production data
        VectorStore._instance = _original_vs_instance
        
        import shutil
        if test_db_dir.exists():
            shutil.rmtree(test_db_dir, ignore_errors=True)
    
    def setUp(self):
        self.client = TestClient(app)
        
    def test_health_endpoint(self):
        """Verify that GET /api/health returns a healthy status code and payload."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})
        
    def test_chat_valid_query(self):
        """Verify that a valid mutual fund query returns RAG response fields."""
        query = "what is exit load of Groww Large Cap?"
        response = self.client.post("/api/chat", json={"question": query})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIn("source", data)
        self.assertIn("last_updated", data)
        
    def test_chat_empty_query(self):
        """Verify that empty questions are rejected with HTTP 400."""
        response = self.client.post("/api/chat", json={"question": ""})
        self.assertEqual(response.status_code, 400)
        
    def test_pii_blocking_aadhaar(self):
        """Verify that queries containing Aadhaar number patterns are blocked with HTTP 400."""
        # 12-digit format
        query = "what is exit load? My Aadhaar is 1234-5678-9012"
        response = self.client.post("/api/chat", json={"question": query})
        self.assertEqual(response.status_code, 400)
        self.assertIn("security", response.json()["detail"])
        
    def test_pii_blocking_pan(self):
        """Verify that queries containing PAN card patterns are blocked with HTTP 400."""
        # ABCDE1234F format
        query = "who is manager of Groww value fund? My PAN: ABCDE1234F"
        response = self.client.post("/api/chat", json={"question": query})
        self.assertEqual(response.status_code, 400)
        self.assertIn("security", response.json()["detail"])
        
    def test_pii_blocking_phone(self):
        """Verify that queries containing mobile phone numbers are blocked with HTTP 400."""
        # 10 digits
        query = "exit load of small cap fund. Call me on 9876543210"
        response = self.client.post("/api/chat", json={"question": query})
        self.assertEqual(response.status_code, 400)
        self.assertIn("security", response.json()["detail"])

    def test_pii_blocking_email(self):
        """Verify that queries containing email addresses are blocked with HTTP 400."""
        query = "send aum to test@example.com"
        response = self.client.post("/api/chat", json={"question": query})
        self.assertEqual(response.status_code, 400)
        self.assertIn("security", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
