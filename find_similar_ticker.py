#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "beautifulsoup4",
# ]
# ///

#chmod +x find_similar_ticker.py
#./find_similar_ticker.py

import requests
from bs4 import BeautifulSoup
import re
import time
import os
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from config import FEED_URL, SLACK_WEBHOOK_URL, PROCESSED_LOG, TICKER_CACHE_FILE, TICKER_SOURCE_URL, CACHE_MAX_AGE, HEADERS



def fetch_existing_tickers():
    if not os.path.exists(TICKER_CACHE_FILE) or (time.time() - os.path.getmtime(TICKER_CACHE_FILE)) > CACHE_MAX_AGE:
        r = requests.get(TICKER_SOURCE_URL, headers=HEADERS)
        r.raise_for_status()
        with open(TICKER_CACHE_FILE, "w") as f:
            f.write(r.text)
    with open(TICKER_CACHE_FILE) as f:
        return set(line.strip().upper() for line in f if line.strip())

def load_processed_filings():
    if not os.path.exists(PROCESSED_LOG):
        return set()
    with open(PROCESSED_LOG) as f:
        return set(line.strip() for line in f)

def log_processed_filing(accession_number):
    with open(PROCESSED_LOG, "a") as f:
        f.write(accession_number + "\n")


def notify_slack(message):
    payload = {"text": message}
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            print(f"   ⚠️  Slack notification failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"   ⚠️  Slack error: {e}")


def is_distance_one_focused(s1, s2):
    if s1 == s2:
        return False
    len_diff = abs(len(s1) - len(s2))
    if len_diff > 1:
        return False
    if len(s1) == len(s2):
        return sum(a != b for a, b in zip(s1, s2)) == 1
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    for i in range(len(s2)):
        if s1 == s2[:i] + s2[i+1:]:
            return True
    return False


def extract_ticker_from_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)


    patterns = [
        r'under the (?:trading )?symbol\s+[“"]?([A-Z]{1,5})[”",.]?',  # under the (trading )?symbol “XYZ”
        r'under the symbol\s+[“"]?([A-Z]{1,5})[”",.]?',  # under the symbol “XYZ”
        r'ticker(?:\s+symbol)?\s*[:\-]?\s*[“"]?([A-Z]{1,5})[”",.]?',  # ticker symbol: XYZ
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ticker = match.group(1).upper()
            if ticker == "SYMBO":
                print("   ❌ Found 'SYMBO' instead of a ticker. Known bug, skipping...")
                continue
            print(f"   ✅ Ticker match found: {ticker}")
            return ticker

    print("   ❌ No ticker pattern match found.")

    return None


def fetch_s1_entries():
    r = requests.get(FEED_URL, headers=HEADERS)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    return [
        {
            "title": e.find("atom:title", ns).text,
            "link": e.find("atom:link", ns).attrib["href"],
            "updated": e.find("atom:updated", ns).text,
        }
        for e in entries
    ]

def get_primary_doc_text(filing_url):
    print(f"   🔍 Fetching filing index page: {filing_url}")
    r = requests.get(filing_url, headers=HEADERS)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"class": "tableFile"})

    if not table:
        print("   ❌ No document table found.")
        return None

    rows = table.find_all("tr")[1:]  # skip header
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        doc_link = cells[2].find("a")
        if not doc_link:
            continue
        doc_type = cells[3].text.strip().upper()
        if doc_type.startswith("S-1"):
            relative_url = doc_link["href"]
            full_url = urljoin(filing_url, relative_url)
            if 'ix?doc=' in full_url:
                print("   🔗 Found ix?doc= in URL, cleaning up as we dont want the javascript viewer...")
                full_url = full_url.replace("ix?doc=/", "")

            print(f"   📄 Using document: {doc_link.text.strip()} ({doc_type})")
            print(f"   📄 Full URL: {full_url}")
            doc_r = requests.get(full_url, headers=HEADERS)
            doc_r.raise_for_status()
            return doc_r.text

    print("   ❌ No S-1 document found in table.")
    return None


def main():
    existing_tickers = fetch_existing_tickers()
    entries = fetch_s1_entries()
    processed = load_processed_filings()

    print(f"\nFound {len(entries)} recent S-1 filings...\n")

    for entry in entries:
        accession = entry["link"].split("/")[-1].replace("-index.htm", "")
        if accession in processed:
            print(f"⏩ Already processed {accession}, skipping.\n")
            continue

        time.sleep(5)
        print(f"📝 {entry['title']} - {entry['updated']}")
        filing_text = get_primary_doc_text(entry["link"])
        if not filing_text:
            print("   ⚠️  Could not fetch filing text.\n")
            continue

        log_processed_filing(accession)

        proposed = extract_ticker_from_text(filing_text)
        if not proposed:
            print("   ⚠️  Ticker not found.\n")
            continue

        matches = [t for t in existing_tickers if is_distance_one_focused(proposed, t)]
        if matches:
            msg = f"   ⚠️  Proposed ticker: {proposed} — Similar existing tickers: {matches}\n"
            print(f"   ⚠️  {msg}\n")
            notify_slack(msg)
        else:
            print(f"   ✅ Proposed ticker: {proposed} — No close matches.\n")


if __name__ == "__main__":
    main()
