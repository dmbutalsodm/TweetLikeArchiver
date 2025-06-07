import os
import time
from pathlib import Path
from tweet_archiver.archive_tweet import archive_tweet

# Configuration
INPUT_FILE = 'liked_tweet_ids.txt'
STATE_FILE = 'last_archived_id.txt'
DELAY_SECONDS = 5

def get_last_archived_id():
    """Get the last archived tweet ID from the state file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_archived_id(tweet_id):
    """Save the last archived tweet ID to the state file."""
    with open(STATE_FILE, 'w') as f:
        f.write(tweet_id)

def main():
    # Read all tweet IDs from the input file (newest first)
    try:
        with open(INPUT_FILE, 'r') as f:
            tweet_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE}")
        return
    
    if not tweet_ids:
        print("No tweet IDs found in the input file.")
        return
    
    last_archived_id = get_last_archived_id()
    
    if last_archived_id:
        print(f"Resuming from last archived tweet ID: {last_archived_id}")
    else:
        print("No previous archive state found. Starting from the beginning.")
    
    # Process each tweet (newest first)
    new_archives = 0
    
    for i, tweet_id in enumerate(tweet_ids, 1):
        # Stop if we encounter a previously archived tweet
        if last_archived_id and tweet_id == last_archived_id:
            print("\nReached previously archived tweet. Stopping.")
            break
            
        print(f"\nProcessing tweet {i}/{len(tweet_ids)} (ID: {tweet_id})")
        
        # Archive the tweet
        success, message = archive_tweet(tweet_id)
        
        if success:
            print(f"Success: {message}")
            save_last_archived_id(tweet_id)
            new_archives += 1
        else:
            print(f"Failed: {message}")
            # Don't update the last_archived_id on failure
            break
        
        # Add a delay between requests
        if i < len(tweet_ids):
            print(f"Waiting {DELAY_SECONDS} seconds before next request...")
            time.sleep(DELAY_SECONDS)
    
    if new_archives == 0:
        print("\nNo new tweets to archive.")
    else:
        print(f"\nSuccessfully archived {new_archives} new tweets.")

if __name__ == "__main__":
    main()
