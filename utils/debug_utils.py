"""Debug utilities for scraping."""

from bs4 import BeautifulSoup
from pathlib import Path


def save_html_debug(soup: BeautifulSoup, filename: str):
    """Save HTML to file for debugging."""
    debug_dir = Path("debug_html")
    debug_dir.mkdir(exist_ok=True)
    filepath = debug_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))
    print(f"Debug HTML saved to: {filepath}")

