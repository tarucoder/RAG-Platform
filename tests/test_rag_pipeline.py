import sys
import unittest
from pathlib import Path

# Add src to the path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.RAG.retriever import Retriever
from src.RAG.prompt_engine import PromptEngine
from src.RAG.generator import Generator
from src.data.vector_store import VectorStore

class TestRAGPipeline(unittest.TestCase):
    """Unit tests for RAG Pipeline components (Retriever, PromptEngine, Generator)."""
    
    def setUp(self):
        # Create a test-specific temporary DB folder to isolate tests
        self.test_dir = Path(__file__).resolve().parent.parent / "data" / "test_rag_pipeline_db"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Instantiate isolated test VectorStore
        self.test_store = VectorStore(persist_dir=str(self.test_dir))
        
        # Insert mock document for retriever test
        url = "https://groww.in/mutual-funds/groww-large-cap-fund-direct-growth"
        self.test_store.add_document_chunks(
            url=url,
            scheme_name="Groww Large Cap Fund Direct Growth",
            title="Groww Large Cap Fund - NAV, Performance",
            chunks=["Groww Large Cap Fund has an exit load of 1.00% if redeemed within 1 year."]
        )
        
        # Override singleton instance to point to our isolated test store
        self.original_instance = VectorStore._instance
        VectorStore._instance = self.test_store
        
        self.retriever = Retriever()
        self.generator = Generator()
        
    def tearDown(self):
        # Restore original singleton
        VectorStore._instance = self.original_instance
        
        # Clean up isolated DB folder
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_retriever_in_domain(self):
        """Verify that relevant mutual fund queries retrieve chunks above the similarity threshold."""
        query = "what is exit load of Groww Large Cap?"
        results = self.retriever.retrieve(query, top_k=2)
        
        # Should retrieve some matching chunks
        self.assertGreater(len(results), 0)
        # Verify metadata exists
        self.assertIn("url", results[0]["metadata"])
        self.assertIn("groww-large-cap-fund-direct-growth", results[0]["metadata"]["url"])

    def test_retriever_out_of_domain(self):
        """Verify that unrelated/noisy queries are completely filtered out by the similarity threshold."""
        query = "how to make a delicious chocolate cake with pasta?"
        results = self.retriever.retrieve(query, top_k=3)
        
        # Similarity threshold should discard all completely unrelated results
        self.assertEqual(len(results), 0)

    def test_prompt_construction(self):
        """Verify prompt builder formats system instructions and chunks correctly."""
        query = "What is the AUM of HDFC Mid Cap?"
        mock_chunks = [
            {
                "id": "hdfc_0",
                "document": "HDFC Mid Cap Fund currently has an AUM of 60000 Cr.",
                "metadata": {
                    "url": "https://groww.in/hdfc-mid-cap",
                    "title": "HDFC Mid Cap Fund"
                }
            }
        ]
        system_p, user_p = PromptEngine.build_prompt(query, mock_chunks)
        
        # Verify rules and context are formatted
        self.assertIn("answer the user query using ONLY the retrieved context", system_p)
        self.assertIn("HDFC Mid Cap Fund currently has an AUM of 60000 Cr.", user_p)
        self.assertIn("https://groww.in/hdfc-mid-cap", user_p)

    def test_compliance_validator_sentence_truncation(self):
        """Verify response is truncated to at most 3 sentences if LLM output is too long."""
        long_answer = (
            "First sentence about mutual funds. "
            "Second sentence stating the facts. "
            "Third sentence outlining details. "
            "Fourth extra sentence that should be truncated."
        )
        mock_context = [
            {
                "document": "Details about scheme",
                "metadata": {"url": "https://groww.in/scheme"}
            }
        ]
        sanitized = self.generator._validate_and_sanitize_response(long_answer, mock_context)
        
        # Count sentences
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', sanitized) if s.strip()]
        self.assertEqual(len(sentences), 3)
        self.assertNotIn("Fourth extra sentence", sanitized)

    def test_compliance_validator_citation_link(self):
        """Verify that citation link is correctly verified or appended if missing."""
        answer_no_link = "Groww Value Fund has exit load of 1%."
        mock_context = [
            {
                "document": "Details",
                "metadata": {"url": "https://groww.in/value-fund"}
            }
        ]
        sanitized = self.generator._validate_and_sanitize_response(answer_no_link, mock_context)
        
        # Verify markdown link exists
        self.assertIn("[official document](https://groww.in/value-fund)", sanitized)

    def test_compliance_validator_multiple_links(self):
        """Verify that only the first markdown link is kept, and others are demoted to plain text."""
        answer_multi_links = (
            "Read details on [first page](https://groww.in/page1). "
            "Also look at [second page](https://groww.in/page2) for returns."
        )
        mock_context = [
            {
                "document": "Details",
                "metadata": {"url": "https://groww.in/page1"}
            }
        ]
        sanitized = self.generator._validate_and_sanitize_response(answer_multi_links, mock_context)
        
        # Verify first link is kept, second is converted to label text
        self.assertIn("[first page](https://groww.in/page1)", sanitized)
        self.assertNotIn("https://groww.in/page2", sanitized)
        self.assertIn("second page", sanitized)

    def test_out_of_domain_generator_refusal(self):
        """Verify generator returns standard refusal for out-of-domain queries."""
        query = "How do I bake bread?"
        response = self.generator.generate(query)
        
        self.assertIn("I don't have that information in my verified sources", response["answer"])
        self.assertIn("https://www.sebi.gov.in", response["answer"])
        self.assertEqual(response["source"], "https://www.sebi.gov.in")

if __name__ == "__main__":
    unittest.main()
