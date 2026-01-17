import streamlit as st
import pandas as pd
import time
import re
import random
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
    data = {"Email": "N/A", "Phone": "N/A"}
    try:
        # Random user agent for requests
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        response = requests.get(url, timeout=5, headers=headers)
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

def setup_driver(headless_mode=True):
    options = webdriver.ChromeOptions()
    
    if headless_mode:
        options.add_argument("--headless") 
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled") # Crucial for Google
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Hide webdriver property to prevent detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

# ==========================================
# 2. STREAMLIT UI LAYOUT
# ==========================================

st.set_page_config(page_title="SEO Lead Scraper", layout="wide")

st.sidebar.title("🕵️ Scraper Logic")
keyword = st.sidebar.text_input("Enter Keyword", "ccna course in delhi")

logic_mode = st.sidebar.selectbox(
    "Target Logic",
    ("Low Ranking (Page 4-10)", "Top Ranking (Page 1-3)", "Deep Dive (Page 1-10)")
)

if "Low Ranking" in logic_mode:
    start_page = 4
    max_pages = 3
elif "Top Ranking" in logic_mode:
    start_page = 1
    max_pages = 3
else:
    start_page = 1
    max_pages = 10

st.sidebar.markdown("---")
show_browser = st.sidebar.checkbox("👀 Show Browser (Debug Mode)", value=True)
st.sidebar.caption("Keep this CHECKED. If Google asks for a Captcha, solve it manually in the window!")

default_ignore = "justdial.com, sulekha.com, quora.com, linkedin.com, facebook.com, shiksha.com, urbanpro.com, wikipedia.org, youtube.com, google.com"
ignore_input = st.sidebar.text_area("Ignore these domains", default_ignore)
ignore_list = [x.strip() for x in ignore_input.split(',')]

run_btn = st.sidebar.button("🚀 Start Scraper")

st.title("Web Data Scraper")
status_area = st.empty()
log_area = st.empty()
table_area = st.empty()

# ==========================================
# 3. MAIN SCRAPING LOOP
# ==========================================

if run_btn:
    # Pass False to setup_driver so the browser is VISIBLE
    driver = setup_driver(headless_mode=not show_browser)
    results = []
    
    try:
        status_area.info("Browser Launched. Visiting Google...")
        driver.get("https://www.google.com")
        
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3) # Wait for results

        # Logic: Jump to specific page
        start_index = (start_page - 1) * 10
        if start_index > 0:
            current_url = driver.current_url + f"&start={start_index}"
            driver.get(current_url)
            time.sleep(3)

        pages_scraped = 0
        
        while pages_scraped < max_pages:
            current_page_num = start_page + pages_scraped
            status_area.warning(f"Scraping Page {current_page_num}...")
            
            # --- DEBUGGING: Check for Captcha ---
            if "sorry" in driver.current_url or "google.com/sorry" in driver.current_url:
                st.error("⚠️ Google detected a bot! Please solve the Captcha in the browser window manually.")
                time.sleep(15) # Give user time to solve it
            
            # Find Results (Generic Divs)
            search_results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
            
            log_area.write(f"Found {len(search_results)} raw results on Page {current_page_num}. Filtering...")

            if len(search_results) == 0:
                log_area.error("No results found. Google might have changed layout or blocked the IP.")
            
            for res in search_results:
                try:
                    # Robust extraction
                    try:
                        link_tag = res.find_element(By.CSS_SELECTOR, 'a')
                        url = link_tag.get_attribute('href')
                        title_tag = res.find_element(By.CSS_SELECTOR, 'h3')
                        title = title_tag.text
                    except:
                        continue # Skip if structure is weird
                    
                    if not url or not title: continue
                    
                    # Domain Filter
                    domain = urlparse(url).netloc.replace("www.", "")
                    
                    # LOGIC: Check Ignore List
                    if any(ignored in domain for ignored in ignore_list):
                        # print(f"Ignored: {domain}")
                        continue 

                    # Avoid duplicates
                    if any(r['Domain'] == domain for r in results):
                        continue

                    # Visit site
                    log_area.write(f"🔍 Visiting: {domain}")
                    contacts = get_contact_info(url)

                    results.append({
                        "Business Name": title,
                        "Domain": domain,
                        "Email": contacts['Email'],
                        "Phone": contacts['Phone'],
                        "Link": url
                    })
                    
                    table_area.dataframe(pd.DataFrame(results))

                except Exception as e:
                    print(e)
                    continue
            
            # Next Page
            pages_scraped += 1
            try:
                next_button = driver.find_element(By.ID, "pnnext")
                next_button.click()
                time.sleep(random.uniform(3, 5)) # Random sleep to act human
            except:
                log_area.warning("No 'Next' button found. Stopping.")
                break

        status_area.success(f"Finished! Found {len(results)} leads.")
        
        if results:
            df_final = pd.DataFrame(results)
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, f'leads_{keyword}.csv', 'text/csv')

    except Exception as e:
        st.error(f"Critical Error: {e}")
    finally:
        # Only close if we are confident, otherwise leave open for debug
        if not show_browser:
            driver.quit()
