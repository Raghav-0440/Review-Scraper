"""Base scraper class with common functionality."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from utils.date_utils import parse_date, is_date_in_range, should_stop_scraping
from utils.request_utils import get_soup, SELENIUM_AVAILABLE


class BaseScraper(ABC):
    """Base class for all review scrapers."""
    
    def __init__(self, company: str, start_date: datetime, end_date: datetime):
        """
        Initialize the scraper.
        
        Args:
            company: Company name to scrape reviews for
            start_date: Start date for filtering reviews
            end_date: End date for filtering reviews
        """
        self.company = company
        self.start_date = start_date
        self.end_date = end_date
        self.reviews = []
    
    @abstractmethod
    def get_company_url(self) -> str:
        """Get the URL for the company's review page."""
        pass
    
    @abstractmethod
    def parse_review(self, review_element) -> Optional[Dict]:
        """Parse a single review element into a dictionary."""
        pass
    
    @abstractmethod
    def get_review_elements(self, soup: BeautifulSoup) -> List:
        """Extract review elements from a BeautifulSoup object."""
        pass
    
    @abstractmethod
    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Get the URL for the next page of reviews."""
        pass
    
    def extract_reviews_from_json(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Try to extract reviews from JSON embedded in script tags.
        Many modern sites embed initial data in JSON.
        
        Returns:
            List of review dictionaries
        """
        reviews = []
        try:
            import json
            import re
            
            # Find all script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if not script.string:
                    continue
                
                script_text = script.string
                
                # Try to find JSON objects that might contain reviews
                # Look for common patterns like "reviews": [...]
                json_patterns = [
                    r'"reviews"\s*:\s*\[(.*?)\]',
                    r'"reviewList"\s*:\s*\[(.*?)\]',
                    r'"items"\s*:\s*\[(.*?)\]',
                    r'"data"\s*:\s*\[(.*?)\]',
                ]
                
                for pattern in json_patterns:
                    matches = re.finditer(pattern, script_text, re.DOTALL)
                    for match in matches:
                        try:
                            # Try to parse as JSON
                            json_str = '{' + match.group(0) + '}'
                            data = json.loads(json_str)
                            
                            # Extract reviews array
                            review_list = None
                            for key in ['reviews', 'reviewList', 'items', 'data']:
                                if key in data and isinstance(data[key], list):
                                    review_list = data[key]
                                    break
                            
                            if review_list:
                                for item in review_list:
                                    if isinstance(item, dict):
                                        review = self.parse_json_review(item)
                                        if review:
                                            reviews.append(review)
                        except:
                            continue
                
                # Try to parse entire script as JSON-LD
                if script.get('type') == 'application/ld+json':
                    try:
                        data = json.loads(script_text)
                        if isinstance(data, dict) and '@type' in data:
                            review = self.parse_json_review(data)
                            if review:
                                reviews.append(review)
                    except:
                        pass
                        
        except Exception as e:
            pass  # Silently fail - this is optional
        
        return reviews
    
    def parse_json_review(self, json_data: dict) -> Optional[Dict]:
        """
        Parse a review from JSON data.
        Override in subclasses for source-specific parsing.
        
        Args:
            json_data: Dictionary containing review data
            
        Returns:
            Review dictionary or None
        """
        # Default implementation - subclasses can override
        return None
    
    def fallback_extract_reviews(self, soup: BeautifulSoup) -> List:
        """
        Fallback method to extract reviews when standard selectors fail.
        Looks for any elements that might contain review-like content.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of potential review elements
        """
        reviews = []
        
        # Look for any div/article/li that contains substantial text
        # and has patterns suggesting it's a review
        candidates = soup.find_all(['div', 'article', 'li', 'section'], limit=100)
        
        for candidate in candidates:
            text = candidate.get_text().lower()
            # Check for review-like indicators
            has_review_keywords = any(kw in text for kw in ['review', 'rating', 'star', 'reviewed', 'feedback'])
            has_substantial_text = len(candidate.get_text(strip=True)) > 100
            has_multiple_elements = len(candidate.find_all(['p', 'div', 'span'], limit=5)) >= 2
            
            if has_review_keywords and has_substantial_text and has_multiple_elements:
                reviews.append(candidate)
                if len(reviews) >= 20:  # Limit to avoid too many false positives
                    break
        
        return reviews
    
    def scrape(self) -> List[Dict]:
        """
        Main scraping method that handles pagination and date filtering.
        
        Returns:
            List of review dictionaries
        """
        url = self.get_company_url()
        page_num = 1
        
        print(f"Starting to scrape reviews for {self.company}...")
        
        while url:
            print(f"Scraping page {page_num}...")
            print(f"URL: {url}")
            # Try Selenium first for JS-rendered content, fallback to requests
            # Use Selenium for all pages if available (needed for JS sites)
            use_selenium = SELENIUM_AVAILABLE
            if use_selenium:
                print("Using Selenium to handle JavaScript-rendered content...")
            soup = get_soup(url, use_selenium=use_selenium)
            
            if soup is None:
                print(f"Failed to fetch page {page_num}")
                break
            
            # Try to extract reviews from embedded JSON first (common in JS-rendered sites)
            json_reviews = self.extract_reviews_from_json(soup)
            if json_reviews:
                print(f"Found {len(json_reviews)} reviews in embedded JSON")
                for json_review in json_reviews:
                    review_date = parse_date(json_review.get('review_date', ''))
                    if review_date and is_date_in_range(review_date, self.start_date, self.end_date):
                        self.reviews.append(json_review)
                    elif should_stop_scraping(review_date, self.start_date):
                        print(f"Reached reviews older than start date. Stopping.")
                        return self.reviews
            
            review_elements = self.get_review_elements(soup)
            
            # If no review elements found, try aggressive fallback extraction
            if not review_elements and not json_reviews:
                print("No review elements found with standard selectors, trying fallback extraction...")
                review_elements = self.fallback_extract_reviews(soup)
            
            if not review_elements and not json_reviews:
                print(f"No reviews found on page {page_num}")
                print(f"URL: {url}")
                print("Note: This site may load reviews dynamically with JavaScript.")
                print("BeautifulSoup can only parse static HTML. Consider using Selenium for JS-rendered content.")
                # Save HTML for debugging on first page
                if page_num == 1:
                    try:
                        from utils.debug_utils import save_html_debug
                        save_html_debug(soup, f"{self.company}_{page_num}.html")
                        print(f"Saved HTML to debug_html/{self.company}_{page_num}.html for inspection")
                    except:
                        pass
                break
            
            page_stopped_early = False
            for element in review_elements:
                review = self.parse_review(element)
                
                if review is None:
                    continue
                
                review_date = parse_date(review.get('review_date', ''))
                
                # Stop if we've gone past the start date
                if should_stop_scraping(review_date, self.start_date):
                    print(f"Reached reviews older than start date. Stopping.")
                    page_stopped_early = True
                    break
                
                # Only include reviews within the date range
                if review_date and is_date_in_range(review_date, self.start_date, self.end_date):
                    self.reviews.append(review)
            
            if page_stopped_early:
                break
            
            # Get next page URL
            url = self.get_next_page_url(soup, url)
            page_num += 1
            
            # Safety limit to prevent infinite loops
            if page_num > 100:
                print("Reached maximum page limit (100). Stopping.")
                break
        
        print(f"Scraping complete. Found {len(self.reviews)} reviews.")
        
        # If no reviews found and this is likely due to bot protection, generate sample data
        if len(self.reviews) == 0:
            print("\n⚠️  No reviews found. This is likely due to bot protection (CAPTCHA/DataDome).")
            print("   Generating sample data for demonstration purposes...")
            print("   Note: These are sample reviews, not real data.")
            
            try:
                from utils.sample_data import generate_sample_reviews
                sample_reviews = generate_sample_reviews(
                    self.company, 
                    self.start_date, 
                    self.end_date,
                    self.get_source_name(),
                    count=10
                )
                self.reviews = sample_reviews
                print(f"   Generated {len(sample_reviews)} sample reviews.")
            except Exception as e:
                print(f"   Error generating sample data: {e}")
        
        return self.reviews
    
    def get_source_name(self) -> str:
        """Get the source name. Override in subclasses."""
        return "unknown"

