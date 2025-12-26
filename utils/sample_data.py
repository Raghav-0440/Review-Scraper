"""Generate sample review data for demonstration purposes."""

import random
from datetime import datetime, timedelta
from typing import List, Dict


def generate_sample_reviews(company: str, start_date: datetime, end_date: datetime, source: str, count: int = 10) -> List[Dict]:
    """
    Generate sample review data for demonstration.
    
    Args:
        company: Company name
        start_date: Start date for reviews
        end_date: End date for reviews
        source: Source name (g2, capterra, trustpilot)
        count: Number of reviews to generate
        
    Returns:
        List of review dictionaries
    """
    reviews = []
    
    # Sample review templates
    positive_templates = [
        "Great product! {company} has really helped our team improve productivity.",
        "Excellent tool. We've been using {company} for months and love it.",
        "Highly recommend {company}. It's user-friendly and powerful.",
        "Best decision we made. {company} transformed our workflow.",
        "Outstanding service. {company} exceeded our expectations.",
        "Love using {company}! It's intuitive and feature-rich.",
        "Perfect solution for our needs. {company} is fantastic.",
        "Great value for money. {company} delivers on all fronts.",
        "Impressive features. {company} has everything we need.",
        "Top-notch product. {company} is reliable and efficient.",
    ]
    
    neutral_templates = [
        "Decent product. {company} works well but could use some improvements.",
        "Good overall, but {company} has a learning curve.",
        "Solid tool. {company} meets most of our requirements.",
        "Not bad. {company} does the job but isn't perfect.",
        "Average experience with {company}. It's functional.",
        "Okay product. {company} works but could be better.",
        "Fair tool. {company} has pros and cons.",
        "Decent solution. {company} is adequate for our needs.",
    ]
    
    negative_templates = [
        "Could be better. {company} lacks some key features we need.",
        "Not impressed. {company} doesn't meet our expectations.",
        "Needs improvement. {company} has some usability issues.",
        "Disappointing. {company} didn't work as advertised.",
    ]
    
    titles = [
        "Great tool for teams",
        "Solid product",
        "Highly recommended",
        "Good value",
        "Works well",
        "Easy to use",
        "Feature-rich",
        "Reliable solution",
        "User-friendly",
        "Powerful features",
    ]
    
    reviewer_names = [
        "John Smith", "Sarah Johnson", "Michael Chen", "Emily Rodriguez",
        "David Williams", "Lisa Anderson", "Robert Taylor", "Jennifer Brown",
        "James Wilson", "Maria Garcia", "William Martinez", "Patricia Davis",
        "Richard Miller", "Linda Moore", "Joseph Jackson", "Barbara White",
    ]
    
    # Calculate date range
    days_range = (end_date - start_date).days
    if days_range < 1:
        days_range = 365  # Default to 1 year
    
    for i in range(count):
        # Random date within range
        random_days = random.randint(0, days_range)
        review_date = start_date + timedelta(days=random_days)
        
        # Choose template based on rating (more positive reviews)
        rating = random.choices(
            [5, 4, 3, 2, 1],
            weights=[40, 30, 15, 10, 5]  # More positive reviews
        )[0]
        
        if rating >= 4:
            template = random.choice(positive_templates)
        elif rating == 3:
            template = random.choice(neutral_templates)
        else:
            template = random.choice(negative_templates)
        
        review_text = template.format(company=company)
        
        # Add some variation
        if random.random() > 0.5:
            review_text += " The interface is clean and modern."
        if random.random() > 0.7:
            review_text += " Customer support is responsive."
        if random.random() > 0.6:
            review_text += " Pricing is reasonable for what you get."
        
        review = {
            'title': random.choice(titles),
            'review_text': review_text,
            'review_date': review_date.strftime('%Y-%m-%d'),
            'reviewer': random.choice(reviewer_names),
            'rating': str(rating),
            'source': source
        }
        
        reviews.append(review)
    
    # Sort by date (newest first)
    reviews.sort(key=lambda x: x['review_date'], reverse=True)
    
    return reviews

