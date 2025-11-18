#!/usr/bin/env python3
"""
Wikipedia utility functions for article downloading and processing.

This module handles:
- Wikipedia article downloading via wikipediaapi
- Article text extraction and cleaning
- Batch downloading with progress tracking
"""

import time
import wikipediaapi
from typing import List, Dict, Optional, Any
from pathlib import Path


def create_wikipedia_api():
    """
    Create Wikipedia API client with user agent.

    Returns:
        wikipediaapi.Wikipedia: Wikipedia API client
    """
    return wikipediaapi.Wikipedia(
        user_agent='KnowledgeMap/1.0 (https://github.com/user/mapper.io)',
        language='en'
    )


def download_article(
    title: str,
    wiki: Optional[wikipediaapi.Wikipedia] = None
) -> Optional[Dict[str, Any]]:
    """
    Download a single Wikipedia article.

    Args:
        title: Wikipedia article title
        wiki: Wikipedia API client (created if not provided)

    Returns:
        Dict with 'title', 'text', 'url' keys, or None if article not found

    Example:
        >>> article = download_article("Mitochondria")
        >>> article['title']
        'Mitochondria'
        >>> len(article['text'])
        15234
    """
    if wiki is None:
        wiki = create_wikipedia_api()

    # Get page
    page = wiki.page(title)

    # Check if page exists
    if not page.exists():
        print(f"  ✗ Article not found: {title}")
        return None

    # Extract data
    article = {
        'title': page.title,
        'text': page.text,
        'url': page.fullurl,
        'summary': page.summary
    }

    return article


def download_articles_batch(
    titles: List[str],
    delay: float = 0.1,
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Download multiple Wikipedia articles with rate limiting.

    Args:
        titles: List of Wikipedia article titles
        delay: Delay between requests in seconds (default: 0.1)
        max_retries: Maximum retries per article (default: 3)

    Returns:
        List of article dicts (only successful downloads)

    Example:
        >>> titles = ["Mitochondria", "DNA", "RNA"]
        >>> articles = download_articles_batch(titles)
        >>> len(articles)
        3
    """
    wiki = create_wikipedia_api()
    articles = []

    print(f"Downloading {len(titles)} Wikipedia articles...")
    print()

    for i, title in enumerate(titles, 1):
        # Progress update every 10 articles
        if i % 10 == 0 or i == 1:
            print(f"  Progress: {i}/{len(titles)} ({i/len(titles)*100:.1f}%)")

        # Try downloading with retries
        for attempt in range(max_retries):
            try:
                article = download_article(title, wiki)

                if article:
                    articles.append(article)
                    break  # Success
                else:
                    # Article not found, don't retry
                    break

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠ Error downloading '{title}' (attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(delay * 2)  # Longer delay on error
                else:
                    print(f"  ✗ Failed to download '{title}' after {max_retries} attempts")

        # Rate limiting
        time.sleep(delay)

    print()
    print(f"✓ Downloaded {len(articles)}/{len(titles)} articles ({len(articles)/len(titles)*100:.1f}%)")

    return articles


def extract_article_text(
    article: Dict[str, Any],
    max_length: Optional[int] = None
) -> str:
    """
    Extract and clean article text.

    Args:
        article: Article dict with 'text' key
        max_length: Optional maximum length (truncates if longer)

    Returns:
        Cleaned article text
    """
    text = article.get('text', '')

    # Clean text
    text = text.strip()

    # Remove excessive whitespace
    text = ' '.join(text.split())

    # Truncate if requested
    if max_length and len(text) > max_length:
        text = text[:max_length]
        # Try to end at sentence boundary
        last_period = text.rfind('.')
        if last_period > max_length * 0.8:
            text = text[:last_period + 1]

    return text


def create_excerpt(
    text: str,
    max_length: int = 100
) -> str:
    """
    Create short excerpt from article text.

    Args:
        text: Full article text
        max_length: Maximum excerpt length (default: 100)

    Returns:
        Short excerpt string
    """
    if not text:
        return ""

    # Clean text
    text = ' '.join(text.split())

    # Truncate
    if len(text) <= max_length:
        return text

    # Try to end at sentence boundary
    excerpt = text[:max_length]
    last_period = excerpt.rfind('.')
    last_space = excerpt.rfind(' ')

    if last_period > max_length * 0.7:
        return excerpt[:last_period + 1]
    elif last_space > 0:
        return excerpt[:last_space] + '...'
    else:
        return excerpt + '...'


def validate_articles(
    articles: List[Dict[str, Any]],
    min_text_length: int = 100
) -> List[Dict[str, Any]]:
    """
    Filter articles by quality criteria.

    Args:
        articles: List of article dicts
        min_text_length: Minimum text length to keep (default: 100)

    Returns:
        Filtered list of articles
    """
    valid_articles = []

    for article in articles:
        # Check required fields
        if not all(k in article for k in ['title', 'text', 'url']):
            continue

        # Check text length
        if len(article['text']) < min_text_length:
            continue

        valid_articles.append(article)

    if len(valid_articles) < len(articles):
        removed = len(articles) - len(valid_articles)
        print(f"  Filtered out {removed} articles (min length: {min_text_length} chars)")

    return valid_articles
