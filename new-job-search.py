#!/usr/bin/env python3
"""
Job/Gig Finder for Craigslist - Fixed for 2026
"""

import requests
from bs4 import BeautifulSoup
import time
import sys
import json
import os
from datetime import datetime

# ============================================
# CONFIGURATION - EDIT THESE
# ============================================

# City code (MUST be lowercase!)
CITY_CODE = 'newyork'  # Lowercase!

# For NYC, you need a subarea (borough)
# Options: 'mnh' (Manhattan), 'brx' (Bronx), 'brk' (Brooklyn), 'que' (Queens), 'stn' (Staten Island)
SUBAREA = 'que'  # Queens

# Build the base URL - DIFFERENT STRUCTURE FOR NYC!
BASE_URL = f"https://{CITY_CODE}.craigslist.org"

# Search URL format for NYC (with subarea)
SEARCH_URL = f"https://{CITY_CODE}.craigslist.org/search/{SUBAREA}"

# Target categories - these are the CORRECT ones for Craigslist
TARGET_CATEGORIES = [
    'ggg',  # All gigs
    'lab',  # Labor gigs  
    'dom',  # Domestic work
    'trd',  # Trades
]

# Keywords to EXCLUDE
EXCLUDE_KEYWORDS = [
    "customer service", "call center", "retail", "cashier",
    "sales associate", "server", "bartender", "hostess",
    "receptionist", "front desk", "restaurant manager",
    "dental", "medical assistant", "rn", "registered nurse",
    "real estate", "insurance", "bank", "teller",
    "administrative", "assistant", "office"
]

# Keywords to HIGHLIGHT
PRIORITY_KEYWORDS = [
    "cash", "daily pay", "same day", "under the table",
    "no experience", "helper", "clean", "cleaning",
    "move", "moving", "haul", "hauling", "labor",
    "construction", "warehouse", "painter", "painting",
    "handyman", "landscaping", "yard", "snow"
]

# Settings
DELAY_SECONDS = 2
MAX_RESULTS = 50
SAVE_HISTORY = True
HISTORY_FILE = os.path.expanduser("~/job_finder_history.json")

# ============================================
# STEP 1: Get search URLs
# ============================================

def get_search_urls():
    """Generate the correct search URLs"""
    search_urls = []
    
    for category in TARGET_CATEGORIES:
        # Correct format for NYC: https://newyork.craigslist.org/search/que/ggg
        url = f"{BASE_URL}/search/{SUBAREA}/{category}"
        search_urls.append(url)
    
    print(f"✅ Generated {len(search_urls)} search URLs for {SUBAREA.upper()}")
    for url in search_urls:
        print(f"   {url}")
    
    return search_urls

# ============================================
# STEP 2: Fetch listings
# ============================================

def fetch_listings_from_search(search_url):
    """Fetch listings from a search URL"""
    listings = []
    
    try:
        print(f"  🔍 Searching: {search_url}")
        response = requests.get(search_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Failed to fetch {search_url}: {e}")
        return listings
    
    # Check if we got HTML
    if not response.text or len(response.text) < 1000:
        print(f"  ⚠️  Empty response from {search_url}")
        return listings
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try different ways to find listings
    results = []
    
    # Method 1: Look for result rows
    results = soup.find_all('li', class_='cl-search-result')
    if not results:
        results = soup.find_all('li', class_='result-row')
    if not results:
        results = soup.find_all('div', class_='result-info')
    
    if not results:
        # Look for any links that might be listings
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if '/d/' in href or '/g/' in href:  # Craigslist ad patterns
                title = link.text.strip()
                if title and len(title) > 5:
                    results.append({
                        'link': link,
                        'title': title
                    })
    
    print(f"  📊 Found {len(results)} results on page")
    
    for result in results:
        # Handle different result types
        if hasattr(result, 'find_all'):  # It's a BeautifulSoup tag
            # Try to find the title link
            link_tag = result.find('a', class_='titlestring')
            if not link_tag:
                link_tag = result.find('a', class_='result-title')
            if not link_tag:
                link_tag = result.find('a', href=True)
            
            if not link_tag or not link_tag.get('href'):
                continue
            
            title = link_tag.text.strip()
            link = link_tag['href']
        else:
            # It's a dict from our fallback method
            link = result['link'].get('href', '')
            title = result['title']
        
        # Make absolute URL
        if link.startswith('/'):
            link = f"{BASE_URL}{link}"
        
        # Skip empty titles or URLs
        if not title or not link:
            continue
        
        # Check for exclusion keywords
        title_lower = title.lower()
        should_exclude = any(word in title_lower for word in EXCLUDE_KEYWORDS)
        
        if should_exclude:
            continue
        
        # Check priority keywords
        is_priority = any(word in title_lower for word in PRIORITY_KEYWORDS)
        
        listings.append({
            'title': title,
            'link': link,
            'priority': is_priority,
            'category': search_url.split('/')[-1]
        })
    
    return listings

# ============================================
# STEP 3: Load/save history
# ============================================

def load_history():
    """Load previously seen listings"""
    if not SAVE_HISTORY or not os.path.exists(HISTORY_FILE):
        return set()
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('seen_links', []))
    except (json.JSONDecodeError, IOError):
        return set()

