"""HTTP request utilities with retry logic and Selenium support."""

import time
import requests
from typing import Optional
from bs4 import BeautifulSoup

# Try to import Selenium, but don't fail if not available
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
    SELENIUM_AVAILABLE = True
    
    # Try to import undetected-chromedriver for better bot evasion
    try:
        import undetected_chromedriver as uc
        UNDETECTED_CHROME_AVAILABLE = True
    except ImportError:
        UNDETECTED_CHROME_AVAILABLE = False
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    UNDETECTED_CHROME_AVAILABLE = False


def fetch_with_retry(url: str, max_retries: int = 3, delay: float = 1.0, headers: dict = None) -> Optional[requests.Response]:
    """
    Fetch a URL with retry logic.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        headers: Optional headers to include in the request
        
    Returns:
        Response object or None if all retries fail
    """
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                print(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                return None
    
    return None


def get_soup_with_selenium(url: str, wait_time: int = 15) -> Optional[BeautifulSoup]:
    """
    Fetch a URL using Selenium (handles JavaScript-rendered content).
    Uses undetected-chromedriver if available for better bot evasion.
    
    Args:
        url: URL to fetch
        wait_time: Time to wait for page to load in seconds
        
    Returns:
        BeautifulSoup object or None if fetch fails
    """
    if not SELENIUM_AVAILABLE:
        print("Selenium not available. Install with: pip install selenium webdriver-manager")
        return None
    
    driver = None
    use_undetected = False
    try:
        # Use undetected-chromedriver if available (better at bypassing bot detection)
        if UNDETECTED_CHROME_AVAILABLE:
            print("Using undetected-chromedriver for better bot evasion...")
            try:
                options = Options()
                options.add_argument('--start-maximized')
                options.add_argument('--disable-blink-features=AutomationControlled')
                # Don't use headless - it's easier to detect
                driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
                use_undetected = True
            except Exception as e:
                print(f"Error initializing undetected-chromedriver: {e}")
                print("Falling back to regular Chrome...")
                use_undetected = False
        
        if not use_undetected:
            # Fallback to regular Selenium with stealth settings
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--start-maximized')
            
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
        
        # Only execute stealth scripts if not using undetected-chromedriver
        if not UNDETECTED_CHROME_AVAILABLE:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.navigator.chrome = {
                        runtime: {}
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                '''
            })
        
        # Navigate to URL
        print(f"Loading page: {url}")
        driver.get(url)
        
        # Initial wait
        time.sleep(5)
        
        # Check if we're on a challenge page (with error handling)
        try:
            page_source = driver.page_source.lower()
            challenge_detected = any(keyword in page_source for keyword in ['captcha', 'challenge', 'datadome', 'cloudflare'])
        except Exception as e:
            print(f"Warning: Could not check page source: {e}")
            challenge_detected = False
        
        if challenge_detected:
            print("Warning: Detected CAPTCHA/challenge page.")
            print("Please wait - the browser window will stay open.")
            print("If a CAPTCHA appears, please solve it manually in the browser window.")
            print("Waiting up to 60 seconds for challenge to resolve...")
            # Wait longer and try to interact
            for i in range(6):  # Wait up to 60 seconds
                try:
                    time.sleep(10)
                    # Try scrolling to simulate human behavior
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                    time.sleep(1)
                    # Check if challenge is resolved
                    current_source = driver.page_source.lower()
                    if not any(kw in current_source for kw in ['captcha', 'challenge', 'datadome']):
                        print("Challenge appears to be resolved.")
                        break
                except Exception as e:
                    print(f"Error during challenge wait: {e}")
                    # Browser might have closed, break out
                    break
        
        # Wait for page to fully load
        time.sleep(wait_time)
        
        # Try to wait for body element
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("Warning: Timeout waiting for page body")
        except Exception as e:
            print(f"Warning: Error waiting for page: {e}")
        
        # Scroll to trigger lazy loading and simulate human behavior
        print("Scrolling to load content...")
        try:
            for scroll_pos in [0.25, 0.5, 0.75, 1.0]:
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pos});")
                time.sleep(1)
            
            # Scroll back up
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Final scroll down to load all content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        except Exception as e:
            print(f"Warning: Error during scrolling: {e}")
        
        # Get page source (with error handling)
        try:
            html = driver.page_source
        except Exception as e:
            print(f"Error getting page source: {e}")
            # Browser might have closed
            return None
        
        # Parse with BeautifulSoup
        return BeautifulSoup(html, 'html.parser')
        
    except WebDriverException as e:
        print(f"Selenium error fetching {url}: {e}")
        print("Browser may have closed unexpectedly. This can happen with CAPTCHA pages.")
        return None
    except Exception as e:
        print(f"Error with Selenium: {e}")
        return None
    finally:
        if driver:
            try:
                # Give it a moment before closing
                time.sleep(1)
                driver.quit()
            except Exception as e:
                # Ignore errors during cleanup
                pass


def get_soup(url: str, headers: dict = None, use_selenium: bool = False) -> Optional[BeautifulSoup]:
    """
    Fetch a URL and return a BeautifulSoup object.
    
    Args:
        url: URL to fetch
        headers: Optional headers to include in the request
        use_selenium: If True, use Selenium for JavaScript-rendered content
        
    Returns:
        BeautifulSoup object or None if fetch fails
    """
    # Use Selenium if requested and available
    if use_selenium:
        soup = get_soup_with_selenium(url)
        if soup:
            return soup
        # Fallback to requests if Selenium fails
        print("Selenium failed, falling back to requests...")
    
    # Use requests (faster but doesn't handle JS)
    response = fetch_with_retry(url, headers=headers)
    if response is None:
        return None
    
    try:
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error parsing HTML from {url}: {e}")
        return None

