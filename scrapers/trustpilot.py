"""Trustpilot review scraper."""

from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import urllib.parse

from scrapers.base_scraper import BaseScraper
from utils.date_utils import parse_date


class TrustpilotScraper(BaseScraper):
    """Scraper for Trustpilot reviews."""
    
    def get_source_name(self) -> str:
        """Get the source name."""
        return "trustpilot"
    
    def get_company_url(self) -> str:
        """Get the URL for the company's Trustpilot review page."""
        # Trustpilot URL format: https://www.trustpilot.com/review/{domain}
        company_slug = self.company.lower().replace(' ', '-').replace('&', 'and').replace('.', '')
        # Remove special characters
        company_slug = ''.join(c for c in company_slug if c.isalnum() or c == '-')
        return f"https://www.trustpilot.com/review/{company_slug}.com"
    
    def get_review_elements(self, soup: BeautifulSoup) -> List:
        """Extract review elements from a BeautifulSoup object."""
        # Trustpilot reviews are typically in article elements
        reviews = soup.find_all('article', class_=lambda x: x and 'review' in x.lower())
        
        if not reviews:
            reviews = soup.find_all('div', class_=lambda x: x and 'review' in x.lower())
        
        if not reviews:
            reviews = soup.find_all('section', class_=lambda x: x and 'review' in x.lower())
        
        return reviews
    
    def parse_review(self, review_element) -> Optional[Dict]:
        """Parse a single Trustpilot review element."""
        try:
            review = {
                'title': '',
                'review_text': '',
                'review_date': '',
                'reviewer': '',
                'rating': '',
                'source': 'trustpilot'
            }
            
            # Extract title
            title_elem = review_element.find('h2') or review_element.find('h3')
            if title_elem:
                review['title'] = title_elem.get_text(strip=True)
            
            # Extract review text
            text_elem = review_element.find('p', class_=lambda x: x and ('review' in x.lower() or 'text' in x.lower() or 'content' in x.lower()))
            if not text_elem:
                text_elem = review_element.find('div', class_=lambda x: x and ('review' in x.lower() or 'text' in x.lower() or 'content' in x.lower()))
            if text_elem:
                review['review_text'] = text_elem.get_text(strip=True)
            
            # Extract date
            date_elem = review_element.find('time')
            if date_elem:
                review['review_date'] = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
            else:
                date_span = review_element.find('span', class_=lambda x: x and 'date' in x.lower())
                if date_span:
                    review['review_date'] = date_span.get_text(strip=True)
            
            # Extract reviewer name
            reviewer_elem = review_element.find('a', class_=lambda x: x and 'user' in x.lower())
            if not reviewer_elem:
                reviewer_elem = review_element.find('span', class_=lambda x: x and ('user' in x.lower() or 'author' in x.lower() or 'name' in x.lower()))
            if reviewer_elem:
                review['reviewer'] = reviewer_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = review_element.find('div', class_=lambda x: x and 'rating' in x.lower())
            if not rating_elem:
                rating_elem = review_element.find('span', class_=lambda x: x and 'rating' in x.lower())
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                # Extract number from rating
                import re
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
                else:
                    # Check for star elements
                    stars = rating_elem.find_all('svg') or rating_elem.find_all('i', class_=lambda x: x and 'star' in x.lower())
                    if stars:
                        review['rating'] = str(len([s for s in stars if 'filled' in str(s).lower() or 'full' in str(s).lower()]))
            
            # Only return if we have at least review text or title
            if review['review_text'] or review['title']:
                return review
            
        except Exception as e:
            print(f"Error parsing Trustpilot review: {e}")
        
        return None
    
    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Get the URL for the next page of reviews."""
        # Look for pagination links
        next_link = soup.find('a', {'aria-label': lambda x: x and 'next' in x.lower()})
        if not next_link:
            next_link = soup.find('a', class_=lambda x: x and 'next' in x.lower())
        if not next_link:
            next_link = soup.find('a', string=lambda x: x and 'next' in x.lower() if x else False)
        
        if next_link and next_link.get('href'):
            href = next_link.get('href')
            if href.startswith('http'):
                return href
            else:
                # Relative URL
                base_url = '/'.join(current_url.split('/')[:3])
                return urllib.parse.urljoin(base_url, href)
        
        return None

