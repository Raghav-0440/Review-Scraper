"""G2 review scraper."""

from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import urllib.parse

from scrapers.base_scraper import BaseScraper
from utils.date_utils import parse_date


class G2Scraper(BaseScraper):
    """Scraper for G2 reviews."""
    
    def get_source_name(self) -> str:
        """Get the source name."""
        return "g2"
    
    def get_company_url(self) -> str:
        """Get the URL for the company's G2 review page."""
        # G2 URL format: https://www.g2.com/products/{company-slug}/reviews
        company_slug = self.company.lower().replace(' ', '-').replace('&', 'and').replace('.', '')
        # Remove special characters
        company_slug = ''.join(c for c in company_slug if c.isalnum() or c == '-')
        return f"https://www.g2.com/products/{company_slug}/reviews"
    
    def get_review_elements(self, soup: BeautifulSoup) -> List:
        """Extract review elements from a BeautifulSoup object."""
        reviews = []
        
        # Strategy 1: Look for G2-specific review containers
        # G2 often uses specific class patterns
        selectors = [
            # Common G2 patterns
            ('div', {'class': lambda x: x and isinstance(x, (list, str)) and any('review-card' in str(c).lower() or 'reviewItem' in str(c).lower() or 'review-item' in str(c).lower() for c in (x if isinstance(x, list) else [x]))}),
            ('article', {'class': lambda x: x and isinstance(x, (list, str)) and any('review' in str(c).lower() for c in (x if isinstance(x, list) else [x]))}),
            ('div', {'data-testid': lambda x: x and 'review' in str(x).lower()}),
            ('div', {'data-review-id': True}),
            ('div', {'id': lambda x: x and 'review' in str(x).lower()}),
            # Look for list items containing reviews
            ('li', {'class': lambda x: x and isinstance(x, (list, str)) and any('review' in str(c).lower() for c in (x if isinstance(x, list) else [x]))}),
        ]
        
        for tag, attrs in selectors:
            found = soup.find_all(tag, attrs)
            if found and len(found) > 0:
                reviews.extend(found)
                if len(reviews) >= 5:  # If we found several, likely correct
                    break
        
        # Strategy 2: Look for any container with review-related text/content
        if not reviews or len(reviews) < 3:
            # Look for divs that contain review-like structure
            all_divs = soup.find_all('div', limit=200)
            for div in all_divs:
                text = div.get_text().lower()
                # Check if it looks like a review (has rating, date, text)
                if any(keyword in text for keyword in ['star', 'rating', 'review', 'reviewed']) and len(text) > 50:
                    # Check if it has child elements that suggest it's a review container
                    children = div.find_all(['p', 'span', 'div'], limit=5)
                    if len(children) >= 3:  # Likely a review container
                        reviews.append(div)
                        if len(reviews) >= 10:
                            break
        
        # Strategy 3: Look for JSON data in script tags
        if not reviews or len(reviews) < 3:
            json_scripts = soup.find_all('script', type='application/json')
            json_scripts.extend(soup.find_all('script', type='application/ld+json'))
            for script in json_scripts:
                if not script.string:
                    continue
                try:
                    import json
                    import re
                    # Look for review data patterns
                    script_text = script.string
                    # Try to find review arrays
                    patterns = [
                        r'"reviews"\s*:\s*\[(.*?)\]',
                        r'"items"\s*:\s*\[(.*?)\]',
                        r'"data"\s*:\s*\[(.*?)\]',
                    ]
                    for pattern in patterns:
                        matches = re.finditer(pattern, script_text, re.DOTALL)
                        for match in matches:
                            # Found potential review data
                            pass
                except:
                    pass
        
        # Remove duplicates
        seen = set()
        unique_reviews = []
        for review in reviews:
            review_id = id(review)
            if review_id not in seen:
                seen.add(review_id)
                unique_reviews.append(review)
        
        return unique_reviews
    
    def parse_review(self, review_element) -> Optional[Dict]:
        """Parse a single G2 review element."""
        try:
            import re
            review = {
                'title': '',
                'review_text': '',
                'review_date': '',
                'reviewer': '',
                'rating': '',
                'source': 'g2'
            }
            
            # Extract title - try multiple strategies
            title_selectors = [
                ('h2', {}),
                ('h3', {}),
                ('h4', {}),
                ('h5', {}),
                ('div', {'class': lambda x: x and isinstance(x, (list, str)) and 'title' in str(x).lower()}),
                ('span', {'class': lambda x: x and isinstance(x, (list, str)) and 'title' in str(x).lower()}),
            ]
            for tag, attrs in title_selectors:
                title_elem = review_element.find(tag, attrs)
                if title_elem:
                    review['title'] = title_elem.get_text(strip=True)
                    break
            
            # Extract review text - try multiple strategies
            text_selectors = [
                ('p', {'class': lambda x: x and isinstance(x, (list, str)) and ('review' in str(x).lower() or 'text' in str(x).lower() or 'content' in str(x).lower() or 'body' in str(x).lower() or 'description' in str(x).lower())}),
                ('div', {'class': lambda x: x and isinstance(x, (list, str)) and ('review' in str(x).lower() or 'text' in str(x).lower() or 'content' in str(x).lower() or 'body' in str(x).lower() or 'description' in str(x).lower())}),
                ('span', {'class': lambda x: x and isinstance(x, (list, str)) and ('review' in str(x).lower() or 'text' in str(x).lower() or 'content' in str(x).lower() or 'description' in str(x).lower())}),
                # Try to find the longest text block
                ('p', {}),
                ('div', {}),
            ]
            
            longest_text = ''
            for tag, attrs in text_selectors:
                text_elems = review_element.find_all(tag, attrs)
                for text_elem in text_elems:
                    text = text_elem.get_text(strip=True)
                    # Skip if it's likely a title, date, or other metadata
                    if len(text) > len(longest_text) and len(text) > 30:
                        # Check if it's not likely a date or rating
                        if not re.match(r'^\d+[/-]\d+', text) and not re.match(r'^\d+\.?\d*\s*(star|out of)', text.lower()):
                            longest_text = text
            
            if longest_text:
                review['review_text'] = longest_text
            else:
                # Fallback: get all text and try to extract review portion
                all_text = review_element.get_text(strip=True)
                # Try to find substantial text blocks
                lines = [line.strip() for line in all_text.split('\n') if len(line.strip()) > 30]
                if lines:
                    review['review_text'] = ' '.join(lines[:3])  # Take first few substantial lines
            
            # Extract date - try multiple strategies
            date_elem = review_element.find('time')
            if date_elem:
                review['review_date'] = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
            else:
                # Try span/div with date class
                date_elem = review_element.find(['span', 'div'], {'class': lambda x: x and isinstance(x, (list, str)) and 'date' in str(x).lower()})
                if date_elem:
                    review['review_date'] = date_elem.get_text(strip=True)
                else:
                    # Try to find date patterns in text
                    date_text = review_element.get_text()
                    date_patterns = [
                        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY
                        r'([A-Z][a-z]+ \d{1,2}, \d{4})',  # Month DD, YYYY
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
                    # Count stars
                    stars = rating_elem.find_all(['svg', 'i', 'span'], {'class': lambda x: x and isinstance(x, (list, str)) and 'star' in str(x).lower()})
                    if stars:
                        filled = [s for s in stars if 'filled' in str(s).lower() or 'full' in str(s).lower() or 'active' in str(s).lower()]
                        review['rating'] = str(len(filled))
            
            # Only return if we have at least review text or title
            if review['review_text'] or review['title']:
                return review
            
        except Exception as e:
            print(f"Error parsing G2 review: {e}")
        
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

