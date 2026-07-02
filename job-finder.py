#!/usr/bin/env python3
"""
Job/Gig Finder for Craigslist Queens
Uses sitemaps (allowed by robots.txt) instead of RSS (broken)
Targets cash gigs, labor, domestic work, trades — no customer service
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
import sys

# ============================================
# CONFIGURATION
# ============================================

# Target categories for cash gigs / no-verification work
# These are the URL endings from the sitemap
TARGET_CATEGORIES = [
    'ggg',                  # All gigs
    'lab',                  # Labor gigs
    'dom',                  # Domestic (cleaning, house work)
    'trd',                  # Trades
    'house-cleaner',        # House cleaning
    'hauling',              # Junk removal / hauling
    'local-movers',         # Moving help
    'construction-jobs',    # Construction
    'handyman',             # Odd jobs / repairs
    'landscaping',          # Yard work
    'warehouse-jobs',       # Warehouse work
    'painter',              # Painting gigs
]

# Keywords to EXCLUDE (customer service, formal employment)
EXCLUDE_KEYWORDS = [
    "customer service",
    "call center",
    "retail",
    "cashier",
    "sales associate",
    "server",
    "bartender",
    "hostess",
    "host",
    "receptionist",
    "front desk",
    "restaurant manager",
    "dental",
    "medical assistant",
    "rn",
    "registered nurse",
    "real estate",
    "insurance",
    "bank",
    "teller",
]

# Keywords to HIGHLIGHT (these are perfect for your situation)
PRIORITY_KEYWORDS = [
    "cash",
    "daily pay",
    "same day",
    "under the table",
    "no experience",
    "helper",
    "clean",
    "cleaning",
    "move",
    "moving",
    "haul",
    "hauling",
    "labor",
    "construction",
    "warehouse",
    "painter",
    "painting",
    "handyman",
    "landscaping",
    "yard",
    "snow",
    "demolición",
    "construcción",
    "limpieza",
    "mudanza",
    "efectivo",
    "hoy pago",
    "sin papeles",
    "trabajo",
    "jornal",
    "jornalero",
]

# Delay between requests (be polite to Craigslist)
DELAY_SECONDS = 3

# Max listings to show
MAX_RESULTS = 30

# ============================================
# STEP 1: Get search URLs from sitemap
# ============================================

def get_search_urls():
    """
    Reads the Queens sitemap and extracts only the search URLs
    that match our target categories.
    """
    sitemap_url = "https://newyork.craigslist.org/sitemap/subarea/que/categories-and-hubs.xml"
    
    print(f"📡 Fetching sitemap: {sitemap_url}")
    
    try:
        response = requests.get(sitemap_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch sitemap: {e}")
        sys.exit(1)
    
    # Parse XML
    root = ET.fromstring(response.content)
    
    # XML namespace handling — Craigslist sitemaps use this namespace
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    # Try with namespace first, fall back to no namespace
    urls = root.findall('.//ns:url/ns:loc', ns)
    if not urls:
        urls = root.findall('.//url/loc')
    
    if not urls:
        print("❌ No URLs found in sitemap. The XML structure may have changed.")
        sys.exit(1)
    
    matching_urls = []
    
    for url in urls:
        full_url = url.text.strip()
        
        # Check if this URL matches any of our target categories
        for category in TARGET_CATEGORIES:
            # Match /que/category or /que/category-name
            if f'/que/{category}' in full_url:
                matching_urls.append(full_url)
                break
    
    print(f"✅ Found {len(matching_urls)} matching search URLs out of {len(urls)} total")
    
    if not matching_urls:
        print("⚠️  No matching categories found. Check TARGET_CATEGORIES list.")
        sys.exit(1)
    
    return matching_urls

# ============================================
# STEP 2: Fetch listings from each search URL
# ============================================

def fetch_listings_from_search(search_url):
    """
    Visits a Craigslist search page and extracts all listing titles and links.
    Returns a list of dicts with 'title', 'link', and 'priority' keys.
    """
    listings = []
    
    try:
        print(f"  🔍 Searching: {search_url}")
        response = requests.get(search_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Failed to fetch {search_url}: {e}")
        return listings
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Craigslist listing structure: each result is in a <li> with class "cl-search-result"
    # The title link is inside <a class="titlestring">
    results = soup.find_all('li', class_='cl-search-result')
    
    if not results:
        # Try alternative class names (Craigslist changes these occasionally)
        results = soup.find_all('li', class_='result-row')
    
    for result in results:
        # Find the title link
        link_tag = result.find('a', class_='titlestring')
        if not link_tag:
            link_tag = result.find('a', class_='result-title')
        if not link_tag:
            link_tag = result.find('a', href=True)  # Last resort: any link
        
        if not link_tag or not link_tag.get('href'):
            continue
        
        title = link_tag.text.strip()
        link = link_tag['href']
        
        # Craigslist gives relative URLs — make them absolute
        if link.startswith('/'):
            link = f"https://newyork.craigslist.org{link}"
        
        # Skip empty titles
        if not title:
            continue
        
        # Check exclusion keywords
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
        })
    
    return listings

# ============================================
# STEP 3: Combine, sort, and display
# ============================================

def display_results(all_listings):
    """
    Sorts listings (priority first), removes duplicates, and displays.
    """
    if not all_listings:
        print("\n" + "=" * 70)
        print("😔 NO LISTINGS FOUND")
        print("=" * 70)
        print("\nThis could mean:")
        print("  - No new listings in your target categories today")
        print("  - Craigslist changed their HTML structure (needs script update)")
        print("  - Your network is blocking the requests")
        print("\nTry manually:")
        print("  https://newyork.craigslist.org/search/que/ggg")
        return
    
    # Remove duplicates (same link)
    seen_links = set()
    unique_listings = []
    for listing in all_listings:
        if listing['link'] not in seen_links:
            seen_links.add(listing['link'])
            unique_listings.append(listing)
    
    # Sort: priority first, then alphabetically
    unique_listings.sort(key=lambda x: (not x['priority'], x['title'].lower()))
    
    # Limit results
    display_listings = unique_listings[:MAX_RESULTS]
    
    print("\n" + "=" * 70)
    print(f"🎯 FOUND {len(unique_listings)} LISTINGS ({len(display_listings)} shown)")
    print(f"   ⭐ = Priority (cash gig, labor, cleaning, construction, etc.)")
    print("=" * 70)
    
    for i, listing in enumerate(display_listings, 1):
        marker = "⭐ " if listing['priority'] else "   "
        print(f"\n{i:2d}. {marker}{listing['title']}")
        print(f"    {listing['link']}")
    
    # Summary
    priority_count = sum(1 for l in unique_listings if l['priority'])
    print(f"\n{'=' * 70}")
    print(f"Summary: {len(unique_listings)} total | {priority_count} priority matches")
    print(f"Sources checked: {len(TARGET_CATEGORIES)} categories")
    print(f"{'=' * 70}")

# ============================================
# MAIN
# ============================================

def main():
    print("\n🔎 CRAIGSLIST QUEENS — GIG & CASH JOB FINDER")
    print("=" * 70)
    print(f"Target categories: {len(TARGET_CATEGORIES)}")
    print(f"Excluding: {len(EXCLUDE_KEYWORDS)} keywords (customer service, retail, etc.)")
    print(f"Highlighting: {len(PRIORITY_KEYWORDS)} priority keywords (cash, labor, etc.)")
    print("=" * 70)
    
    # Step 1: Get search URLs from sitemap
    search_urls = get_search_urls()
    
    # Step 2: Fetch listings from each search URL
    all_listings = []
    
    for i, url in enumerate(search_urls, 1):
        listings = fetch_listings_from_search(url)
        all_listings.extend(listings)
        
        if listings:
            print(f"    ✅ Found {len(listings)} listings")
        else:
            print(f"    📭 No listings in this category")
        
        # Be polite — delay between requests
        if i < len(search_urls):
            time.sleep(DELAY_SECONDS)
    
    # Step 3: Display results
    display_results(all_listings)
    
    print("\n💡 TIP: Run this during your job search block (9:30-10:30 AM)")
    print("💡 TIP: Craigslist updates throughout the day — check morning and evening")

if __name__ == "__main__":
    """
    How this script works:
    1. Reads Craigslist's sitemap (allowed by robots.txt) to find search URLs
    2. Filters to only the categories you want (gigs, labor, cleaning, etc.)
    3. Visits each search page and extracts listing titles and links
    4. Filters out customer service / formal jobs
    5. Highlights cash gigs and no-verification work with a ⭐
    6. Displays everything sorted with priority first
    
    To run:
        python ~/Scripts/Python/job-finder.py
    
    Requirements:
        pip install requests beautifulsoup4 lxml
    """
    main()
