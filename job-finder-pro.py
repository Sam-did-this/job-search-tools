#!/usr/bin/env python3
"""
============================================================
JOB FINDER PRO — Local Gigs + Remote Tech Jobs
Search everything. Filter what you need. Save where you want.
============================================================

USAGE:
  python job-finder-pro.py                                    # Everything, print to terminal
  python job-finder-pro.py -s "python"                        # Only Python jobs
  python job-finder-pro.py -s "cash, cleaning"                # Cash + cleaning jobs
  python job-finder-pro.py -s "ai, react" -o python_jobs.txt  # Filter + save to ~/Documents/

CONFIGURATION:
  Edit the SETTINGS section below.
============================================================
"""

import requests
from bs4 import BeautifulSoup
import time
import sys
import json
import os
import argparse
from datetime import datetime
from pathlib import Path

# ============================================================
# SETTINGS — EDIT THESE FOR YOUR CITY & PREFERENCES
# ============================================================

# --- Your Location ---
CITY_CODE = 'newyork'           # Lowercase craigslist city code
SUBAREA = 'que'                 # Borough: mnh, brx, brk, que, stn
BASE_URL = f"https://{CITY_CODE}.craigslist.org"

# --- Local Gig Categories (Craigslist) ---
LOCAL_CATEGORIES = ['ggg', 'lab', 'dom', 'trd']

# --- Keywords to EXCLUDE (local jobs) ---
EXCLUDE_KEYWORDS = [
    "customer service", "call center", "retail", "cashier",
    "sales associate", "server", "bartender", "hostess",
    "receptionist", "front desk", "dental", "medical assistant",
    "rn", "registered nurse", "real estate", "insurance",
    "bank", "teller", "administrative", "assistant", "office"
]

# --- Priority Keywords (local jobs) ---
PRIORITY_KEYWORDS = [
    "cash", "daily pay", "same day", "under the table",
    "no experience", "helper", "clean", "cleaning",
    "move", "moving", "haul", "hauling", "labor",
    "construction", "warehouse", "painter", "painting",
    "handyman", "landscaping", "yard", "snow"
]

# --- Remote Job Keywords ---
AI_KEYWORDS = [
    "ai", "machine learning", "ml", "llm", "gpt",
    "copilot", "chatgpt", "prompt engineer", "generative ai",
    "openai", "anthropic", "claude", "gemini", "nlp"
]

DEV_KEYWORDS = [
    "python", "javascript", "typescript", "react", "node",
    "full stack", "backend", "frontend", "software engineer",
    "web developer", "api", "cloud", "devops", "remote"
]

# --- General Settings ---
DELAY_SECONDS = 2
MAX_RESULTS = 50
SAVE_HISTORY = True
HISTORY_FILE = Path.home() / "job_finder_pro_history.json"
OUTPUT_DIR = Path.home() / "Documents"  # Default save location (Linux/Windows/Mac)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
}

# ============================================================
# LOCAL JOB FETCHING (Craigslist)
# ============================================================

def get_local_search_urls():
    urls = []
    for cat in LOCAL_CATEGORIES:
        urls.append(f"{BASE_URL}/search/{SUBAREA}/{cat}")
    return urls

def fetch_local_listings(search_url):
    listings = []
    try:
        response = requests.get(search_url, timeout=15, headers=HEADERS)
        response.raise_for_status()
    except requests.RequestException:
        return listings

    if not response.text or len(response.text) < 1000:
        return listings

    soup = BeautifulSoup(response.text, 'html.parser')
    results = (
        soup.find_all('li', class_='cl-search-result') or
        soup.find_all('li', class_='result-row') or
        soup.find_all('div', class_='result-info') or
        []
    )

    if not results:
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/d/' in href or '/g/' in href:
                title = link.text.strip()
                if title and len(title) > 5:
                    results.append({'link': link, 'title': title})

    for result in results:
        if hasattr(result, 'find_all'):
            link_tag = (
                result.find('a', class_='titlestring') or
                result.find('a', class_='result-title') or
                result.find('a', href=True)
            )
            if not link_tag or not link_tag.get('href'):
                continue
            title = link_tag.text.strip()
            link = link_tag['href']
        else:
            link = result['link'].get('href', '')
            title = result['title']

        if link.startswith('/'):
            link = f"{BASE_URL}{link}"
        if not title or not link:
            continue

        title_lower = title.lower()
        if any(w in title_lower for w in EXCLUDE_KEYWORDS):
            continue

        listings.append({
            'title': title,
            'link': link,
            'priority': any(w in title_lower for w in PRIORITY_KEYWORDS),
            'source': 'Craigslist',
            'type': 'local'
        })
    return listings

