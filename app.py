import streamlit as st
import pandas as pd
import time
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def get_contact_info(url):
    """
    Visits a URL and tries to find emails and phone numbers.
    """
    data = {"Email": "N/A", "Phone": "N/A"}
    try:
        # aggressive timeout to keep the tool fast
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()

        # Find Email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp'))]
        if valid_emails:
            data["Email"] = valid_emails[0]

        # Find Phone (Generic pattern)
        # Check for tel: links first (most accurate)
        tel_links = soup.select("a[href^='tel:']")
        if tel_links:
            data["Phone"] = tel_links[0]['href'].replace("tel:", "")
        else:
            # Fallback regex for loose numbers
            phone_pattern = r'(\+91[\-\s]?)?[6789]\d{9}'
            phones = re.findall(phone_pattern, text)
            if phones:
                # This regex returns tuples, need to clean up
                data["Phone"] = "Found in text" 

    except:
        pass # If site fails, just return N/A
    return data

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # This helps avoid bot detection on servers
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    # This logic automatically finds Chrome on Streamlit Cloud/Linux or Local
    service = Service(ChromeDriverManager(driver_version="114.0.5735.90").install())
    
    # Try generic driver setup
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except:
        # Fallback for Streamlit Cloud specific path
        options.binary_location = "/usr/bin/chromium"
        driver = webdriver.Chrome(service=Service(), options=options)

    return driver

# ==========================================
# 2. STREAMLIT UI LAYOUT
# ==========================================

st.set_page_config(page_title="SEO Lead Scraper", layout="wide")

# Sidebar for Logic Inputs
st.sidebar.title("🕵️ Scraper Logic")
st.sidebar.header("1. Target Data")
keyword = st.sidebar.text_input("Enter Keyword", "ccna course in delhi")

st.sidebar.header("2. Search Logic")
logic_mode = st.sidebar.selectbox(
    "Who are we looking for?",
    (
        "Low Ranking (Page 4-10) - Ideal for SEO Pitching",
        "Top Ranking (Page 1-3) - Competitor Analysis",
        "Deep Dive (Page 1-10) - Maximum Data"
    )
)

# Logic Translation
if "Low Ranking" in logic_mode:
    start_page = 4
    max_pages = 3
elif "Top Ranking" in logic_mode:
    start_page = 1
    max_pages = 3
else:
    start_page = 1
    max_pages = 10

st.sidebar.header("3. Filters")
default_ignore = "justdial.com, sulekha.com, quora.com, linkedin.com, facebook.com, shiksha.com, urbanpro.com, wikipedia.org, youtube.com"
ignore_input = st.sidebar.text_area("Ignore these domains (comma separated)", default_ignore)
ignore_list = [x.strip() for x in ignore_input.split(',')]

run_btn = st.sidebar.button("🚀 Start Scraper")

# Main Content Area
st.title("Web Data Scraper with Business Logic")
st.markdown(f"**Current Logic:** Scraping '{keyword}' starting from **Page {start_page}** (ignoring directories).")

status_area = st.empty()
table_area = st.empty()

# ==========================================
# 3. MAIN SCRAPING LOOP
# ==========================================

if run_btn:
    driver = setup_driver()
    results = []
    
    try:
        status_area.info("Initializing Browser...")
        driver.get("https://www.google.com")
        
        # Search
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)

        # Logic: Jump to specific page
        start_index = (start_page - 1) * 10
        if start_index > 0:
            current_url = driver.current_url + f"&start={start_index}"
            driver.get(current_url)
            time.sleep(2)

        pages_scraped = 0
        
        while pages_scraped < max_pages:
            current_page_num = start_page + pages_scraped
            status_area.warning(f"Scraping Google Page {current_page_num}...")
            
            # Get Results
            search_results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
            
            for res in search_results:
                try:
                    link_tag = res.find_element(By.CSS_SELECTOR, 'a')
                    url = link_tag.get_attribute('href')
                    title = res.find_element(By.CSS_SELECTOR, 'h3').text
                    
                    if not url or not title: continue
                    
                    # Domain Filter Logic
                    domain = urlparse(url).netloc.replace("www.", "")
                    if any(ignored in domain for ignored in ignore_list):
                        continue # Skip directories

                    # Data Extraction
                    # Check if we already have this domain to avoid duplicates
                    if any(r['Domain'] == domain for r in results):
                        continue

                    # Visit site for contacts
                    status_area.text(f"Extracting contact info from: {domain}")
                    contacts = get_contact_info(url)

                    results.append({
                        "Rank": len(results) + 1 + start_index,
                        "Business Name": title,
                        "Domain": domain,
                        "Website": url,
                        "Email": contacts['Email'],
                        "Phone": contacts['Phone'],
                        "Source Page": current_page_num
                    })
                    
                    # Update Table Live
                    df_live = pd.DataFrame(results)
                    table_area.dataframe(df_live)

                except Exception as e:
                    continue
            
            # Next Page Logic
            pages_scraped += 1
            try:
                next_button = driver.find_element(By.ID, "pnnext")
                next_button.click()
                time.sleep(3)
            except:
                status_area.error("No more pages found or Google blocked the request.")
                break

        status_area.success(f"Finished! Found {len(results)} potential leads.")
        
        # Download Button
        if results:
            df_final = pd.DataFrame(results)
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv,
                file_name=f'leads_{keyword.replace(" ", "_")}.csv',
                mime='text/csv',
            )

    except Exception as e:
        status_area.error(f"An error occurred: {e}")
    finally:

        driver.quit()
