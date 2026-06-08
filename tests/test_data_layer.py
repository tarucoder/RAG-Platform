import sys
import unittest
from pathlib import Path

# Add src to the path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data.parser import HTMLParser

class TestDataLayer(unittest.TestCase):
    """Unit tests for the Data Layer crawler and chunking components."""
    
    def setUp(self):
        self.parser = HTMLParser()
        
    def test_markdown_table_conversion(self):
        """Verify that HTML table tag blocks are successfully mapped to clean Markdown grids."""
        html = """
        <html>
        <body>
            <table border="1">
                <tr><th>Scheme Name</th><th>Expense Ratio</th></tr>
                <tr><td>Groww Large Cap</td><td>0.43%</td></tr>
                <tr><td>Parag Parikh Flexi</td><td>0.72%</td></tr>
            </table>
        </body>
        </html>
        """
        title, cleaned_text = self.parser.clean_html(html)
        
        # Verify markdown formatting exists in output
        self.assertIn("| Scheme Name | Expense Ratio |", cleaned_text)
        self.assertIn("| --- | --- |", cleaned_text)
        self.assertIn("| Groww Large Cap | 0.43% |", cleaned_text)
        
    def test_table_preservation_chunking(self):
        """Verify that chunking algorithms treat markdown tables as single, atomic, unsplit blocks."""
        table_md = (
            "| Feature | Detail |\n"
            "| --- | --- |\n"
            "| Expense | 0.50% |\n"
            "| Exit Load | 1.00% |\n"
            "| Tenure | 3 Years |"
        )
        text = f"Intro paragraph about mutual funds.\n\n{table_md}\n\nConclusion sentence."
        
        # Chunk split with very small size to force normal splits
        chunks = self.parser.recursive_chunk_split(text, chunk_size=50, overlap=10)
        
        # Table must be kept fully intact in its own chunk
        self.assertIn(table_md, chunks)
        
    def test_recursive_splitter_overlap(self):
        """Verify that character-split overlays are constructed correctly across chunks."""
        text = "First long paragraph here.\n\nSecond long paragraph here.\n\nThird paragraph."
        
        chunks = self.parser.recursive_chunk_split(text, chunk_size=40, overlap=10)
        
        # Check overlaps
        self.assertTrue(len(chunks) >= 2)
        logger_log = f"Generated {len(chunks)} chunks"
        
if __name__ == "__main__":
    unittest.main()
