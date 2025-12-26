"""Date utility functions for parsing and comparing review dates."""

from datetime import datetime
from typing import Optional


def parse_date(date_str: str, formats: list = None) -> Optional[datetime]:
    """
    Parse a date string using multiple formats.
    
    Args:
        date_str: Date string to parse
        formats: List of date format strings to try
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
        ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def is_date_in_range(review_date: datetime, start_date: datetime, end_date: datetime) -> bool:
    """
    Check if a review date is within the specified range.
    
    Args:
        review_date: The review date to check
        start_date: Start date of the range
        end_date: End date of the range
        
    Returns:
        True if review_date is between start_date and end_date (inclusive)
    """
    return start_date <= review_date <= end_date


def should_stop_scraping(review_date: Optional[datetime], start_date: datetime) -> bool:
    """
    Determine if scraping should stop because we've gone past the start date.
    
    Args:
        review_date: The current review date (None if parsing failed)
        start_date: The earliest date we want to scrape
        
    Returns:
        True if we should stop scraping (review is older than start_date)
    """
    if review_date is None:
        return False  # Continue if we can't parse the date
    
    return review_date < start_date

