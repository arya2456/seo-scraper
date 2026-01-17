import streamlit as st
import pandas as pd
import time
import re
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from urllib.parse import urlparse

# ==========================================
# 1. HELPER: EXTRACT CONTACT INFO
# ==========================================
def extract_contacts(url):
    data = {"Email": "N/A", "Phone": "N/A"}
    try:
        # We use a fake browser header so websites let us in
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        # Timeout is short (3s) to keep the tool fast
        response = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()

        # Regex for Email
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp'))]
        if valid_emails:
            data["Email"] = valid_emails[0]

        # Regex for Phone (India + Generic)
        phones = re.findall(r'(\+91[\-\s]?)?[6789]\d{9}', text)
        if phones:
            data["Phone"] = "Found in text"
            
        # Check 'tel:' links for better accuracy
        tel_link = soup.select_one("a[href^='tel:']")
        if tel_link:
            data["Phone"] = tel_link['href'].replace("tel:", "")

    except Exception:
        pass # If site fails, return N/A
    return data

# ==========================================
# 2. STREAMLIT APP UI
# ==========================================
st.set_page_config(page_title="Lead Generator", layout="wide")

st.sidebar.title("🕵️ Lead Scraper")
st.sidebar.caption("Powered by DuckDuckGo (Cloud Safe)")

keyword = st.sidebar.text_input("Enter Keyword", "ccna course in delhi")

# LOGIC SELECTION
logic_mode = st.sidebar.selectbox(
    "Scraping Logic",
    (
        "Low SEO Clients (Rank 30-100)", 
        "Top Competitors (Rank 1-20)",
        "Deep Search (Rank 1-100)"
    )
)

# Translate Logic to Data Limits
if "Low SEO" in logic_mode:
    # Skip the first 30 results (Top guys), take the next 50
    OFFSET = 30
    LIMIT = 50
elif "Top Competitors" in logic_mode:
    OFFSET = 0
    LIMIT = 20
else:
    OFFSET = 0
    LIMIT = 100

st.sidebar.markdown("---")
ignore_input = st.sidebar.text_area("Ignore Domains", "justdial, sulekha, quora, linkedin, facebook, shiksha, urbanpro, youtube, google, amazon")
ignore_list = [x.strip() for x in ignore_input.split(',')]

run_btn = st.sidebar.button("🚀 Find Leads")

st.title("Business Lead Scraper (No Block)")
st.info(f"Logic Applied: {logic_mode}")

status_area = st.empty()
table_area = st.empty()

# ==========================================
# 3. MAIN LOGIC
# ==========================================
if run_btn:
    results = []
    status_area.info("Searching DuckDuckGo...")
    
    try:
        # Use DDGS library - It mimics a browser search without Selenium overhead
        with DDGS() as ddgs:
            # We fetch more results than needed to handle the offset logic
            search_results = list(ddgs.text(keyword, region='in-en', max_results=LIMIT + OFFSET))
        
        # Apply Logic: Slice the list (e.g., Skip first 30)
        targeted_results = search_results[OFFSET:]
        
        status_area.success(f"Found {len(targeted_results)} raw results. Extracting contacts...")
        
        progress_bar = st.progress(0)
        
        for i, res in enumerate(targeted_results):
            # Update Progress
            progress = (i + 1) / len(targeted_results)
            progress_bar.progress(progress)
            
            url = res['href']
            title = res['title']
            domain = urlparse(url).netloc.replace("www.", "")

            # Filter: Ignore List
            if any(ignored in domain for ignored in ignore_list):
                continue
            
            # Filter: Deduplicate
            if any(r['Domain'] == domain for r in results):
                continue
                
            # LIVE EXTRACTION
            contacts = extract_contacts(url)
            
            results.append({
                "Rank Position": OFFSET + i + 1,
                "Business Name": title,
                "Domain": domain,
                "Email": contacts['Email'],
                "Phone": contacts['Phone'],
                "Website": url
            })
            
            # Update Table
            table_area.dataframe(pd.DataFrame(results))
            time.sleep(0.1) # Tiny pause to be nice to CPU

        status_area.success(f"Job Done! Scraped {len(results)} valid leads.")
        
        if results:
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"leads_{keyword}.csv", "text/csv")

    except Exception as e:
        status_area.error(f"Error: {e}")
