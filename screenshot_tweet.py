"""
Tweet Screenshot Tool

This script takes a tweet ID and saves a screenshot of it using Selenium with authenticated cookies.
"""
import json
import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def load_cookies(cookie_file='cookies.json'):
    """
    Load cookies from a file or extract fresh ones if needed.
    
    Args:
        cookie_file (str): Path to save/load cookies
        
    Returns:
        dict: Dictionary containing Twitter authentication cookies
    """
    # First try to load from file
    try:
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
            print(f"Loaded cookies from {cookie_file}")
            return cookies
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Could not load cookies from {cookie_file}, extracting fresh cookies...")
        
    # If loading from file fails, extract fresh cookies
    from extract_cookies import setup_driver, get_twitter_cookies, save_cookies
    
    driver = setup_driver()
    if not driver:
        print("Failed to initialize WebDriver")
        return None
        
    try:
        cookies = get_twitter_cookies(driver)
        if cookies:
            save_cookies(cookies, cookie_file)
            return cookies
        return None
    except Exception as e:
        print(f"Error extracting cookies: {e}")
        return None
    finally:
        driver.quit()

def setup_driver(headless=True):
    """Set up and return a Chrome WebDriver with options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1200,12000')
    chrome_options.add_argument('--disable-notifications')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error starting Chrome: {e}")
        print("\nMake sure you have Chrome installed and chromedriver in your PATH")
        return None

def add_cookies(driver, cookies):
    """Add cookies to the WebDriver."""
    # First navigate to the domain to set cookies
    driver.get('https://x.com')
    
    # Delete all existing cookies first
    driver.delete_all_cookies()
    
    # Add each cookie from our saved cookies
    for name, value in cookies.items():
        driver.add_cookie({
            'name': name,
            'value': value,
            'domain': '.x.com'  # Important: must match the domain
        })

def wait_for_images_to_load(driver, element, timeout=10):
    """Wait for all images within an element to load."""
    print("Waiting for images to load...")
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: all(img.get_attribute('complete') == 'true' 
                        for img in element.find_elements(By.TAG_NAME, 'img')
                        if 'http' in (img.get_attribute('src') or ''))
        )
        return True
    except Exception as e:
        print(f"Warning: Some images might not have loaded: {e}")
        return False

def take_tweet_screenshot(driver, tweet_id, output_dir='screenshots'):
    """Take a screenshot of a tweet by its ID, waiting for all content to load."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Construct tweet URL
    url = f'https://x.com/i/web/status/{tweet_id}'
    
    try:
        print(f"Opening tweet: {url}")
        driver.get(url)
        
        # Wait for the main tweet content to load
        try:
            # First wait for the tweet container
            tweet_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'article[data-testid="tweet"]'
                ))
            )
            
            # Wait for tweet text to be visible
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tweetText"]'))
            )
            
            # Wait for images to load
            wait_for_images_to_load(driver, tweet_element)
            
            # Try to find and click "Translate post" button if it exists
            try:
                print("Waiting for 'Translate post' button...")
                translate_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        '//span[text()="Translate post"]/ancestor::div[contains(@role, "button")] | '  # Try with div role="button"
                        '//span[text()="Translate post"]/ancestor::button'  # Or with actual button element
                    ))
                )
                # Scroll to the button and click it
                print("Scrolling to and clicking 'Translate post' button...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", translate_button)
                time.sleep(0.5)  # Small delay for any animations
                translate_button.click()
                
                # Wait for translation to complete
                print("Waiting for translation to complete...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        '//span[contains(text(), "Translated from")]'
                    ))
                )
                
                # Remove translation feedback element if it exists
                try:
                    feedback_xpath = '//span[contains(text(), "Was this translation accurate?")]/ancestor::div[1]'
                    feedback_element = driver.find_element(By.XPATH, feedback_xpath)
                    driver.execute_script("arguments[0].remove();", feedback_element)
                    print("Removed translation feedback element")
                except Exception as e:
                    print(f"Could not find/remove feedback element: {e}")
                
                time.sleep(1)  # Additional time for any lazy-loaded content
                
            except (TimeoutException, Exception) as e:
                # If no translate button or any other error, just continue
                pass
            
            # Small delay to ensure everything is rendered
            time.sleep(1)
            
            # Scroll the tweet into view and add some margin at the top
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tweet_element)
            driver.execute_script("window.scrollBy(0, -100);")  # Scroll up a bit to show more context
            
        except TimeoutException as e:
            print(f"Timed out waiting for tweet content to load: {e}")
            return False
        
        # Take screenshot of just the tweet element
        screenshot_path = os.path.join(output_dir, f'tweet_{tweet_id}.png')
        tweet_element.screenshot(screenshot_path)
        return True
        
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return False

def capture_tweet_screenshot(tweet_id, output_dir='screenshots', headless=True, keep_open=False, cookie_file='cookies.json'):
    """
    Capture a screenshot of a tweet programmatically.
    
    Args:
        tweet_id (str): The ID of the tweet to capture
        output_dir (str, optional): Directory to save screenshots. Defaults to 'screenshots'.
        headless (bool, optional): Run browser in headless mode. Defaults to True.
        keep_open (bool, optional): Keep browser open after capture. Defaults to False.
        cookie_file (str, optional): Path to cookie file. Defaults to 'cookies.json'.
    
    Returns:
        tuple: (success: bool, output_path: str)
    """
    # Load cookies
    cookies = load_cookies(cookie_file)
    if not cookies:
        return False, None
    
    # Set up driver
    driver = setup_driver(headless=headless)
    if not driver:
        return False, None
    
    try:
        # Add cookies for authentication
        add_cookies(driver, cookies)
        
        # Take the screenshot
        success = take_tweet_screenshot(driver, tweet_id, output_dir)
        output_path = os.path.join(output_dir, f'tweet_{tweet_id}.png')
        
        if success:
            print(f"Screenshot saved to: {output_path}")
        
        if keep_open and not headless:
            input("Press Enter to close the browser...")
            
        return success, output_path if success else None
        
    except Exception as e:
        print(f"Error in capture_tweet_screenshot: {e}")
        return False, None
    finally:
        if not keep_open:
            driver.quit()

def main():
    """Command-line interface for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Take a screenshot of a tweet.')
    parser.add_argument('tweet_id', help='ID of the tweet to capture')
    parser.add_argument('output_dir', nargs='?', default='screenshots',
                       help='Directory to save the screenshot (default: screenshots/)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                       help='Run browser in non-headless mode')
    parser.add_argument('--keep-open', action='store_true',
                       help='Keep browser open after capture')
    parser.add_argument('--cookie-file', default='cookies.json',
                       help='Path to cookie file (default: cookies.json)')
    
    args = parser.parse_args()
    
    success, _ = capture_tweet_screenshot(
        tweet_id=args.tweet_id,
        output_dir=args.output_dir,
        headless=args.headless,
        keep_open=args.keep_open,
        cookie_file=args.cookie_file
    )
    
    if success:
        print("Screenshot completed successfully!")
    else:
        print("Failed to take screenshot.")
        sys.exit(1)

if __name__ == "__main__":
    main()
