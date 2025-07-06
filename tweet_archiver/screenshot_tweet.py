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
from PIL import Image

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
    
    # Disable GPU acceleration to avoid issues
    chrome_options.add_argument('--disable-gpu')
    
    if headless:
        chrome_options.add_argument('--headless')
    
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

def take_tweet_screenshot(tweet_id, output_dir='screenshots', headless=True):
    """
    Take a screenshot of a tweet and its entire conversation thread.
    
    Args:
        tweet_id (str): The ID of the tweet to capture
        output_dir (str): Directory to save screenshots. Defaults to 'screenshots'.
        headless (bool): Whether to run the browser in headless mode. Defaults to True.
        
    Returns:
        bool: True if screenshot was successful, False otherwise
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Construct tweet URL
    url = f'https://x.com/i/web/status/{tweet_id}'
    
    driver = None
    try:
        # Set up the WebDriver
        driver = setup_driver(headless=headless)
        
        # Load cookies for authentication
        cookies = load_cookies()
        driver.get('https://x.com')
        add_cookies(driver, cookies)
        
        print(f"Opening tweet: {url}")
        driver.get(url)
        
        # Wait for the conversation to load
        try:
            # Wait for the conversation container
            conversation_container = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'div[data-testid="cellInnerDiv"]'
                ))
            )
            
            # Wait for all tweets in the conversation to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((
                    By.CSS_SELECTOR,
                    'article[data-testid="tweet"]'
                ))
            )
            
            # Handle translation if needed (for the main tweet)
            try:
                # Try to find and click "Translate post" button if it exists
                translate_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        '//span[text()="Translate post"]/ancestor::div[contains(@role, "button")] | '  # Try with div role="button"
                        '//span[text()="Translate post"]/ancestor::button'  # Or with actual button element
                    ))
                )
                print("Found and clicking 'Translate post' button...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", translate_button)
                time.sleep(0.5)
                translate_button.click()
                
                # Wait for translation to complete
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        '//span[contains(text(), "Translated from")]'
                    ))
                )
                
                # Remove translation feedback element if it exists
                try:
                    feedback_xpath = '//span[contains(text(), "Rate this translation")]/ancestor::div[1]'
                    feedback_element = driver.find_element(By.XPATH, feedback_xpath)
                    driver.execute_script("arguments[0].remove();", feedback_element)
                    print("Removed translation feedback element")
                except Exception as e:
                    print(f"Could not find/remove feedback element: {e}")
                
            except (TimeoutException, Exception) as e:
                # If no translate button or any other error, just continue
                pass
            
            # Add a small delay to ensure everything is rendered
            time.sleep(1)
            
            # Find the conversation container and set its height
            try:
                # Scroll to the very top of the page first
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)  # Small delay for the scroll to complete
                    
                # Find the conversation timeline and get its first child with position: relative
                conversation = WebDriverWait(driver, 10).until(
                    lambda d: d.find_element(
                        By.CSS_SELECTOR, 
                        'div[aria-label="Timeline: Conversation"] > div[style*="position: relative"]'
                    )
                )
                
                # const conversation = document.querySelector('div[aria-label="Timeline: Conversation"] > div[style*="position: relative"]');
                # Calculate and set the appropriate height
                height_script = """
                const replyElement = document.querySelector('[data-testid=inline_reply_offscreen]') || document.querySelector('[aria-live=polite][role=status]');
                let height = replyElement ? (replyElement.getBoundingClientRect().top - 53) + 'px' : document.body.scrollHeight + 'px';
                arguments[0].style.minHeight = height;
                return arguments[0].getBoundingClientRect().height;
                """
                
                # Execute the script and get the calculated height
                calculated_height = driver.execute_script(height_script, conversation)
                print(f"Set conversation height to: {calculated_height}px")
                
                # Small delay to ensure the height is applied
                time.sleep(5)
                
                # Take screenshot of the conversation container
                # Crop the screenshot to the determined height
                screenshot_path = os.path.join(output_dir, f'{tweet_id}.png')
                conversation.screenshot(screenshot_path)

                print("Cropping screenshot...")
                image = Image.open(screenshot_path)
                width, height = image.size
                cropped_image = image.crop((0, 0, width, calculated_height))
                cropped_image.save(screenshot_path)
                return True
                
            except Exception as e:
                print(f"Error capturing conversation: {e}")
                # Fallback to the original method if the new approach fails
                driver.execute_script("arguments[0].scrollIntoView(true);", conversation_container)
                time.sleep(0.5)
                screenshot_path = os.path.join(output_dir, f'{tweet_id}.png')
                conversation_container.screenshot(screenshot_path)
                return True
        
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False
        
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
        output_path = os.path.join(output_dir, f'{tweet_id}.png')
        
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
