import csv
import requests
import subprocess
import shutil
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from analyze_apk import load_string_resources, find_layout_xml_files, element_to_record, INPUT_TAGS, FORM_TAGS


API_KEY = os.environ.get("ANDROZOO_API_KEY")

APKTOOL_JAR = "/Users/meshari/Downloads/apktool.jar"

FILTERED_CSV = "./filtered.csv"

# where we save the results for each app
OUTPUT_DIR = Path("./results")

# temp folder apktool dumps the decoded apk into
DECODED_DIR = Path("./decoded_apk")

# keeping this small for now to test, can bump it up later
MAX_APPS = 1

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

    # run the actual form analysis on the decoded apk
    string_map = load_string_resources(DECODED_DIR)
    layout_files = find_layout_xml_files(DECODED_DIR)
    
    forms = []
    for xml_file in layout_files:
        try:
            import xml.etree.ElementTree as ET
            xml_text = xml_file.read_text(encoding="utf-8", errors="ignore")
            xml_obj = ET.fromstring(xml_text)
        except Exception:
            continue

        elements = []
        label_text_by_id = {}
        for elem in xml_obj.iter():
            if elem.tag is None:
                continue
            rec = element_to_record(elem, string_map)
            if rec["tag"] == "TextView" and rec["id_name"] and rec["text"]:
                label_text_by_id[rec["id_name"]] = rec["text"]
            elements.append(rec)

        form_elements = []
        for rec in elements:
            if rec["tag"] not in FORM_TAGS:
                continue
            element_id = rec.get("id_name")
            rec["label_text"] = label_text_by_id.get(element_id) if element_id else None
            form_elements.append(rec)

        if any(e["tag"] in INPUT_TAGS for e in form_elements):
            forms.append({
                "source_file": xml_file.as_posix(),
                "elements": form_elements,
            })

    # save the forms for this app
    result_file = OUTPUT_DIR / f"{sha256[:16]}_{pkg_name}.json"
    with open(result_file, "w") as f:
        json.dump({
            "sha256": sha256,
            "pkg_name": pkg_name,
            "forms_found": len(forms),
            "forms": forms
        }, f, indent=2)
    
    print(f"Found {len(forms)} forms in {pkg_name}")

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
    main()
