from androguard.misc import AnalyzeAPK
import xml.etree.ElementTree as ET
from collections import defaultdict
import csv
import os


apk_path = r"C:\Users\Teigen\Downloads\com.google.android.youtube_21.10.494-1561059346_minAPI28(arm64-v8a,armeabi-v7a,x86,x86_64)(nodpi)_apkmirror.com.apk"
apk,dex, analysis = AnalyzeAPK(apk_path)



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

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def get_attr(elem, name):
    key = name.split(":")[-1]
    return (
        elem.attrib.get(name)
        or elem.attrib.get(f"{ANDROID_NS}{key}")
        or elem.attrib.get(key)
    )

def is_form_tag(tag: str) -> bool:
    short = tag.split("}")[-1]
    short = short.split(".")[-1]
    return short in FORM_TAGS or any(short.endswith(t) for t in FORM_TAGS)

rows = []

# Debug counters
total_xml = 0
layout_xml = 0
parse_errors = 0

all_files = list(apk.get_files())
print(f"Total files in APK: {len(all_files)}")


xml_files = [f for f in all_files if f.endswith(".xml")]
print(f"Total XML files: {len(xml_files)}")
layout_files = [f for f in xml_files if f.startswith("res/")]
print(f"Layout XML files: {len(layout_files)}")
print("Sample layout files:", layout_files[:10])  # check

# temp show ALL xml paths
for f in xml_files[:30]:
    print(f)

for file in all_files:
    if not file.endswith(".xml"):
        continue

    total_xml += 1
    is_layout = file.startswith("res/layout")
    if not is_layout: 
        continue

    layout_xml += 1
    try:
        xml_obj = apk.get_xml_obj(file)
    except Exception as e:
        parse_errors += 1
        print(f"  Parse error on {file}: {e}")
        continue

    if xml_obj is None:
        print(f"  xml_obj is None for {file}")
        continue

    for elem in xml_obj.iter():
        tag = elem.tag
        if tag is None:
            continue
        if is_form_tag(tag):
            row = {
                "file": file,
                "tag": tag.split("}")[-1],  # strip namespace from tag for readability
            }
            for attr in ATTRS:
                row[attr] = get_attr(elem, attr)
            rows.append(row)

print(f"\n--- Summary ---")
print(f"XML files scanned: {total_xml}")
print(f"Layout/manifest files parsed: {layout_xml}")
print(f"Parse errors: {parse_errors}")
print(f"Form elements found: {len(rows)}")

output = "form_elements.csv"
fieldnames = ["file", "tag"] + ATTRS
with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved {len(rows)} rows to {output}")

# attempt at making forms into objects

INPUT_TAGS = {"EditText", "TextInputEditText", "AutoCompleteTextView", "Spinner"}

forms = defaultdict(list)
for row in rows:
    forms[row["file"]].append(row)

form_objects = []
for layout_file, elements in forms.items():
    # only treat as a form if it has at least one input-type element
    has_input = any(el["tag"] in INPUT_TAGS for el in elements)
    if not has_input:
        continue

    form_objects.append({
        "source_file": layout_file,
        "element_count": len(elements),
        "input_fields": [el for el in elements if el["tag"] in INPUT_TAGS],
        "buttons": [el for el in elements if el["tag"] in {"Button", "ImageButton"}],
        "all_elements": elements,
    })

print(f"\nForm objects identified: {len(form_objects)}")
for i, form in enumerate(form_objects[:5]):  # preview first 5
    print(f"\n  Form {i+1}: {form['source_file']}")
    print(f"    Inputs : {[f.get('android:hint') or f.get('android:text') or f['tag'] for f in form['input_fields']]}")
    print(f"    Buttons: {[b.get('android:text') or b['tag'] for b in form['buttons']]}")