# ============================================================
# REMOTE JOB FETCHING
# ============================================================

def fetch_remotive_jobs():
    jobs = []
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs?category=software-dev&limit=50",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        for job in resp.json().get("jobs", []):
            text = f"{job.get('title','')} {job.get('description','')} {' '.join(job.get('tags',[]))}".lower()
            ai = sum(1 for k in AI_KEYWORDS if k in text)
            dev = sum(1 for k in DEV_KEYWORDS if k in text)
            if ai or dev:
                jobs.append({
                    'title': job.get('title', ''),
                    'link': job.get('url', ''),
                    'company': job.get('company_name', ''),
                    'source': 'Remotive',
                    'type': 'remote',
                    'is_ai': ai > 0
                })
    except:
        pass
    return jobs

def fetch_remoteok_jobs():
    jobs = []
    try:
        resp = requests.get(
            "https://remoteok.com/api/remote-dev-jobs",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        for job in data[1:]:
            if not isinstance(job, dict):
                continue
            text = f"{job.get('position','')} {job.get('description','')} {' '.join(job.get('tags',[]))}".lower()
            ai = sum(1 for k in AI_KEYWORDS if k in text)
            dev = sum(1 for k in DEV_KEYWORDS if k in text)
            if ai or dev:
                jobs.append({
                    'title': job.get('position', ''),
                    'link': f"https://remoteok.com/remote-jobs/{job.get('slug', '')}",
                    'company': job.get('company', ''),
                    'source': 'RemoteOK',
                    'type': 'remote',
                    'is_ai': ai > 0
                })
    except:
        pass
    return jobs

def fetch_weworkremotely_jobs():
    jobs = []
    try:
        resp = requests.get(
            "https://weworkremotely.com/categories/remote-programming-jobs",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        listings = soup.find_all('li', class_='feature') or soup.find_all('article') or []
        for listing in listings[:30]:
            title_tag = listing.find('h4') or listing.find('a')
            company_tag = listing.find('strong') or listing.find(class_='company')
            link_tag = listing.find('a', href=True)
            if not title_tag or not link_tag:
                continue
            title = title_tag.text.strip()
            company = company_tag.text.strip() if company_tag else "Unknown"
            url = link_tag['href']
            if url.startswith('/'):
                url = f"https://weworkremotely.com{url}"
            text = f"{title} {company}".lower()
            ai = sum(1 for k in AI_KEYWORDS if k in text)
            dev = sum(1 for k in DEV_KEYWORDS if k in text)
            if ai or dev:
                jobs.append({
                    'title': title,
                    'link': url,
                    'company': company,
                    'source': 'WeWorkRemotely',
                    'type': 'remote',
                    'is_ai': ai > 0
                })
    except:
        pass
    return jobs

# ============================================================
# HISTORY
# ============================================================

def load_history():
    if not SAVE_HISTORY or not HISTORY_FILE.exists():
        return set()
    try:
        with open(HISTORY_FILE, 'r') as f:
            return set(json.load(f).get('seen_links', []))
    except:
        return set()

def save_history(urls):
    if not SAVE_HISTORY:
        return
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump({'seen_links': list(urls), 'updated': datetime.now().isoformat()}, f, indent=2)
    except:
        pass

# ============================================================
# FILTERING
# ============================================================

def filter_jobs(jobs, search_terms):
    """Filter jobs by search terms. Returns matching jobs only."""
    if not search_terms:
        return jobs
    terms = [t.strip().lower() for t in search_terms.split(',')]
    filtered = []
    for job in jobs:
        text = f"{job.get('title','')} {job.get('company','')} {job.get('source','')}".lower()
        if any(term in text for term in terms):
            filtered.append(job)
    return filtered

# ============================================================
# DISPLAY / SAVE
# ============================================================

def format_results(jobs, mode_label, search_terms=None):
    """Format results into a readable string (for print or file)"""
    lines = []
    
    if not jobs:
        lines.append(f"\n{'='*70}")
        lines.append(f"😔 NO {mode_label.upper()} JOBS FOUND")
        if search_terms:
            lines.append(f"🔍 Filter: {search_terms}")
        lines.append(f"{'='*70}")
        return "\n".join(lines)

    seen = load_history()
    jobs.sort(key=lambda j: (not j['link'] not in seen, not j.get('priority', False), not j.get('is_ai', False)))
    
    display = jobs[:MAX_RESULTS]
    new_count = sum(1 for j in display if j['link'] not in seen)
    priority_count = sum(1 for j in display if j.get('priority'))
    ai_count = sum(1 for j in display if j.get('is_ai'))

    lines.append(f"\n{'='*70}")
    header = f"🎯 {mode_label.upper()} JOBS — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    if search_terms:
        header += f" | 🔍 {search_terms}"
    lines.append(header)
    
    stats = f"📊 {len(jobs)} total | ✨ {new_count} new"
    if priority_count:
        stats += f" | ⭐ {priority_count} priority"
    if ai_count:
        stats += f" | 🤖 {ai_count} AI"
    lines.append(stats)
    lines.append(f"{'='*70}")

    for i, job in enumerate(display, 1):
        is_new = job['link'] not in seen
        marker = "🆕" if is_new else "  "
        badge = ""
        if job.get('priority'):
            badge += "⭐"
        if job.get('is_ai'):
            badge += "🤖"
        if badge:
            badge += " "
        company = f" — {job.get('company', '')}" if job.get('company') else ""

        lines.append(f"\n{i:2d}. {marker} {badge}{job['title'][:75]}")
        lines.append(f"    📂 {job['source']}{company} | {'🆕 NEW' if is_new else '   '}")
        lines.append(f"    🔗 {job['link']}")

    lines.append(f"\n{'='*70}")
    if new_count:
        lines.append(f"💡 {new_count} NEW listings — apply fast!")
    lines.append(f"{'='*70}")

    if SAVE_HISTORY and new_count:
        save_history(seen | {j['link'] for j in display})

    return "\n".join(lines)

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Job Finder Pro — Search everything, filter what you need.")
    parser.add_argument('-s', '--search', type=str, default='',
                        help='Filter: "python", "cash, cleaning", "ai, react"')
    parser.add_argument('-o', '--output', type=str, default='',
                        help='Save to file in ~/Documents/ instead of printing')
    args = parser.parse_args()

    search_terms = args.search
    output_file = args.output

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_output = []

    # --- Local Jobs ---
    print(f"🔍 Searching local gigs...")
    urls = get_local_search_urls()
    local_jobs = []
    for i, url in enumerate(urls, 1):
        local_jobs.extend(fetch_local_listings(url))
        if i < len(urls):
            time.sleep(DELAY_SECONDS)
    
    local_jobs = filter_jobs(local_jobs, search_terms)
    local_output = format_results(local_jobs, "local", search_terms)
    all_output.append(local_output)

    # --- Remote Jobs ---
    print(f"🔍 Searching remote tech jobs...")
    remote_jobs = []
    remote_jobs.extend(fetch_remotive_jobs())
    time.sleep(DELAY_SECONDS)
    remote_jobs.extend(fetch_remoteok_jobs())
    time.sleep(DELAY_SECONDS)
    remote_jobs.extend(fetch_weworkremotely_jobs())

    # Deduplicate
    seen_urls = set()
    unique_remote = []
    for j in remote_jobs:
        if j['link'] not in seen_urls:
            seen_urls.add(j['link'])
            unique_remote.append(j)
    
    unique_remote = filter_jobs(unique_remote, search_terms)
    remote_output = format_results(unique_remote, "remote", search_terms)
    all_output.append(remote_output)

    # --- Output ---
    final_output = "\n".join(all_output)

    if output_file:
        filepath = OUTPUT_DIR / output_file
        with open(filepath, 'w') as f:
            f.write(final_output)
        print(f"\n✅ Saved to: {filepath}")
    else:
        print(final_output)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
