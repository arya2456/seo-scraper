import streamlit as st
import pandas as pd
import time
import re
import random
import requests
import os
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from urllib.parse import urlparse

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def get_contact_info(url):
    data = {"Email": "N/A", "Phone": "N/A"}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        response = requests.get(url, timeout=4, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()

        # Find Email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp'))]
        if valid_emails:
            data["Email"] = valid_emails[0]

        # Find Phone
        tel_links = soup.select("a[href^='tel:']")
        if tel_links:
            data["Phone"] = tel_links[0]['href'].replace("tel:", "")
        else:
            phone_pattern = r'(\+91[\-\s]?)?[6789]\d{9}'
            phones = re.findall(phone_pattern, text)
            if phones:
                data["Phone"] = "Found in text" 
    except:
        pass 
    return data

def setup_driver():
    options = webdriver.ChromeOptions()
    
    # --- CLOUD SETTINGS (CRITICAL) ---
    options.add_argument("--headless") # Must be headless on server
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Anti-detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

    # LOCATE CHROME ON LINUX/CLOUD
    # Streamlit Cloud installs chromium at /usr/bin/chromium
    
    try:
        # Try finding Chromium automatically (Best for Streamlit Cloud)
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        st.warning(f"Standard method failed: {e}. Trying fallback path...")
        
    try:
        # Hardcoded fallback for Debian/Linux environments
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e2:
        st.error(f"Could not start browser. Details: {e2}")
        return None

# ==========================================
# 2. UI
# ==========================================

st.set_page_config(page_title="SEO Scraper", layout="wide")

st.sidebar.title("🕵️ Cloud Scraper")
keyword = st.sidebar.text_input("Enter Keyword", "ccna course in delhi")

# Logic Selection
logic_mode = st.sidebar.selectbox(
    "Target Logic",
    ("Low Ranking (Page 4-10)", "Top Ranking (Page 1-3)")
)
if "Low Ranking" in logic_mode:
    start_page = 4
    max_pages = 3
else:
    start_page = 1
    max_pages = 3

st.sidebar.info("Note: Running on Cloud Server. 'Show Browser' is disabled.")

run_btn = st.sidebar.button("🚀 Start Scraper")
status_area = st.empty()
table_area = st.empty()

# ==========================================
# 3. SCRAPING LOOP
# ==========================================

if run_btn:
    driver = setup_driver()
    
    if driver:
        results = []
        try:
            status_area.info("Browser Started. Visiting Google...")
            driver.get("https://www.google.com")
            
            search_box = driver.find_element(By.NAME, "q")
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)
            time.sleep(2)

            # Jump pages logic
            start_index = (start_page - 1) * 10
            if start_index > 0:
                current_url = driver.current_url + f"&start={start_index}"
                driver.get(current_url)
                time.sleep(2)

            pages_scraped = 0
            
            while pages_scraped < max_pages:
                current_page_num = start_page + pages_scraped
                status_area.warning(f"Scanning Page {current_page_num}...")
                
                # Check for Captcha by title or url
                if "sorry" in driver.current_url:
                    st.error("Google has blocked this Server IP (Captcha). Try again later.")
                    break

                search_results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
                
                for res in search_results:
                    try:
                        link = res.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                        title = res.find_element(By.CSS_SELECTOR, 'h3').text
                        
                        # Simple Ignore Logic
                        domain = urlparse(link).netloc
                        if "google" in domain or "youtube" in domain or "justdial" in domain:
                            continue

                        # Extract
                        contacts = get_contact_info(link)
                        
                        results.append({
                            "Business": title,
                            "Website": link,
                            "Email": contacts['Email'],
                            "Phone": contacts['Phone']
                        })
                        
                        table_area.dataframe(pd.DataFrame(results))
                    except:
                        continue
                
                pages_scraped += 1
                try:
                    driver.find_element(By.ID, "pnnext").click()
                    time.sleep(2)
                except:
                    break

            # Done
            if results:
                status_area.success(f"Finished! Found {len(results)} leads.")
                csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "leads.csv", "text/csv")
            else:
                status_area.error("No results found (or blocked by Google).")

        except Exception as e:
            st.error(f"Runtime Error: {e}")
        finally:
            driver.quit()