def save_history(links):
    """Save seen listing links"""
    if not SAVE_HISTORY:
        return
    
    data = {
        'seen_links': list(links),
        'last_updated': datetime.now().isoformat()
    }
    
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"⚠️  Could not save history: {e}")

# ============================================
# STEP 4: Display results
# ============================================

def display_results(all_listings):
    """Display listings with new/seen status"""
    if not all_listings:
        print("\n" + "=" * 70)
        print("😔 NO LISTINGS FOUND")
        print("=" * 70)
        print("\nTry these manual links:")
        for category in TARGET_CATEGORIES:
            url = f"{BASE_URL}/search/{SUBAREA}/{category}"
            print(f"  {url}")
        print("\nOr check the main page:")
        print(f"  {BASE_URL}")
        return
    
    # Load history
    seen_links = load_history()
    
    # Separate new vs seen
    new_listings = []
    seen_listings = []
    seen_set = set()
    
    for listing in all_listings:
        if listing['link'] in seen_links:
            seen_listings.append(listing)
        else:
            new_listings.append(listing)
            seen_set.add(listing['link'])
    
    # Sort: new priority first
    def sort_key(x):
        is_new = x['link'] not in seen_links
        return (not is_new, not x['priority'], x['title'].lower())
    
    sorted_listings = sorted(new_listings + seen_listings, key=sort_key)
    
    # Limit results
    display_listings = sorted_listings[:MAX_RESULTS]
    new_count = len(new_listings)
    
    print("\n" + "=" * 70)
    print(f"🎯 JOB FINDER RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📍 Location: {SUBAREA.upper()} ({CITY_CODE})")
    print(f"📊 {len(all_listings)} total | ✨ {new_count} new | ⭐ {sum(1 for l in new_listings if l['priority'])} priority")
    print("=" * 70)
    
    for i, listing in enumerate(display_listings, 1):
        is_new = listing['link'] not in seen_links
        marker = "✨ " if is_new else "   "
        priority = "⭐ " if listing['priority'] else "   "
        status = "🆕 NEW" if is_new else "   "
        
        print(f"\n{i:2d}. {marker}{priority}{listing['title']}")
        print(f"    📂 {listing['category']} | {status}")
        print(f"    🔗 {listing['link']}")
    
    print(f"\n{'=' * 70}")
    if new_count > 0:
        print(f"💡 {new_count} NEW LISTINGS FOUND - Apply ASAP!")
    else:
        print("💡 No new listings - check again later today")
    print("=" * 70)
    
    # Save history
    if SAVE_HISTORY and new_count > 0:
        all_links = seen_links | seen_set
        save_history(all_links)
        print(f"💾 History saved ({len(all_links)} total links)")

# ============================================
# MAIN
# ============================================

def main():
    print("\n🔎 CRAIGSLIST GIG & CASH JOB FINDER")
    print("=" * 70)
    print(f"📍 Location: {SUBAREA.upper()} ({CITY_CODE})")
    print(f"📂 Categories: {len(TARGET_CATEGORIES)}")
    print(f"🚫 Excluding: {len(EXCLUDE_KEYWORDS)} keywords")
    print(f"⭐ Priority: {len(PRIORITY_KEYWORDS)} keywords")
    print("=" * 70)
    
    # Get search URLs
    search_urls = get_search_urls()
    
    if not search_urls:
        print("❌ No search URLs generated. Check configuration.")
        sys.exit(1)
    
    # Fetch listings
    all_listings = []
    seen_links = load_history()
    
    for i, url in enumerate(search_urls, 1):
        listings = fetch_listings_from_search(url)
        all_listings.extend(listings)
        
        if listings:
            print(f"    ✅ Found {len(listings)} listings")
        else:
            print(f"    📭 No listings")
        
        # Be polite - delay between requests
        if i < len(search_urls):
            time.sleep(DELAY_SECONDS)
    
    # Display results
    display_results(all_listings)
    
    print(f"\n🔧 To change location, edit CITY_CODE and SUBAREA")
    print("    Borough codes: 'mnh' (Manhattan), 'brx' (Bronx)")
    print("    'brk' (Brooklyn), 'que' (Queens), 'stn' (Staten Island)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Script cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
