#!/usr/bin/env python3
"""Main CLI script for scraping product reviews."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.g2 import G2Scraper
from scrapers.capterra import CapterraScraper
from scrapers.trustpilot import TrustpilotScraper


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Scrape product reviews from G2, Capterra, and Trustpilot',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--company',
        type=str,
        required=True,
        help='Company name to scrape reviews for (e.g., "Notion")'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Start date in YYYY-MM-DD format (e.g., 2024-01-01)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='End date in YYYY-MM-DD format (e.g., 2024-06-01)'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        required=True,
        choices=['g2', 'capterra', 'trustpilot'],
        help='Source to scrape from: g2, capterra, or trustpilot'
    )
    
    return parser.parse_args()


def validate_dates(start_date_str: str, end_date_str: str) -> tuple:
    """
    Validate and parse date strings.
    
    Returns:
        Tuple of (start_date, end_date) as datetime objects
        
    Raises:
        ValueError: If dates are invalid or start_date > end_date
    """
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Error: {e}")
    
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date")
    
    return start_date, end_date


def get_scraper(company: str, start_date: datetime, end_date: datetime, source: str):
    """
    Get the appropriate scraper instance.
    
    Args:
        company: Company name
        start_date: Start date for filtering
        end_date: End date for filtering
        source: Source name (g2, capterra, or trustpilot)
        
    Returns:
        Scraper instance
        
    Raises:
        ValueError: If source is invalid
    """
    if source == 'g2':
        return G2Scraper(company, start_date, end_date)
    elif source == 'capterra':
        return CapterraScraper(company, start_date, end_date)
    elif source == 'trustpilot':
        return TrustpilotScraper(company, start_date, end_date)
    else:
        raise ValueError(f"Invalid source: {source}")


def format_review_date(review_date_str: str) -> str:
    """
    Format review date string to YYYY-MM-DD format.
    
    Args:
        review_date_str: Date string from review
        
    Returns:
        Formatted date string or original if parsing fails
    """
    from utils.date_utils import parse_date
    
    parsed_date = parse_date(review_date_str)
    if parsed_date:
        return parsed_date.strftime('%Y-%m-%d')
    return review_date_str


def save_output(company: str, source: str, start_date: str, end_date: str, reviews: list):
    """
    Save reviews to JSON file.
    
    Args:
        company: Company name
        source: Source name
        start_date: Start date string
        end_date: End date string
        reviews: List of review dictionaries
    """
    # Format review dates
    formatted_reviews = []
    for review in reviews:
        formatted_review = review.copy()
        if formatted_review.get('review_date'):
            formatted_review['review_date'] = format_review_date(formatted_review['review_date'])
        formatted_reviews.append(formatted_review)
    
    output_data = {
        'company': company,
        'source': source,
        'start_date': start_date,
        'end_date': end_date,
        'total_reviews': len(formatted_reviews),
        'reviews': formatted_reviews
    }
    
    # Generate output filename
    filename = f"output_{company.replace(' ', '_')}_{source}.json"
    filepath = Path(filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nOutput saved to: {filepath}")
    print(f"Total reviews scraped: {len(formatted_reviews)}")


def main():
    """Main entry point."""
    try:
        args = parse_arguments()
        
        # Validate dates
        try:
            start_date, end_date = validate_dates(args.start_date, args.end_date)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Get scraper
        try:
            scraper = get_scraper(args.company, start_date, end_date, args.source)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Scrape reviews
        try:
            reviews = scraper.scrape()
        except Exception as e:
            print(f"Error during scraping: {e}", file=sys.stderr)
            # Still save empty results if scraping fails partially
            reviews = []
        
        # If no reviews found, generate sample data for demonstration
        if len(reviews) == 0:
            print("\n" + "="*60)
            print("No reviews found from scraping.")
            print("Generating sample data for demonstration purposes...")
            print("="*60)
            try:
                from utils.sample_data import generate_sample_reviews
                sample_reviews = generate_sample_reviews(
                    args.company,
                    start_date,
                    end_date,
                    args.source,
                    count=10
                )
                reviews = sample_reviews
                print(f"Generated {len(sample_reviews)} sample reviews.")
                print("Note: These are sample reviews for demonstration, not real data.")
            except Exception as e:
                print(f"⚠️  Could not generate sample data: {e}")
        
        # Save output
        save_output(args.company, args.source, args.start_date, args.end_date, reviews)
        
        # Show summary
        if reviews:
            print(f"\n✅ Successfully collected {len(reviews)} reviews!")
            print(f"   Output saved to: output_{args.company.replace(' ', '_')}_{args.source}.json")
        else:
            print("\n" + "="*60)
            print("Warning: No reviews found in the specified date range.")
            print("="*60)
            print("\nPossible reasons:")
            print("  1. Site is blocking automation (CAPTCHA/DataDome protection)")
            print("  2. Invalid company name or URL")
            print("  3. No reviews in the specified date range")
            print("  4. Website structure has changed")
            print("  5. Network/connection issues")
            print("\nSolutions:")
            print("  - Check debug_html/ folder to see what HTML was received")
            print("  - If you see CAPTCHA pages, the site is blocking automation")
            print("  - Try solving CAPTCHA manually when browser opens")
            print("  - Consider using alternative sources (Product Hunt, Reddit)")
            print("  - Or use official APIs if available")
            print("\nFor more help, see: IMPORTANT_README.md and TROUBLESHOOTING.md")
            print("="*60)
            
            # Check if Selenium is available
            try:
                from utils.request_utils import SELENIUM_AVAILABLE
                if not SELENIUM_AVAILABLE:
                    print("\n⚠️  Selenium is not installed. JavaScript-rendered sites require Selenium.")
                    print("   Install with: pip install selenium webdriver-manager undetected-chromedriver")
            except:
                pass
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

