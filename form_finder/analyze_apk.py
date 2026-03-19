from androguard.misc import AnalyzeAPK
import xml.etree.ElementTree as ET
from collections import defaultdict
import csv
import os

apk_path = "../testapk/youtube.apk"
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


for file in apk.get_files():
        
        if not file.endswith(".xml"):
            continue
        if not file.startswith("res/layout/") and file != "AndroidManifest.xml":
            continue
        
        try:
            xml_obj = apk.get_xml_obj(file)
        except Exception:
            continue
        
        for elem in xml_obj.iter():
            tag = elem.tag.split("}")[-1]
            if is_form_tag(tag):
                row = {
                    "file": file,
                    "tag" : tag,
                }  
                for attr in ATTRS:
                    row[attr] = get_attr(elem, attr)
                rows.append(row)      

# Write results to csv file
output = "form_elements.csv"
with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["xml_file", "tag"] + ATTRS)
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved {len(rows)} rowss to {output}")