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

def get_all_tweets_to_archive():
    """
    Get all tweets that need to be archived, in reverse chronological order.
    
    Returns:
        list: List of tweet IDs to be archived, newest first
    """
    last_archived_id = get_last_archived_id()
    try:
        with open(INPUT_FILE, 'r') as f:
            tweet_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE}")
        return []
    
    tweet_ids = tweet_ids[::-1]

    if not tweet_ids:
        print("No tweet IDs found in the input file.")
        return []
    
    # If no last_archived_id, return all tweets in reverse order (newest first)
    if not last_archived_id:
        return tweet_ids
    
    try:
        # Find the index of the last archived tweet
        last_index = tweet_ids.index(last_archived_id)
        # Return all tweets after the last archived one (since we reversed the list)
        return tweet_ids[last_index+1:]
    except ValueError:
        # If last_archived_id not found, return all tweets
        print(f"Warning: Last archived tweet ID {last_archived_id} not found. Archiving all tweets.")
        return tweet_ids

def main():
    # Get all tweets that need to be archived (newest first)
    tweet_ids = get_all_tweets_to_archive()
    
    if not tweet_ids:
        print("No tweets to archive.")
        return
    
    print(f"Found {len(tweet_ids)} tweets to archive.")
    
    # Process each tweet (newest first)
    new_archives = 0
    
    for i, tweet_id in enumerate(tweet_ids, 1):
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
