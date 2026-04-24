import csv
import requests
import subprocess
import shutil
import json
import os
from pathlib import Path

API_KEY = "apikey"

APKTOOL_JAR = "/Users/meshari/Downloads/apktool.jar"

FILTERED_CSV = "./filtered.csv"

# where we save the results for each app
OUTPUT_DIR = Path("./results")

# temp folder apktool dumps the decoded apk into
DECODED_DIR = Path("./decoded_apk")

# keeping this small for now to test, can bump it up later
MAX_APPS = 10

OUTPUT_DIR.mkdir(exist_ok=True)

def download_apk(sha256, out_path):
    # use the androzoo api to download the apk by its sha256 hash
    url = f"https://androzoo.uni.lu/api/download?apikey={API_KEY}&sha256={sha256}"
    print(f"Downloading {sha256[:16]}...")
    response = requests.get(url, stream=True, timeout=60)
    if response.status_code == 200:
        with open(out_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    else:
        print(f"Failed to download: {response.status_code}")
        return False

def decode_apk(apk_path, out_dir):
    # wipe old decoded folder if it exists so we start fresh each time
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["java", "-jar", APKTOOL_JAR, "d", "-f", str(apk_path), "-o", str(out_dir)]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0

def run_analysis(sha256, pkg_name):
    apk_path = Path(f"./temp_{sha256[:8]}.apk")
    
    
    if not download_apk(sha256, apk_path):
        return
    
    
    print(f"Decoding {pkg_name}...")
    if not decode_apk(apk_path, DECODED_DIR):
        print(f"Failed to decode {pkg_name}, skipping")
        apk_path.unlink(missing_ok=True)
        return

    # save a result file for each app, will hook up the full analysis later
    result_file = OUTPUT_DIR / f"{sha256[:16]}_{pkg_name}.json"
    with open(result_file, "w") as f:
        json.dump({"sha256": sha256, "pkg_name": pkg_name, "status": "decoded"}, f)

    # cleanup after each apk so we dont run out of storage
    apk_path.unlink(missing_ok=True)
    shutil.rmtree(DECODED_DIR)
    print(f"Done: {pkg_name}")

def main():
    # read through the filtered csv and process each app one by one
    with open(FILTERED_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= MAX_APPS:
                break
            if len(row) < 6:
                continue
            sha256 = row[0]
            pkg_name = row[5].strip('"')
            print(f"\nApp {i+1}/{MAX_APPS}: {pkg_name}")
            run_analysis(sha256, pkg_name)

if __name__ == "__main__":
