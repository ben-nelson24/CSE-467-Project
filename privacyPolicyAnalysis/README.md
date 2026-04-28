# CSE 467 - Group 7 Privacy Policy Processing
We make use of privacy_policy_pipeline.py to run our analysis

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
