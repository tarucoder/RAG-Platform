import re
import json
from pathlib import Path
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import markdownify
from src.infrastructure.logger import logger
from src.infrastructure.config import Config
from src.infrastructure.exceptions import ScrapingException

class HTMLParser:
    """Parses and sanitizes mutual fund HTML pages into clean text and structured chunks."""
    
    def __init__(self):
        self.processed_dir = Config.PROCESSED_DATA_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
    def _extract_markdown_table(self, table_tag) -> str:
        """Converts an HTML table tag into a clean Markdown table format."""
        rows = table_tag.find_all("tr")
        if not rows:
            return ""
            
        md_rows = []
        for i, row in enumerate(rows):
            cols = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
            
            # Format rows
            md_row = "| " + " | ".join(cols) + " |"
            md_rows.append(md_row)
            
            # Insert markdown header separator line
            if i == 0 and len(rows) > 1:
                separator = "| " + " | ".join(["---"] * len(cols)) + " |"
                md_rows.append(separator)
                
        return "\n".join(md_rows)
        
    def clean_html(self, html_content: str) -> tuple[str, str]:
        """Strips HTML boilerplate and returns page title and cleaned markdown text."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "Groww Mutual Fund Scheme"
        
        # Remove noisy elements (navigation, footers, script, stylesheet, headers)
        for element in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()
            
        # Target specific content wrappers if present
        main_content = soup.find(id="root") or soup.find(id="amcMainPage") or soup
        
        # Parse tables before flattening structure
        tables = main_content.find_all("table")
        for table in tables:
            md_table = self._extract_markdown_table(table)
            if md_table:
                # Replace HTML table with markdown table placeholder
                table.replace_with(soup.new_string(f"\n\n{md_table}\n\n"))
                
        # Convert main content HTML to clean markdown using markdownify
        text = markdownify.markdownify(str(main_content), heading_style="ATX")
        
        # Clean extra white spaces and duplicate newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        return title, text
        
    def recursive_chunk_split(self, text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
        """Recursively splits clean text into overlaps of target dimensions, leaving tables intact."""
        chunks = []
        
        # Identify atomic blocks (e.g. Markdown tables start and end with '|')
        # We split text by double newlines first (paragraphs/tables)
        blocks = text.split("\n\n")
        
        current_chunk = []
        current_length = 0
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            block_length = len(block)
            
            # Table preservation check: if it looks like a markdown table, keep it atomic
            is_table = block.startswith("|") and block.endswith("|")
            
            if is_table:
                # If table alone fits or is slightly larger, push current chunk and push table as single chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                chunks.append(block)
                continue
                
            # Normal text block processing
            if current_length + block_length + 2 <= chunk_size:
                current_chunk.append(block)
                current_length += block_length + 2
            else:
                # Close current chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    
                # Create overlap context from previous block if possible
                overlap_text = []
                overlap_length = 0
                if current_chunk:
                    prev_block = current_chunk[-1]
                    if len(prev_block) <= overlap:
                        overlap_text.append(prev_block)
                        overlap_length = len(prev_block)
                        
                current_chunk = overlap_text + [block]
                current_length = overlap_length + block_length
                
        # Append residual blocks
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks
        
    def parse_file(self, raw_filepath: Path, url: str) -> dict:
        """Parses a single raw HTML file, chunks the text, and persists structured JSON metadata."""
        try:
            logger.info(f"Parsing raw file: {raw_filepath.name}")
            with open(raw_filepath, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            title, cleaned_text = self.clean_html(html_content)
            
            # Extract scheme name from title
            scheme_name = title.split("-")[0].strip()
            
            # Split into chunks
            chunks = self.recursive_chunk_split(cleaned_text)
            
            # Prepare parsed structure
            parsed_data = {
                "url": url,
                "scheme_name": scheme_name,
                "title": title,
                "raw_file": str(raw_filepath),
                "full_text": cleaned_text,
                "chunks": chunks
            }
            
            # Save as JSON structure
            out_filename = raw_filepath.stem + ".json"
            out_path = self.processed_dir / out_filename
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Successfully processed and chunked scheme. Output chunks: {len(chunks)}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing file {raw_filepath.name}: {e}")
            raise ScrapingException(f"Parsing failure for {raw_filepath.name}: {e}")

if __name__ == "__main__":
    # Test execution
    parser = HTMLParser()
    raw_dir = Config.RAW_DATA_DIR
    for raw_file in raw_dir.glob("*.html"):
        parser.parse_file(raw_file, "https://groww.in/mutual-funds/" + raw_file.stem)
