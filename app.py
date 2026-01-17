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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        # Timeout is short (5s)
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()

        # Regex for Email
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp'))]
        if valid_emails:
            data["Email"] = valid_emails[0]

        # Regex for Phone
        # Check tel link first
        tel_link = soup.select_one("a[href^='tel:']")
        if tel_link:
            data["Phone"] = tel_link['href'].replace("tel:", "")
        else:
            # Fallback regex
            phones = re.findall(r'(\+91[\-\s]?)?[6789]\d{9}', text)
            if phones:
                data["Phone"] = "Found in text (Clean in CSV)"

    except Exception:
        pass 
    return data

# ==========================================
# 2. UI
# ==========================================
st.set_page_config(page_title="Lead Generator", layout="wide")

st.sidebar.title("🕵️ Lead Scraper")
keyword = st.sidebar.text_input("Enter Keyword", "ccna course in delhi")

logic_mode = st.sidebar.selectbox(
    "How many VALID leads do you need?",
    (
        "10 Leads (Fast)", 
        "20 Leads (Standard)",
        "50 Leads (Deep Search)"
    )
)

# Parse Limit
if "10" in logic_mode: target_leads = 10
elif "20" in logic_mode: target_leads = 20
else: target_leads = 50

st.sidebar.markdown("---")
default_ignore = "justdial, sulekha, quora, linkedin, facebook, shiksha, urbanpro, youtube, google, amazon, udemy, coursera, glassdoor, indeed, naukri"
ignore_input = st.sidebar.text_area("Ignore Domains (Comma Separated)", default_ignore, height=150)
ignore_list = [x.strip() for x in ignore_input.split(',')]

run_btn = st.sidebar.button("🚀 Find Leads")

st.title("Business Lead Scraper (Smart Filter)")
st.caption(f"Goal: Find {target_leads} real business websites. Skipping directories.")

# UI Containers
metric_col1, metric_col2 = st.columns(2)
progress_bar = st.progress(0)
status_area = st.empty()
log_expander = st.expander("View Processing Logs", expanded=True)
table_area = st.empty()

# ==========================================
# 3. MAIN LOGIC
# ==========================================
if run_btn:
    results = []
    
    # We fetch A LOT of raw results because most will be junk directories
    FETCH_LIMIT = 100 
    
    status_area.info("Searching DuckDuckGo... This takes a moment.")
    
    try:
        # 1. GET RAW RESULTS
        raw_results = []
        with DDGS() as ddgs:
            # region='in-en' for India, or 'wt-wt' for global. 
            # Using wt-wt is safer for cloud servers to avoid 0 results.
            generator = ddgs.text(keyword, region='wt-wt', max_results=FETCH_LIMIT)
            for r in generator:
                raw_results.append(r)
        
        status_area.success(f"Found {len(raw_results)} raw search results. Filtering now...")
        
        # 2. FILTER & EXTRACT LOOP
        processed_count = 0
        
        for res in raw_results:
            # Stop if we hit the user's target
            if len(results) >= target_leads:
                break
                
            processed_count += 1
            progress_bar.progress(min(processed_count / len(raw_results), 1.0))
            
            url = res['href']
            title = res['title']
            try:
                domain = urlparse(url).netloc.replace("www.", "")
            except:
                continue

            # CHECK IGNORE LIST
            is_ignored = False
            for ignored in ignore_list:
                if ignored in domain:
                    is_ignored = True
                    log_expander.write(f"❌ Skipped Directory: {domain}")
                    break
            
            if is_ignored:
                continue
            
            # CHECK DUPLICATES
            if any(r['Domain'] == domain for r in results):
                continue

            # IF WE ARE HERE, IT'S A REAL LEAD
            log_expander.write(f"✅ Scanning Website: {domain}")
            
            # Extract Contacts
            contacts = extract_contacts(url)
            
            results.append({
                "Business Name": title,
                "Domain": domain,
                "Email": contacts['Email'],
                "Phone": contacts['Phone'],
                "Website": url
            })
            
            # Update UI Live
            metric_col1.metric("Leads Found", len(results))
            metric_col2.metric("Sites Scanned", processed_count)
            table_area.dataframe(pd.DataFrame(results))
            
            # Small sleep to prevent crashing
            time.sleep(0.1)

        # 3. FINISH
        if len(results) > 0:
            status_area.success(f"Job Complete! Found {len(results)} qualified leads.")
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"leads_{keyword}.csv", "text/csv")
        else:
            status_area.error("Scanned the top 100 results but found 0 leads. Try removing items from the 'Ignore List' or changing the keyword.")

    except Exception as e:
        status_area.error(f"Error: {e}")
