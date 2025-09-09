import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def scrape_instagram_page(page_url):
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--lang=en-US")
    
    # Path to your chromedriver (download from https://sites.google.com/chromium.org/driver/)
    # You can also use webdriver_manager to handle this automatically
    service = Service('chromedriver')  # Update this path
    
    # Initialize the driver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Open the Instagram page
        driver.get(page_url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "article")))
        
        # Scroll down to load more posts (you can adjust the number of scrolls)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all posts
        posts = soup.find_all('article')
        
        if not posts:
            print("No posts found on this page.")
            return
        
        print(f"\nFound {len(posts)} posts on the page:\n")
        
        for i, post in enumerate(posts, 1):
            print(f"=== Post {i} ===")
            
            # Extract username
            username = post.find('a', {'class': 'x1i10hfl'})
            if username:
                print(f"Username: {username.text.strip()}")
            
            # Extract post time (if available)
            time_tag = post.find('time')
            if time_tag:
                print(f"Posted: {time_tag.get('datetime', 'N/A')}")
            
            # Extract caption (approximate)
            caption = post.find('div', {'class': '_a9zs'})
            if caption:
                print(f"Caption: {caption.text.strip()}")
            
            # Extract likes count (approximate)
            likes = post.find('span', {'class': 'x193iq5w'})
            if likes:
                print(f"Likes: {likes.text.strip()}")
            
            # Extract image/video URL (approximate)
            media = post.find('img', {'class': 'x5yr21d'})
            if media:
                print(f"Media URL: {media.get('src', 'N/A')}")
            
            print("\n")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Instagram Page Scraper")
    print("----------------------\n")
    
    page_url = input("Enter the Instagram page URL: ").strip()
    
    if not page_url.startswith(('https://www.instagram.com/', 'http://www.instagram.com/')):
        print("Please enter a valid Instagram page URL.")
    else:
        scrape_instagram_page(page_url)