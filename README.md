# Job Finder Pro

One script. Every job you need — local gigs + remote tech roles.

## Features

- 🔍 **Local Gigs** — Craigslist scraper for cash jobs, labor, cleaning, moving
- 🌐 **Remote Tech Jobs** — Remotive, RemoteOK, WeWorkRemotely APIs
- 🔎 **Built-in Search** — Filter by keyword: `-s "python, cash, cleaning"`
- 💾 **Save to File** — Output to `~/Documents/` with `-o filename.txt`
- 🆕 **Smart History** — Tracks new vs. seen listings automatically
- 🏷️ **Priority Badges** — ⭐ cash/priority, 🤖 AI roles
- 🖥️ **Cross-Platform** — Linux, Windows, Mac

## Quick Start

```bash
# Install dependencies
pip install requests beautifulsoup4

# Everything (local + remote, print to terminal)
python job-finder-pro.py

# Filter by keyword
python job-finder-pro.py -s "python"
python job-finder-pro.py -s "cash, cleaning"

# Save to file
python job-finder-pro.py -s "ai, react" -o tech_jobs.txt
