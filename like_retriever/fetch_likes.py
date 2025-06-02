import os
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

class TwitterLikesRetriever:
    """
    A class to retrieve liked tweets for a given Twitter user ID using direct API calls.
    """
    
    def __init__(self):
        """
        Initialize the Twitter API client using credentials from environment variables.
        """
        load_dotenv()  # Load environment variables from .env file
        
        # Get Twitter API credentials from environment variables
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError(
                "Missing required Twitter API credentials. "
                "Please set TWITTER_API_KEY, TWITTER_API_SECRET, "
                "TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET in .env file."
            )
        
        self.base_url = "https://api.twitter.com/2"
        self.auth = OAuth1(
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_token_secret
        )
        self.headers = {
            "Content-Type": "application/json"
        }
    
    def get_liked_tweets(self, user_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve liked tweets for a given user ID.
        
        Args:
            user_id: Twitter user ID (not username)
            max_results: Maximum number of liked tweets to retrieve (default: 100, max: 100)
            
        Returns:
            List of dictionaries containing tweet information
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
            
        max_results = max(5, min(100, max_results))  # Ensure max_results is between 5 and 100
        
        try:
            # First, get the user's liked tweets
            likes_url = f"{self.base_url}/users/{user_id}/liked_tweets"
            params = {
                "max_results": max_results,
                "tweet.fields": "created_at,text,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments",
                "expansions": "author_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id",
                "media.fields": "url,preview_image_url,type",
                "user.fields": "username,name,profile_image_url"
            }
            
            print(f"Making request to: {likes_url}")
            print(f"Headers: {self.headers}")
            
            response = requests.get(likes_url, auth=self.auth, headers=self.headers, params=params, timeout=10)
            
            # Print detailed error information if the request fails
            if response.status_code != 200:
                print(f"Error response: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Response text: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data or not data['data']:
                return []
            
            # Process includes for users and media
            includes = data.get('includes', {})
            users = {user['id']: user for user in includes.get('users', [])}
            media = {m['media_key']: m for m in includes.get('media', [])}
            
            # Format the tweets
            tweets = []
            for tweet in data['data']:
                author = users.get(tweet.get('author_id', ''), {})
                
                # Get media attachments if any
                tweet_media = []
                if 'attachments' in tweet and 'media_keys' in tweet['attachments']:
                    for media_key in tweet['attachments']['media_keys']:
                        if media_key in media:
                            tweet_media.append(media[media_key])
                
                # Format the tweet data
                formatted_tweet = {
                    'id': tweet['id'],
                    'text': tweet.get('text', ''),
                    'created_at': tweet.get('created_at'),
                    'author': {
                        'id': author.get('id'),
                        'username': author.get('username', 'unknown'),
                        'name': author.get('name', 'Unknown User'),
                        'profile_image_url': author.get('profile_image_url')
                    },
                    'public_metrics': tweet.get('public_metrics', {}),
                    'media': tweet_media,
                    'referenced_tweets': [
                        {'type': ref['type'], 'id': ref['id']}
                        for ref in tweet.get('referenced_tweets', [])
                    ]
                }
                tweets.append(formatted_tweet)
            
            return tweets
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}"
            if e.response.status_code == 429:
                error_msg += " - Rate limit exceeded"
            print(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            raise

def main():
    """
    Example usage of the TwitterLikesRetriever class.
    """
    try:
        # Initialize the retriever
        retriever = TwitterLikesRetriever()
        
        # Get user input for Twitter user ID
        user_id = input("Enter Twitter User ID: ").strip()
        
        if not user_id:
            print("Error: User ID cannot be empty")
            return
            
        # Fetch liked tweets
        print(f"Fetching up to 100 most recent liked tweets for user ID: {user_id}")
        liked_tweets = retriever.get_liked_tweets(user_id)
        
        if not liked_tweets:
            print("No liked tweets found or the account has no public likes.")
            return
            
        print(f"\nFound {len(liked_tweets)} liked tweets:")
        print("-" * 80)
        
        # Display the results
        for i, tweet in enumerate(liked_tweets, 1):
            print(f"{i}. {tweet['text'][:150]}{'...' if len(tweet['text']) > 150 else ''}")
            print(f"   By: @{tweet['author']['username']} | {tweet['created_at']}")
            print(f"   Likes: {tweet['public_metrics'].get('like_count', 0)} | "
                  f"Retweets: {tweet['public_metrics'].get('retweet_count', 0)}")
            if tweet['media']:
                print(f"   Contains {len(tweet['media'])} media item(s)")
            if tweet['referenced_tweets']:
                print(f"   References {len(tweet['referenced_tweets'])} other tweet(s)")
            print("-" * 80)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()