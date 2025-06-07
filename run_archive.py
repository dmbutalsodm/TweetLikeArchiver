"""
Twitter Like Archiver - Main Entry Point

This script serves as the main entry point for the Twitter Like Archiver.
It coordinates the process of fetching new liked tweets and archiving them.
"""

import sys
import time
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

def fetch_new_likes():
    """Fetch new liked tweets from Twitter."""
    print("\n=== Fetching New Likes ===")
    from like_retriever.fetch_likes import main as fetch_likes_main
    fetch_likes_main()
    print("=== Finished fetching likes ===\n")

def archive_likes():
    """Archive all unarchived liked tweets."""
    print("\n=== Archiving Tweets ===")
    from archive_all_likes import main as archive_main
    archive_main()
    print("=== Finished archiving tweets ===\n")

def main():
    """Main function to run the Twitter Like Archiver."""
    parser = argparse.ArgumentParser(description='Twitter Like Archiver')
    parser.add_argument('--fetch-only', action='store_true', help='Only fetch new likes without archiving')
    parser.add_argument('--archive-only', action='store_true', help='Only archive existing likes without fetching')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    try:
        if not args.archive_only:
            fetch_new_likes()
        
        if not args.fetch_only:
            archive_likes()
            
        if not (args.fetch_only or args.archive_only):
            print("\n=== All Done! ===")
            print(f"Total time: {time.time() - start_time:.2f} seconds")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
