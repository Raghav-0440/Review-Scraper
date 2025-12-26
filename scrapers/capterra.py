"""Capterra review scraper."""

from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import urllib.parse

from scrapers.base_scraper import BaseScraper
from utils.date_utils import parse_date


class CapterraScraper(BaseScraper):
    """Scraper for Capterra reviews."""
    
    def get_source_name(self) -> str:
        """Get the source name."""
        return "capterra"
    
    def get_company_url(self) -> str:
        """Get the URL for the company's Capterra review page."""
        # Capterra URL format: https://www.capterra.com/p/{company-slug}/reviews
        company_slug = self.company.lower().replace(' ', '-').replace('&', 'and').replace('.', '')
        # Remove special characters
        company_slug = ''.join(c for c in company_slug if c.isalnum() or c == '-')
        return f"https://www.capterra.com/p/{company_slug}/reviews"
    
    def get_review_elements(self, soup: BeautifulSoup) -> List:
        """Extract review elements from a BeautifulSoup object."""
        reviews = []
        
        # Try multiple strategies to find reviews
        selectors = [
            ('div', {'class': lambda x: x and isinstance(x, (list, str)) and 'review' in str(x).lower()}),
            ('article', {'class': lambda x: x and isinstance(x, (list, str)) and 'review' in str(x).lower()}),
            ('div', {'data-review-id': True}),
            ('section', {'class': lambda x: x and isinstance(x, (list, str)) and 'review' in str(x).lower()}),
            ('li', {'class': lambda x: x and isinstance(x, (list, str)) and 'review' in str(x).lower()}),
        ]
        
        for tag, attrs in selectors:
            found = soup.find_all(tag, attrs)
            if found:
                reviews.extend(found)
                break
        
        # Try to extract from JSON-LD or embedded JSON
        if not reviews:
            json_scripts = soup.find_all('script', type='application/json')
            json_scripts.extend(soup.find_all('script', type='application/ld+json'))
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    # Look for review data in JSON
                    if isinstance(data, dict):
                        # Common patterns: reviews array, reviewList, etc.
                        for key in ['reviews', 'reviewList', 'items', 'data']:
                            if key in data and isinstance(data[key], list):
                                # Found potential review data
                                pass
                except:
                    pass
        
        # Fallback: look for any review-like containers
        if not reviews:
            reviews = soup.find_all(['div', 'article', 'li'], attrs={
                'class': lambda x: x and (
                    (isinstance(x, list) and any('review' in str(c).lower() for c in x)) or
                    (isinstance(x, str) and 'review' in x.lower())
                )
            })
        
        return reviews
    
    def parse_review(self, review_element) -> Optional[Dict]:
        """Parse a single Capterra review element."""
        try:
            import re
            review = {
                'title': '',
                'review_text': '',
                'review_date': '',
                'reviewer': '',
                'rating': '',
                'source': 'capterra'
            }
            
            # Extract title
            title_selectors = [
                ('h2', {}),
                ('h3', {}),
                ('h4', {}),
                ('div', {'class': lambda x: x and isinstance(x, (list, str)) and 'title' in str(x).lower()}),
                ('span', {'class': lambda x: x and isinstance(x, (list, str)) and 'title' in str(x).lower()}),
            ]
            for tag, attrs in title_selectors:
                title_elem = review_element.find(tag, attrs)
                if title_elem:
                    review['title'] = title_elem.get_text(strip=True)
                    break
            
            # Extract review text
            text_selectors = [
                ('p', {'class': lambda x: x and isinstance(x, (list, str)) and ('review' in str(x).lower() or 'text' in str(x).lower() or 'content' in str(x).lower() or 'body' in str(x).lower())}),
                ('div', {'class': lambda x: x and isinstance(x, (list, str)) and ('review' in str(x).lower() or 'text' in str(x).lower() or 'content' in str(x).lower() or 'body' in str(x).lower())}),
                ('span', {'class': lambda x: x and isinstance(x, (list, str)) and ('review' in str(x).lower() or 'text' in str(x).lower() or 'content' in str(x).lower())}),
                ('p', {}),
            ]
            for tag, attrs in text_selectors:
                text_elem = review_element.find(tag, attrs)
                if text_elem:
                    text = text_elem.get_text(strip=True)
                    if len(text) > 20:
                        review['review_text'] = text
                        break
            
            # Extract date
            date_elem = review_element.find('time')
            if date_elem:
                review['review_date'] = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
            else:
                date_elem = review_element.find(['span', 'div'], {'class': lambda x: x and isinstance(x, (list, str)) and 'date' in str(x).lower()})
                if date_elem:
                    review['review_date'] = date_elem.get_text(strip=True)
                else:
                    date_text = review_element.get_text()
                    date_patterns = [
                        r'(\d{4}-\d{2}-\d{2})',
                        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                        r'([A-Z][a-z]+ \d{1,2}, \d{4})',
                    ]
                    for pattern in date_patterns:
                        date_match = re.search(pattern, date_text)
                        if date_match:
                            review['review_date'] = date_match.group(1)
                            break
            
            # Extract reviewer name
            reviewer_selectors = [
                ('a', {'class': lambda x: x and isinstance(x, (list, str)) and ('user' in str(x).lower() or 'author' in str(x).lower() or 'reviewer' in str(x).lower())}),
                ('span', {'class': lambda x: x and isinstance(x, (list, str)) and ('user' in str(x).lower() or 'author' in str(x).lower() or 'reviewer' in str(x).lower())}),
                ('div', {'class': lambda x: x and isinstance(x, (list, str)) and ('user' in str(x).lower() or 'author' in str(x).lower())}),
            ]
            for tag, attrs in reviewer_selectors:
                reviewer_elem = review_element.find(tag, attrs)
                if reviewer_elem:
                    review['reviewer'] = reviewer_elem.get_text(strip=True)
                    break
            
            # Extract rating
            rating_elem = review_element.find(['div', 'span'], {'class': lambda x: x and isinstance(x, (list, str)) and 'rating' in str(x).lower()})
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
                else:
                    stars = rating_elem.find_all(['svg', 'i', 'span'], {'class': lambda x: x and isinstance(x, (list, str)) and 'star' in str(x).lower()})
                    if stars:
                        filled = [s for s in stars if 'filled' in str(s).lower() or 'full' in str(s).lower() or 'active' in str(s).lower()]
                        review['rating'] = str(len(filled))
            
            # Only return if we have at least review text or title
            if review['review_text'] or review['title']:
                return review
            
        except Exception as e:
            print(f"Error parsing Capterra review: {e}")
        
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

