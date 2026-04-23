"""
Step 6: Privacy Policy Processing
CSE 467 - Group 7

Pipeline:
  1. Takes package names from AndroZoo CSV or forms.json
  2. Scrapes privacy policy URL from Google Play Store
  3. Downloads the privacy policy text
  4. Compares disclosed PI types against what forms.json collects
  5. Outputs a comparison report CSV flagging violations

Install:
  pip install google-play-scraper requests beautifulsoup4

Usage:
  # Single app:
  python privacy_policy_pipeline.py --package com.duolingo --forms forms.json

  # Full AndroZoo CSV:
  python privacy_policy_pipeline.py --csv androzoo_filtered.csv --forms forms.json
"""

import argparse
import json
import csv
import time
import re
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


# ── Config ────────────────────────────────────────────────────────────────────

POLICY_DIR = Path("privacy_policies")
REPORT_CSV = "privacy_comparison_report.csv"

PI_KEYWORDS = {
    "email":         ["email", "e-mail", "email address"],
    "phone":         ["phone", "telephone", "mobile number", "phone number"],
    "name":          ["first name", "last name", "full name", "your name"],
    "password":      ["password", "passcode", "pin"],
    "address":       ["address", "street", "city", "zip", "postal code"],
    "date_of_birth": ["date of birth", "birthday", "birth date", "dob", "age"],
    "username":      ["username", "user name", "display name", "handle"],
    "credit_card":   ["credit card", "card number", "cvv", "expiry", "payment"],
    "location":      ["location", "gps", "latitude", "longitude", "geolocation"],
    "gender":        ["gender", "sex"],
}


# ── Step 1: Get privacy policy URL from Google Play ───────────────────────────

def get_policy_url(package: str):
    try:
        details = gp_app(package, lang='en', country='us')
        url = details.get('privacyPolicy')
        if url:
            print(f"  [+] Policy URL: {url}")
        else:
            print(f"  [x] No policy URL found on Play Store")
        return url
    except Exception as e:
        print(f"  [!] Play Store lookup failed: {e}")
        return None


# ── Step 2: Download policy text ─────────────────────────────────────────────

def fetch_policy_text(url: str, save_path: Path):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)

        save_path.mkdir(parents=True, exist_ok=True)
        (save_path / "policy.txt").write_text(text, encoding="utf-8")
        print(f"  [+] Policy saved ({len(text):,} chars)")
        return text
    except Exception as e:
        print(f"  [!] Failed to download policy: {e}")
        return None


# ── Step 3: Analyze policy text for PI disclosures ───────────────────────────

def analyze_policy(text: str) -> dict:
    text_lower = text.lower()
    disclosed = {}
    for pi_type, keywords in PI_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in text_lower]
        if matches:
            disclosed[pi_type] = matches
    return disclosed


# ── Step 4: Analyze forms.json for PI collection ─────────────────────────────

def analyze_forms(forms_json_path: str) -> dict:
    with open(forms_json_path, encoding="utf-8") as f:
        forms = json.load(f)

    collected = {}
    for form in forms:
        source = form.get("source_file", "")
        for elem in form.get("elements", []):
            signals = " ".join(filter(None, [
                elem.get("hint") or "",
                elem.get("text") or "",
                elem.get("autofill_hints") or "",
                elem.get("input_type") or "",
                elem.get("id_name") or "",
                elem.get("android:contentDescription") or "",
                elem.get("label_text") or "",
            ])).lower()

            if not signals.strip():
                continue

            for pi_type, keywords in PI_KEYWORDS.items():
                if any(kw in signals for kw in keywords):
                    if pi_type not in collected:
                        collected[pi_type] = []
                    collected[pi_type].append({
                        "file": source,
                        "tag": elem.get("tag"),
                        "signals": signals[:120]
                    })
    return collected


# ── Step 5: Compare and flag violations ──────────────────────────────────────

def compare(package: str, collected: dict, disclosed: dict) -> list:
    all_types = set(list(collected.keys()) + list(disclosed.keys()))
    rows = []
    for pi_type in sorted(all_types):
        in_forms  = pi_type in collected
        in_policy = pi_type in disclosed

        if in_forms and not in_policy:
            status = "VIOLATION - collected but NOT disclosed in policy"
        elif in_forms and in_policy:
            status = "OK - collected and disclosed"
        elif not in_forms and in_policy:
            status = "INFO - disclosed in policy but not found in forms"
        else:
            status = "N/A"

        evidence = " | ".join(
            f"{e['file']} ({e['tag']}): {e['signals']}"
            for e in collected.get(pi_type, [])[:3]
        )

        rows.append({
            "package":        package,
            "pi_type":        pi_type,
            "in_forms":       in_forms,
            "in_policy":      in_policy,
            "status":         status,
            "form_evidence":  evidence,
            "policy_matches": ", ".join(disclosed.get(pi_type, [])),
        })
    return rows


# ── Main per-package flow ─────────────────────────────────────────────────────

def process_package(package: str, forms_json: str) -> list:
    print(f"\n{'='*60}")
    print(f"Package: {package}")
    print(f"{'='*60}")

    out_dir = POLICY_DIR / package
    policy_url = get_policy_url(package)

    disclosed = {}
    if policy_url:
        time.sleep(1)
        text = fetch_policy_text(policy_url, out_dir)
        if text:
            disclosed = analyze_policy(text)
            print(f"  Policy discloses: {list(disclosed.keys()) or ['none found']}")
    else:
        # Check if we already have a saved policy txt
        saved = out_dir / "policy.txt"
        if saved.exists():
            text = saved.read_text(encoding="utf-8")
            disclosed = analyze_policy(text)
            print(f"  Using saved policy. Discloses: {list(disclosed.keys())}")

    collected = analyze_forms(forms_json)
    print(f"  Forms collect:    {list(collected.keys()) or ['none found']}")

    return compare(package, collected, disclosed)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Step 6: Privacy Policy Processing")
    parser.add_argument("--package", help="Single package e.g. com.duolingo")
    parser.add_argument("--csv",     help="AndroZoo CSV (column: apkid or package)")
    parser.add_argument("--forms",   default="forms.json", help="Path to forms.json")
    args = parser.parse_args()

    POLICY_DIR.mkdir(exist_ok=True)
    all_rows = []

    if args.package:
        all_rows = process_package(args.package, args.forms)

    elif args.csv:
        import pandas as pd
        df = pd.read_csv(args.csv)
        pkg_col = "apkid" if "apkid" in df.columns else "package"
        packages = df[pkg_col].dropna().unique().tolist()
        print(f"Found {len(packages)} packages in CSV")
        for pkg in packages:
            all_rows.extend(process_package(pkg, args.forms))
            time.sleep(0.5)

    else:
        # Default demo
        all_rows = process_package("com.duolingo", args.forms)

    if all_rows:
        fieldnames = ["package", "pi_type", "in_forms", "in_policy",
                      "status", "form_evidence", "policy_matches"]
        with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"\n{'='*60}")
        print(f"Report saved to: {REPORT_CSV}")
        violations = [r for r in all_rows if "VIOLATION" in r["status"]]
        ok         = [r for r in all_rows if r["status"].startswith("OK")]
        print(f"  OK (collected + disclosed): {len(ok)}")
        print(f"  Potential violations:       {len(violations)}")
        for v in violations:
            print(f"    - {v['package']}: {v['pi_type']}")


if __name__ == "__main__":
    main()
