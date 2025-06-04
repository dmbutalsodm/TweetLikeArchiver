import os
import json
import time
import re
import sys
from typing import List, Set, OrderedDict
from pathlib import Path
from collections import OrderedDict

# Add the parent directory to sys.path to import from project root
sys.path.append(str(Path(__file__).parent.parent))

# Import the cookie and driver setup functions from existing files
from extract_cookies import get_twitter_cookies, save_cookies
from tweet_archiver.screenshot_tweet import setup_driver

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TwitterScraper:
    """Scrape Twitter/X to retrieve liked tweets using Selenium."""
    
    def __init__(self, cookies_file: str = 'cookies.json'):
        """Initialize the Twitter scraper with cookies for authentication."""
        self.cookies_file = cookies_file
        self.base_url = "https://x.com"
        self.driver = None
        self.tweet_ids = OrderedDict()  # Use OrderedDict to maintain insertion order
    
    def setup_browser(self, headless=False):
        """Set up the Chrome WebDriver with options."""
        print("Setting up Chrome WebDriver...")
        # Use our existing setup_driver function, but override headless if needed
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument('--headless')
        
        # Add options to make browser less detectable
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")  # Larger window size for better visibility
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent to appear more like a real browser
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        
        # Initialize Chrome WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Set a reasonable page load timeout
        self.driver.set_page_load_timeout(30)
        
        # Navigate to Twitter before adding cookies
        self.driver.get(self.base_url)
        
    def add_cookies_to_browser(self, cookies):
        """Add cookies to the browser for authentication."""
        print("Adding authentication cookies to browser...")
        
        # Handle different cookie formats - it could be a dict or a list of dicts
        if isinstance(cookies, dict):
            # Format from extract_cookies.py - dict with name:value pairs
            for name, value in cookies.items():
                self.driver.add_cookie({
                    'name': name,
                    'value': value,
                    'domain': '.x.com',
                    'path': '/',
                    'secure': True
                })
        elif isinstance(cookies, list):
            # Format with full cookie objects
            for cookie in cookies:
                try:
                    self.driver.add_cookie({
                        'name': cookie.get('name'),
                        'value': cookie.get('value'),
                        'domain': cookie.get('domain', '.twitter.com'),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', True)
                    })
                except Exception as e:
                    print(f"Error adding cookie {cookie.get('name')}: {str(e)}")
    
    def navigate_to_likes_page(self, username: str = None):
        """Navigate to the likes page. If username is not provided, it will go to the logged-in user's likes."""
        # First, refresh the page to apply cookies
        self.driver.refresh()
        time.sleep(2)
        
        if username:
            likes_url = f"{self.base_url}/{username}/likes"
        else:
            # Go to home first to make sure we're logged in
            print("Going to home page to verify login...")
            self.driver.get(self.base_url + "/home")
            time.sleep(3)  # Give it time to load
            
            # Wait for the page to load and try to find the logged-in username
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-testid="AppTabBar_Profile_Link"]'))
                )
                profile_link = self.driver.find_element(By.CSS_SELECTOR, 'a[data-testid="AppTabBar_Profile_Link"]')
                username = profile_link.get_attribute('href').split('/')[-1]
                likes_url = f"{self.base_url}/{username}/likes"
                print(f"Detected username: {username}")
            except (TimeoutException, NoSuchElementException):
                # If we can't find the username, try to navigate to likes through the UI
                print("Could not determine username, attempting to navigate to likes through UI...")
                try:
                    profile_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-testid="AppTabBar_Profile_Link"]')
                    profile_button.click()
                    time.sleep(3)
                    
                    # Find and click the likes tab
                    likes_tab = self.driver.find_element(By.XPATH, "//span[text()='Likes']")
                    likes_tab.click()
                    time.sleep(3)
                    
                    # Get the current URL as the likes URL
                    likes_url = self.driver.current_url
                except Exception as e:
                    print(f"Error navigating to likes: {str(e)}")
                    likes_url = self.base_url + "/i/likes"
        
        print(f"Navigating to likes page: {likes_url}")
        self.driver.get(likes_url)
        
        # Wait for the likes page to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
            )
            print("Likes page loaded successfully!")
        except TimeoutException:
            print("Warning: Could not detect tweets on the likes page. Page might not have loaded properly.")
    
    def extract_tweet_ids(self) -> Set[str]:
        """Extract tweet IDs from the currently loaded tweets."""
        new_ids = set()
        
        # Find all tweet articles
        tweets = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        
        for tweet in tweets:
            try:
                # Get the tweet's permalink
                links = tweet.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
                
                for link in links:
                    href = link.get_attribute('href')
                    # Extract the tweet ID using regex
                    match = re.search(r'/status/(\d+)', href)
                    if match:
                        tweet_id = match.group(1)
                        if tweet_id not in self.tweet_ids:
                            new_ids.add(tweet_id)
                            self.tweet_ids[tweet_id] = None  # Using OrderedDict to maintain order
            except Exception as e:
                print(f"Error extracting tweet ID: {str(e)}")
        
        return new_ids
    
    def scroll_and_extract(self, max_scrolls: int = None):
        """Scroll through the page and extract tweet IDs."""
        # Initial scroll position
        self.driver.execute_script("window.scrollTo(0, 0);")
        
        # Extract tweet IDs from the initial view
        new_ids = self.extract_tweet_ids()
        previous_ids_count = len(self.tweet_ids)
        
        print("Starting to scroll and extract tweet IDs...")
        
        scroll_count = 0
        scroll_pause_time = 3  # Longer pause between scrolls to allow rendering
        viewport_height = self.driver.execute_script("return window.innerHeight")
        total_scroll_position = 0
        no_new_tweets_count = 0
        
        while max_scrolls is None or scroll_count < max_scrolls:
            # Scroll down 1x viewport height each time for more gradual scrolling
            scroll_amount = viewport_height 
            total_scroll_position += scroll_amount
            
            # Scroll to the new position
            self.driver.execute_script(f"window.scrollTo(0, {total_scroll_position});")
            
            # Wait for the page to load and render new content
            time.sleep(scroll_pause_time)
            
            # Extract tweet IDs from the new content
            new_ids = self.extract_tweet_ids()
            # Add new IDs to the ordered dict
            for tweet_id in new_ids:
                self.tweet_ids[tweet_id] = None
            
            # Check if we found new tweets
            current_count = len(self.tweet_ids)
            if current_count > previous_ids_count:
                # Reset the counter if we found new tweets
                no_new_tweets_count = 0
                print(f"Scroll #{scroll_count+1}: Found {current_count - previous_ids_count} new tweets (Total: {current_count})")
                previous_ids_count = current_count
                
                # Save more frequently
                if current_count % 20 == 0:
                    self.save_tweet_ids()
            else:
                # Keep track of how many scrolls with no new tweets
                no_new_tweets_count += 1
                print(f"Scroll #{scroll_count+1}: No new tweets found (still at {current_count})")
                
                # If we've scrolled 5 times with no new tweets, try scrolling a bit more
                if no_new_tweets_count >= 5:
                    print("No new tweets for several scrolls, jumping ahead...")
                    jump_amount = viewport_height * 2
                    total_scroll_position += jump_amount
                    self.driver.execute_script(f"window.scrollTo(0, {total_scroll_position});")
                    time.sleep(scroll_pause_time * 1.5)  # Wait a bit longer after a jump
                    no_new_tweets_count = 0  # Reset the counter
            
            # Check if we're at the bottom of the page
            current_position = self.driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop;")
            total_height = self.driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
            
            # If we're close to the bottom, wait for more content to load
            if (total_height - current_position - viewport_height) < 200:
                print("Near the bottom of the page, waiting for more content to load...")
                time.sleep(scroll_pause_time * 2)
                
                # Calculate new total height
                new_total_height = self.driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
                
                # Check if the height has increased (meaning more content loaded)
                if new_total_height <= total_height:
                    # Try a refresh if we're at the bottom and no new content is loading
                    if no_new_tweets_count >= 10:
                        print("No new content loading. Refreshing the page...")
                        current_url = self.driver.current_url
                        self.driver.refresh()
                        time.sleep(5)  # Wait for the page to fully refresh
                        total_scroll_position = 0  # Reset scroll position
                        no_new_tweets_count = 0  # Reset counter
                    elif no_new_tweets_count >= 15:
                        print("Reached the end of the likes feed or no new content is loading.")
                        break
            
            scroll_count += 1
            
            # Save progress more frequently
            if scroll_count % 5 == 0:
                self.save_tweet_ids()
        
        # Final save
        self.save_tweet_ids()
        print(f"Finished scrolling. Found {len(self.tweet_ids)} total liked tweets.")
    
    def save_tweet_ids(self, filename: str = 'liked_tweet_ids.txt'):
        """Save the collected tweet IDs to a file in the order they were scraped."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for tweet_id in self.tweet_ids.keys():  # Maintains insertion order
                    f.write(f"{tweet_id}\n")
            print(f"Saved {len(self.tweet_ids)} tweet IDs to {filename}")
        except Exception as e:
            print(f"Error saving tweet IDs to file: {str(e)}")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")
    
    def run(self, username: str = None, max_scrolls: int = None, headless: bool = False):
        """Run the full scraping process."""
        try:
            # Load cookies from file or extract them
            cookies = None
            try:
                # Check if the file exists first
                if not os.path.exists(self.cookies_file):
                    print(f"Cookie file {self.cookies_file} not found")
                    print("Running extract_cookies.py to generate cookies file...")
                    # Get a new driver to extract cookies
                    driver = setup_driver(headless=False)  # Need visible browser for manual login
                    if driver:
                        try:
                            cookies = get_twitter_cookies(driver)
                            if cookies:
                                save_cookies(cookies, self.cookies_file)
                        finally:
                            driver.quit()
                else:
                    # Load cookies from file
                    with open(self.cookies_file, 'r') as f:
                        cookies = json.load(f)
                    print(f"Loaded cookies from {self.cookies_file}")
                    
                if not cookies:
                    print("Failed to get authentication cookies")
                    return []
                    
            except (FileNotFoundError, json.JSONDecodeError):
                print(f"Could not load cookies from {self.cookies_file}")
                print("You need to create a cookies.json file with Twitter authentication cookies.")
                print("You can run 'python extract_cookies.py' to generate this file.")
                return []
            
            # Set up the browser
            self.setup_browser(headless=headless)
            time.sleep(2)  # Give the browser a moment to initialize
            
            if cookies:
                # Add cookies and navigate
                self.add_cookies_to_browser(cookies)
                self.navigate_to_likes_page(username)
            else:
                print("No valid cookies found. Cannot proceed without authentication.")
                return []
            
            # Perform the scrolling and extraction
            self.scroll_and_extract(max_scrolls)
            
            # Return the collected tweet IDs
            return list(self.tweet_ids)
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return list(self.tweet_ids)  # Return any IDs we collected before the error
        finally:
            self.close()


def main():
    """Main function to run the Twitter scraper."""
    try:
        print("Twitter Likes Scraper")
        print("====================\n")
        
        # Set path to cookies file in project root
        cookies_file = Path(__file__).parent.parent / 'cookies.json'
        # We'll check for the file in the run method and create it if needed
        
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description='Scrape Twitter/X liked tweets and save their IDs.')
        parser.add_argument('--username', help='Twitter username whose likes you want to scrape (default: logged-in user)')
        parser.add_argument('--max-scrolls', type=int, help='Maximum number of scrolls (default: unlimited)')
        parser.add_argument('--no-headless', action='store_true', help='Run in visible browser mode')
        parser.add_argument('--output', default='liked_tweet_ids.txt', help='Output file for tweet IDs (default: liked_tweet_ids.txt)')
        
        args = parser.parse_args()
        
        # Create and run the scraper
        username = args.username  # None means the logged-in user
        max_scrolls = args.max_scrolls  # None means unlimited scrolling
        headless = not args.no_headless  # By default, run in headless mode
        output_file = args.output
        
        print(f"Starting to scrape liked tweets{'.' if username is None else f' for {username}.'}")
        print(f"Tweet IDs will be saved to '{output_file}'")
        print("Press Ctrl+C at any time to stop and save current progress.\n")
        
        scraper = TwitterScraper(str(cookies_file))
        liked_tweet_ids = scraper.run(username, max_scrolls, headless)
        
        if liked_tweet_ids:
            print(f"\nSuccessfully scraped {len(liked_tweet_ids)} liked tweets.")
            print(f"All tweet IDs have been saved to '{output_file}'")
        else:
            print("\nNo liked tweets were found or there was an error during scraping.")
            print("Please check if you're logged in correctly or if Twitter's page structure has changed.")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Saving current progress...")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()