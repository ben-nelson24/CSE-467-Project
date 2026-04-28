"""
Step 6: Privacy Policy Comparison
CSE 467 - Group 7

Reads PI types from forms.db, matches against downloaded policy text,
flags violations where PI is collected but not disclosed.

Usage:
    python privacy_policy_pipeline.py --db forms.db --policies privacy_policies
"""

import argparse
import csv
import sqlite3
import os
from pathlib import Path

PI_KEYWORDS = {
    "email":         ["email", "e-mail", "email address"],
    "phone":         ["phone", "telephone", "mobile number", "phone number"],
    "name":          ["first name", "last name", "full name", "your name", "username"],
    "password":      ["password", "passcode", "pin"],
    "address":       ["address", "street", "city", "zip", "postal code"],
    "date_of_birth": ["date of birth", "birthday", "birth date", "dob", "age"],
    "credit_card":   ["credit card", "card number", "cvv", "expiry", "payment"],
    "location":      ["location", "gps", "latitude", "longitude", "geolocation"],
    "gender":        ["gender", "sex"],
}

def analyze_policy(policy_path: Path) -> dict:
    if not policy_path.exists():
        return {}
    text = policy_path.read_text(encoding="utf-8", errors="ignore").lower()
    disclosed = {}
    for pi_type, keywords in PI_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in text]
        if matches:
            disclosed[pi_type] = matches
    return disclosed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",       default="forms.db",        help="Path to forms.db")
    parser.add_argument("--policies", default="privacy_policies", help="Path to privacy_policies folder")
    parser.add_argument("--urls",     default="privacy_policy_urls.csv", help="Path to URLs CSV")
    args = parser.parse_args()

    POLICY_DIR = Path(args.policies)
    REPORT_CSV = "privacy_comparison_report.csv"

    # Load privacy policy URLs
    policy_urls = {}
    if Path(args.urls).exists():
        with open(args.urls, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                policy_urls[row["package"]] = row.get("url", "")

    # Query forms.db for PI types per app
    print(f"Reading {args.db}...")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT a.pkg_name, p.pi_type, COUNT(*) as count
            FROM form_pi_types p
            JOIN forms f ON p.form_id = f.id
            JOIN apks a ON f.sha256 = a.sha256
            GROUP BY a.pkg_name, p.pi_type
        """)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Query failed: {e}")
        print("Trying alternative table structure...")
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Available tables: {tables}")
        except:
            pass
        conn.close()
        return

    conn.close()

    print(f"Found {len(rows)} PI type records across apps")

    # Group by package
    apps = {}
    for pkg_name, pi_type, count in rows:
        if pkg_name not in apps:
            apps[pkg_name] = []
        apps[pkg_name].append(pi_type)

    print(f"Total unique apps: {len(apps)}")

    # Compare against policies
    report_rows = []
    matched = 0
    violations = 0

    for pkg_name, pi_types in apps.items():
        safe_name = pkg_name.replace(".", "_")
        policy_file = POLICY_DIR / f"{safe_name}.txt"
        disclosed = analyze_policy(policy_file)

        has_policy = policy_file.exists()
        if has_policy:
            matched += 1

        for pi_type in pi_types:
            in_policy = pi_type.lower() in disclosed or any(
                pi_type.lower() in k or k in pi_type.lower()
                for k in disclosed.keys()
            )

            if not has_policy:
                status = "NO POLICY - could not retrieve"
            elif in_policy:
                status = "OK - collected and disclosed"
            else:
                status = "VIOLATION - collected but NOT disclosed"
                violations += 1

            report_rows.append({
                "package":        pkg_name,
                "pi_type":        pi_type,
                "has_policy":     has_policy,
                "in_policy":      in_policy if has_policy else "N/A",
                "status":         status,
                "policy_url":     policy_urls.get(pkg_name, ""),
                "policy_matches": ", ".join(disclosed.get(pi_type.lower(), [])),
            })

    # Write report
    fieldnames = ["package", "pi_type", "has_policy", "in_policy", "status", "policy_url", "policy_matches"]
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"\n{'='*60}")
    print(f"Report saved to: {REPORT_CSV}")
    print(f"Total apps analyzed:     {len(apps)}")
    print(f"Apps with policy found:  {matched}")
    print(f"Apps missing policy:     {len(apps) - matched}")
    print(f"Potential violations:    {violations}")
    print(f"Total rows in report:    {len(report_rows)}")

if __name__ == "__main__":
    main()
