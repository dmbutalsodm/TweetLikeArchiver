"""
Tweet Archiver

This script archives tweets by:
1. Taking a screenshot of the tweet
2. Downloading any media from the tweet
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import Optional, Tuple

# Import local modules
from tweet_archiver.screenshot_tweet import take_tweet_screenshot
from tweet_archiver.download_tweet_media import download_tweet_media

def extract_tweet_id(url_or_id: str) -> str:
    """Extract tweet ID from URL or return as is if it's already an ID."""
    # If it's already just digits, assume it's a tweet ID
    if url_or_id.isdigit():
        return url_or_id
    
    # Try to extract from Twitter/X URL
    patterns = [
        r'twitter\.com/[^/]+/status/(\d+)',  # Standard URL
        r'x\.com/[^/]+/status/(\d+)',         # x.com URL
        r'status/(\d+)',                        # Shortened URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # If no match found, assume it's a tweet ID
    return url_or_id

def get_tweet_url(tweet_id: str, username: Optional[str] = None) -> str:
    """Construct the tweet URL from ID and optional username."""
    if username:
        return f"https://x.com/{username}/status/{tweet_id}"
    return f"https://x.com/i/web/status/{tweet_id}"

def archive_tweet(identifier: str, output_dir: str = 'archive') -> Tuple[bool, str]:
    """
    Archive a tweet by taking a screenshot and downloading its media.
    
    Args:
        identifier (str): Tweet URL or ID
        output_dir (str): Base directory to save the archive
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Extract tweet ID and create output directories
        tweet_id = extract_tweet_id(identifier)
        tweet_url = get_tweet_url(tweet_id)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Archiving tweet {tweet_id}...")
        
        # Take screenshot
        print("Taking screenshot...")
        try:
            screenshot_success = take_tweet_screenshot(tweet_id, output_dir, headless=True)
        except Exception as e:
            print(f"Error taking screenshot: {str(e)}")
            screenshot_success = False
        
        # Download media
        print("Downloading media...")
        media_success = download_tweet_media(tweet_url, output_dir)
        
        # Prepare result message
        messages = []
        if screenshot_success:
            messages.append("Screenshot completed successfully")
        if media_success:
            messages.append("Media download completed successfully")
        
        if not messages:
            return False, "Failed to archive tweet (screenshot and media download failed)"
            
        return True, ", ".join(messages)
        
    except Exception as e:
        return False, f"Error archiving tweet: {str(e)}"

def main():
    """Command-line interface for the script."""
    parser = argparse.ArgumentParser(description='Archive a tweet by taking a screenshot and downloading its media.')
    parser.add_argument('tweet', help='Tweet URL or ID')
    parser.add_argument('-o', '--output', default='archive', help='Output directory (default: archive)')
    
    args = parser.parse_args()
    
    success, message = archive_tweet(args.tweet, args.output)
    
    if success:
        print(f"Success: {message}")
        sys.exit(0)
    else:
        print(f"Error: {message}")
        sys.exit(1)

if __name__ == "__main__":
    main()
