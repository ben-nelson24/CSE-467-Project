from androguard.misc import AnalyzeAPK
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import subprocess
import csv
import re
import os
import shutil



apk_path = Path("../testapk/GooglePlay.apk")
decoded_dir = Path("./decoded_apk")
# apk,dex, analysis = AnalyzeAPK(apk_path)
output = "form_elements.csv"
output_json = "forms.json"

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

# Find xml elements of forms
FORM_TAGS = [
    "EditText",
    "TextInputEditText",
    "AutoCompleteTextView",
    "Spinner",
    "CheckBox",
    "RadioButton",
    "Switch",
    "Button",
    "ImageButton",
]

# Attributes for form behavior
ATTRS = [
    "android:id",
    "android:text",
    "android:hint",
    "android:inputType",
    "android:contentDescription",
    "android:checked",
    "android:enabled",
    "android:maxLength",
    "android:autofillHints",
]

INPUT_TAGS = {
    "EditText",
    "TextInputEditText",
    "AutoCompleteTextView",
    "Spinner",
}


def apk_tool_decode(apk_path: Path, out_dir: Path) -> None:

    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"Using existing decoded output: {out_dir}")
        return
    
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Decoding {apk_path} with apktool")

    cmd = [
        "java",
        "-jar",
        r"C:\Users\bdnel\apktool\apktool.jar",  # full path to your jar
        "d",
        "-f",
        str(apk_path),
        "-o",
        str(out_dir),
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def load_string_resources(decoded_dir: Path) -> dict[str,str]:
    strings: dict[str, str] = {}
    values_dir = decoded_dir / "res" / "values"
    if not values_dir.exists():
        return strings
    
    for xml_file in values_dir.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError:
            continue

        root = tree.getroot()
        if root.tag.split("}")[-1] != "resources":
            continue

        for child in root:
            tag = child.tag.split("}")[-1]
            name = child.attrib.get("name")
            if not name:
                continue

            if tag == "string":
                strings[name] = (child.text or "").strip()
            elif tag == "item" and child.attrib.get("type") == "string":
                strings[name] = (child.text or "").strip()

    return strings

def get_attr(elem: ET.Element, name: str):
    key = name.split(":")[-1]
    return (
        elem.attrib.get(name)
        or elem.attrib.get(f"{ANDROID_NS}{key}")
        or elem.attrib.get(key)
    )

def short_tag(tag: str) -> str:
    return tag.split("}")[-1].split(".")[-1]

def is_form_tag(tag: str) -> bool:
    s = short_tag(tag)
    return s in FORM_TAGS or any(s.endswith(t) for t in FORM_TAGS)

def extract_id_name(value: str | None) -> str | None:
    if not value:
        return None
    
    m = re.fullmatch(r"@\+?id/([A-Za-z0-9_.-]+)", value.strip())

    if m:
        return m.group(1)
    return None

def resolve_value(value: str | None, string_map: dict[str, str]) -> str | None:
    if not value:
        return value
    
    value = value.strip()

    m = re.fullmatch(r"@string/([A-Za-z0-9_.-]+)", value)

    if m:
        return string_map.get(m.group(1), value)
    
    id_name = extract_id_name(value)
    if id_name:
        return id_name
    
    return value

def find_layout_xml_files(decoded_dir: Path) -> list[Path]:
    res_dir = decoded_dir / "res"
    if not res_dir.exists():
        return []
    
    files = []
    for path in res_dir.rglob("*.xml"):
        rel = path.relative_to(decoded_dir).as_posix()
        if rel.startswith("res/values/"):
            continue
        if "/layout" in rel or "/xml/" in rel:
            files.append(path)
    
    return files

def element_to_record(elem: ET.Element, string_map: dict[str, str]) -> dict:
    record = {
        "tag": short_tag(elem.tag),
    }

    for attr in ATTRS:
        raw_val = get_attr(elem, attr)
        record[attr] = resolve_value(raw_val, string_map)

    record["id_name"] = extract_id_name(record.get("android:id"))
    record["text"] = record.get("android:text")
    record["hint"] = record.get("android:hint")
    record["autofill_hints"] = record.get("android:autofillHints")
    record["input_type"] = record.get("android:inputType")
    record["label_for"] = record.get("android:contentDescription")

    return record


def main():
    apk_tool_decode(apk_path, decoded_dir)
    string_map = load_string_resources(decoded_dir)
    layout_files = find_layout_xml_files(decoded_dir)

    print(f"Found {len(layout_files)} XML files under layout/xml paths")

    forms = []
    rows = []

    for xml_file in layout_files:
        try:
            xml_text = xml_file.read_text(encoding="utf-8", errors="ignore")
            xml_obj = ET.fromstring(xml_text)
        except Exception as e:
            print(f"Skipping {xml_file}: {type(e).__name__}: {e}")
            continue

        elements = []
        label_text_by_id = {}

        # Get text labels and id's
        for elem in xml_obj.iter():
            if elem.tag is None:
                continue

            rec = element_to_record(elem, string_map)

            if rec["tag"] == "TextView" and rec["id_name"] and rec["text"]:
                label_text_by_id[rec["id_name"]] = rec["text"]

            elements.append(rec)

        # Keep only form elements
        form_elements = []
        for rec in elements:
            if rec["tag"] not in FORM_TAGS:
                continue

            # Attach label if label references this element
            element_id = rec.get("id_name")
            if element_id:
                rec["label_text"] = label_text_by_id.get(element_id)
            else:
                rec["label_text"] = None
            
            form_elements.append(rec)
            rows.append({
                "file": xml_file.as_posix(),
                **rec,
            })

        #Form if it has at least one field
        if any(e["tag"] in INPUT_TAGS for e in form_elements):
            forms.append({
                "source_file": xml_file.as_posix(),
                "elements": form_elements,
            })

    print(f"For-like layouts found: {len(forms)}")
    print(f"Form elements found: {len(rows)}")

    # Save csv file
    fieldnames = ["file", "tag"] + ATTRS + ["id_name", "label_text", "hint", "text", "autofill_hints", "input_type", "label_for", "content_description"]
    with open (output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved flat export to {output}")

    # save forms to json
    import json
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(forms, f, indent=2, ensure_ascii=False)

    print(f"Saved forms to {output_json}")

    # Preview
    for i, form in enumerate(forms[:5]):
        print(f"\nForm {i+1}: {form['source_file']}")
        for el in form["elements"]:
            if el["tag"] in INPUT_TAGS:
                print(
                    f"  {el['tag']}: "
                    f"hint={el.get('hint')!r}, "
                    f"text={el.get('text')!r}, "
                    f"autofill={el.get('autofill_hints')!r}, "
                    f"inputType={el.get('input_type')!r}, "
                    f"label={el.get('label_text')!r}"
                )
                
    shutil.rmtree(decoded_dir)
    print("Cleaned up decoded APK folder")
    
if __name__ == "__main__":
    main()

# rows = []

# # Debug counters
# total_xml = 0
# layout_xml = 0
# parse_errors = 0

# all_files = list(apk.get_files())
# print(f"Total files in APK: {len(all_files)}")


# xml_files = [f for f in all_files if f.endswith(".xml")]
# print(f"Total XML files: {len(xml_files)}")
# layout_files = [f for f in xml_files if f.startswith("res/layout")]
# print(f"Layout XML files: {len(layout_files)}")
# print("Sample layout files:", layout_files[:10])  # check

# # temp show ALL xml paths
# for f in xml_files[:30]:
#     print(f)

# for file in all_files:
#     if not file.endswith(".xml"):
#         continue

#     total_xml += 1
#     is_layout = file.startswith("res/layout")
#     if not is_layout: 
#         continue

#     layout_xml += 1
#     try:
#         xml_obj = apk.get_xml_obj(file)
#     except Exception as e:
#         parse_errors += 1
#         print(f"  Parse error on {file}: {e}")
#         continue

#     if xml_obj is None:
#         print(f"  xml_obj is None for {file}")
#         continue

#     for elem in xml_obj.iter():
#         tag = elem.tag
#         if tag is None:
#             continue
#         if is_form_tag(tag):
#             row = {
#                 "file": file,
#                 "tag": tag.split("}")[-1],  # strip namespace from tag for readability
#             }
#             for attr in ATTRS:
#                 row[attr] = get_attr(elem, attr)
#             rows.append(row)

# print(f"\n--- Summary ---")
# print(f"XML files scanned: {total_xml}")
# print(f"Layout/manifest files parsed: {layout_xml}")
# print(f"Parse errors: {parse_errors}")
# print(f"Form elements found: {len(rows)}")


# fieldnames = ["file", "tag"] + ATTRS
# with open(output, "w", newline="", encoding="utf-8") as f:
#     writer = csv.DictWriter(f, fieldnames=fieldnames)
#     writer.writeheader()
#     writer.writerows(rows)

# print(f"Saved {len(rows)} rows to {output}")

# # attempt at making forms into objects

# INPUT_TAGS = {"EditText", "TextInputEditText", "AutoCompleteTextView", "Spinner"}

# forms = defaultdict(list)
# for row in rows:
#     forms[row["file"]].append(row)

# form_objects = []
# for layout_file, elements in forms.items():
#     # only treat as a form if it has at least one input-type element
#     has_input = any(el["tag"] in INPUT_TAGS for el in elements)
#     if not has_input:
#         continue

#     form_objects.append({
#         "source_file": layout_file,
#         "element_count": len(elements),
#         "input_fields": [el for el in elements if el["tag"] in INPUT_TAGS],
#         "buttons": [el for el in elements if el["tag"] in {"Button", "ImageButton"}],
#         "all_elements": elements,
#     })

# print(f"\nForm objects identified: {len(form_objects)}")
# for i, form in enumerate(form_objects[:5]):  # preview first 5
#     print(f"\n  Form {i+1}: {form['source_file']}")
#     print(f"    Inputs : {[f.get('android:hint') or f.get('android:text') or f['tag'] for f in form['input_fields']]}")
#     print(f"    Buttons: {[b.get('android:text') or b['tag'] for b in form['buttons']]}")


# for file in layout_files[:5]:
#     try:
#         xml_obj = apk.get_xml_obj(file)
#         print("\nFILE:", file)
#         print("TYPE:", type(xml_obj))
#         if xml_obj is None:
#             print("xml_obj is None")
#             continue

#         for elem in xml_obj.iter():
#             print(repr(elem.tag))
#     except Exception as e:
#         print("ERROR:", file, e)
