from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import time

# Replace with the path to your ChromeDriver
CHROME_DRIVER_PATH = "/path/to/chromedriver"

# Sandbox credentials
email = "mojalefajefff@gmail.com"
password = "oneonetwo"

# Setup browser
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)

# Go to PayPal Sandbox login
driver.get("https://www.sandbox.paypal.com/signin")

# Wait for page to load
time.sleep(3)

# Enter email
email_input = driver.find_element(By.ID, "email")
email_input.send_keys(email)
email_input.send_keys(Keys.RETURN)

time.sleep(3)

# Enter password
password_input = driver.find_element(By.ID, "password")
password_input.send_keys(password)
password_input.send_keys(Keys.RETURN)

# Wait to see result
time.sleep(10)

# You are now logged in to the sandbox (optional: screenshot it)
driver.save_screenshot("sandbox_logged_in.png")

# Close browser
driver.quit()
