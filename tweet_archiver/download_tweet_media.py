"""
Twitter Media Downloader

This module provides functionality to download media from tweets using gallery-dl.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

def download_tweet_media(tweet_url: str, output_dir: Optional[str] = None) -> bool:
    """
    Download media from a tweet using gallery-dl.
    
    Args:
        tweet_url (str): URL of the tweet containing media
        output_dir (str, optional): Directory to save downloaded media. Defaults to 'downloads'.
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Build the gallery-dl command
        cmd = [
            'gallery-dl',
            '--cookies-from-browser', 'firefox',  # Use your browser for cookies
            '--no-mtime',
            '-D', output_dir,
            tweet_url
        ]
        
        # Run the command
        print(f"Downloading media from: {tweet_url}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print("Download completed successfully!")
            return True
        else:
            print(f"Error downloading media: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

def main():
    """Command-line interface for the script."""
    if len(sys.argv) < 2:
        print("Usage: python download_tweet_media.py <tweet_url> [output_dir]")
        sys.exit(1)
    
    tweet_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = download_tweet_media(tweet_url, output_dir)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
