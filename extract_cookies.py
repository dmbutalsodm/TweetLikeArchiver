"""
Twitter cookie extractor using Selenium.
Automatically logs in using credentials from .env file if available,
otherwise falls back to manual login.
"""
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def auto_login(driver):
    """Attempt to log in automatically using credentials from .env"""
    try:
        print("Attempting automatic login...")
        
        # Wait for email/username field and enter credentials
        email = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'text'))
        )
        print("Entering username...")
        email.send_keys(os.getenv('TWITTER_USERNAME'))
        
        # Click next button
        next_buttons = driver.find_elements(By.XPATH, "//span[text()='Next']")
        if next_buttons:
            next_buttons[0].click()
        
        # Wait for password field and enter password
        password = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'password'))
        )
        print("Entering password...")
        password.send_keys(os.getenv('TWITTER_PASSWORD'))
        
        # Click login button
        login_buttons = driver.find_elements(By.XPATH, "//span[text()='Log in']")
        if login_buttons:
            login_buttons[0].click()
        
        # Wait for login to complete (check for home timeline)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Home timeline"]'))
        )
        
        print("Successfully logged in!")
        return True
        
    except TimeoutException:
        print("Automatic login failed, falling back to manual login")
        return False
    except Exception as e:
        print(f"Error during automatic login: {e}")
        return False

def setup_driver():
    """Set up and return a Chrome WebDriver in headless mode."""
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Use Chrome's built-in WebDriver with headless options
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error starting Chrome: {e}")
        print("\nMake sure you have Chrome installed and chromedriver in your PATH")
        return None

def get_twitter_cookies(driver):
    """Extract Twitter authentication cookies after login."""
    print("Navigating to Twitter login page...")
    driver.get("https://x.com/i/flow/login")
    
    # Try automatic login if credentials are available
    if os.getenv('TWITTER_USERNAME') and os.getenv('TWITTER_PASSWORD'):
        if not auto_login(driver):
            print("Please log in manually in the browser window...")
            input("Press Enter after you've successfully logged in to Twitter...")
    else:
        print("No credentials found in .env file")
        print("Please create a .env file with TWITTER_USERNAME and TWITTER_PASSWORD")
        print("Or log in manually in the browser window...")
        input("Press Enter after you've successfully logged in to Twitter...")
    
    # Get cookies after login
    cookies = driver.get_cookies()
    twitter_cookies = {}
    
    for cookie in cookies:
        if cookie['name'] in ('auth_token', 'ct0'):
            twitter_cookies[cookie['name']] = cookie['value']
    
    return twitter_cookies if twitter_cookies else None

def save_cookies(cookies, filename='cookies.json'):
    """Save cookies to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"\nCookies saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving cookies: {e}")
        return False

def main():
    print("Starting Twitter cookie extraction...")
    driver = setup_driver()
    
    try:
        # Open Twitter login page
        driver.get("https://x.com/i/flow/login")
        
        # Get cookies after user logs in
        cookies = get_twitter_cookies(driver)
        
        if not cookies:
            print("No Twitter authentication cookies found. Did you log in?")
            return
        
        print("Extracted Twitter cookies:")
        for name, value in cookies.items():
            print(f"{name}: {value[:10]}...")
        
        save_cookies(cookies)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
