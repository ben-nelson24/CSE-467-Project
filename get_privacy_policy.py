"""
Google Play Store - Privacy Policy Scraper
CSE 467 Group 7 - Step 6

Install:
    pip install google-play-scraper requests beautifulsoup4 selenium webdriver-manager

Usage:
    python get_privacy_policy.py --file Packages.txt
    python get_privacy_policy.py --package com.duolingo
"""

import argparse
import csv
import re
import time
from pathlib import Path

try:
    from google_play_scraper import app as gp_app
except ImportError:
    print("Run: pip install google-play-scraper")
    exit(1)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Run: pip install requests beautifulsoup4")
    exit(1)

OUTPUT_DIR = Path("privacy_policies")
URLS_CSV   = "privacy_policy_urls.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def get_policy_url(package: str):
    try:
        details = gp_app(package, lang='en', country='us')
        return details.get('privacyPolicy')
    except Exception as e:
        print(f"  [!] Play Store lookup failed: {e}")
        return None


def download_with_requests(url: str):
    """Try plain requests first."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # If we got real content (not just a title/redirect)
        if len(text) > 500:
            return text
        return None
    except Exception:
        return None


def download_with_selenium(url: str):
    """Fall back to Selenium if requests didn't get enough content."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.get(url)
        time.sleep(3)  # wait for JS to load

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text if len(text) > 500 else None

    except ImportError:
        print("  [!] Selenium not installed. Run: pip install selenium webdriver-manager")
        return None
    except Exception as e:
        print(f"  [!] Selenium failed: {e}")
        return None


def process_package(package: str) -> dict:
    print(f"\nPackage: {package}")
    result = {"package": package, "url": None, "status": "not found"}

    url = get_policy_url(package)
    if not url:
        print(f"  [x] No privacy policy URL on Play Store")
        return result

    result["url"] = url
    print(f"  [+] URL: {url}")

    # Try requests first (fast)
    print(f"  ... trying requests")
    text = download_with_requests(url)

    # Fall back to Selenium (handles JS-heavy pages)
    if not text:
        print(f"  ... requests got too little content, trying Selenium")
        text = download_with_selenium(url)

    if not text:
        print(f"  [x] Could not download policy text")
        result["status"] = "url found, download failed"
        return result

    OUTPUT_DIR.mkdir(exist_ok=True)
    safe_name = package.replace(".", "_")
    out_file = OUTPUT_DIR / f"{safe_name}.txt"
    out_file.write_text(text, encoding="utf-8")
    print(f"  [+] Saved {out_file} ({len(text):,} chars)")

    result["status"] = "success"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", help="Single package e.g. com.duolingo")
    parser.add_argument("--file",    help="Text file, one package per line")
    parser.add_argument("--csv",     help="AndroZoo CSV file")
    args = parser.parse_args()

    packages = []
    if args.package:
        packages = [args.package]
    elif args.file:
        with open(args.file) as f:
            packages = [l.strip() for l in f if l.strip()]
    elif args.csv:
        import pandas as pd
        df = pd.read_csv(args.csv)
        col = "apkid" if "apkid" in df.columns else "package"
        packages = df[col].dropna().unique().tolist()
    else:
        packages = ["com.duolingo", "com.instagram.android", "com.spotify.music"]

    results = []
    for pkg in packages:
        result = process_package(pkg)
        results.append(result)
        time.sleep(1)

    with open(URLS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["package", "url", "status"])
        writer.writeheader()
        writer.writerows(results)

    success = [r for r in results if r["status"] == "success"]
    print(f"\n{'='*50}")
    print(f"Done! {len(success)}/{len(results)} policies saved to privacy_policies/")
    print(f"URLs saved to {URLS_CSV}")


if __name__ == "__main__":
    main()
