import time
import random
import json
import hashlib
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from src.infrastructure.logger import logger
from src.infrastructure.config import Config
from src.infrastructure.exceptions import ScrapingException

# 34 Target Mutual Fund URLs whitelisted for the Corpus
MUTUAL_FUND_URLS = [
    # Groww AMC Specific Funds
    "https://groww.in/mutual-funds/groww-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-multicap-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-value-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-elss-tax-saver-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-aggressive-hybrid-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-arbitrage-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-banking-financial-services-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-liquid-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-overnight-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-dynamic-bond-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-short-duration-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-total-market-index-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-smallcap-250-index-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-india-railways-psu-index-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-india-defence-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-ev-new-age-automotive-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-non-cyclical-consumer-index-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-private-bank-index-fund-direct-growth",
    "https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/groww-silver-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/groww-bse-power-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/groww-nifty-200-etf-fof-direct-growth",
    # Popular Platform Funds
    "https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth",
    "https://groww.in/mutual-funds/nippon-india-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/quant-small-cap-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/quant-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/quant-infrastructure-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-mid-cap-opportunities-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/kotak-midcap-fund-direct-growth",
    "https://groww.in/mutual-funds/canara-robeco-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/mirae-asset-elss-tax-saver-fund-direct-growth",
    "https://groww.in/mutual-funds/sbi-contra-fund-direct-growth"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

class Crawler:
    """Manages the network crawl and raw caching of mutual fund webpages with checksum-based diff checks."""
    
    def __init__(self):
        self.raw_dir = Config.RAW_DATA_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.checksums_path = Config.PROCESSED_DATA_DIR / "checksums.json"
        self.checksums = self._load_checksums()
        
    def _load_checksums(self) -> dict:
        """Loads persistent crawled page checksums from disk."""
        if self.checksums_path.exists():
            try:
                with open(self.checksums_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load checksums: {e}")
        return {}

    def _save_checksums(self):
        """Saves current crawled page checksums to disk."""
        try:
            self.checksums_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checksums_path, "w", encoding="utf-8") as f:
                json.dump(self.checksums, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save checksums: {e}")
        
    def _get_filename(self, url: str) -> str:
        """Derives a clean filesystem filename from a Groww scheme URL."""
        base_name = url.rstrip("/").split("/")[-1]
        return f"{base_name}.html"
        
    def fetch_url(self, url: str) -> str:
        """Fetches raw HTML contents of a single URL with agent rotation."""
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        try:
            logger.info(f"Crawling: {url}")
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to crawl {url}: {e}")
            raise ScrapingException(f"Network error fetching {url}: {e}")
            
    def crawl_all(self, force: bool = False, only_modified: bool = False) -> dict:
        """Crawls all 34 mutual fund webpages and persists them only if modified or forced."""
        results = {}
        logger.info(f"Initiating mutual fund crawl. Target URLs: {len(MUTUAL_FUND_URLS)}")
        
        # Reload checksums to capture external/concurrent updates
        self.checksums = self._load_checksums()
        
        for url in MUTUAL_FUND_URLS:
            filename = self._get_filename(url)
            file_path = self.raw_dir / filename
            
            try:
                # Scrape URL
                html_content = self.fetch_url(url)
                
                # Calculate stable checksum by stripping dynamic HTML tags
                soup = BeautifulSoup(html_content, "html.parser")
                for tag in ["script", "style", "meta", "input"]:
                    for element in soup.find_all(tag):
                        element.decompose()
                cleaned_text = soup.get_text()
                html_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
                
                is_modified = True
                if url in self.checksums and self.checksums[url] == html_hash and file_path.exists() and not force:
                    is_modified = False
                    
                if not is_modified:
                    logger.info(f"Content unmodified for {filename}, skipping disk write.")
                    if not only_modified:
                        results[url] = str(file_path)
                else:
                    # Write/update raw file on disk
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    logger.info(f"Successfully cached/updated raw file: {filename}")
                    
                    # Update checksum
                    self.checksums[url] = html_hash
                    self._save_checksums()
                    
                    results[url] = str(file_path)
                
                # Respectful rate-limiting pause
                time.sleep(random.uniform(1.0, 2.5))
                
            except Exception as e:
                logger.error(f"Error processing crawl for {url}: {e}")
                # Fallback to cached file if it exists and we're not filtering for only modified
                if file_path.exists() and not only_modified:
                    results[url] = str(file_path)
                
        logger.info("Crawling completed successfully.")
        return results

if __name__ == "__main__":
    # Scrape data directly when run as script
    crawler = Crawler()
    crawler.crawl_all()
