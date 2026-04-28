import sqlite3
from collections import defaultdict
import json
from openai import OpenAI
import re



db_path = "./forms.db"

# fetch forms and form elements from the db
def fetch_forms(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    query = """ 
    SELECT
        f.id AS form_id,
        f.source_file,
        e.*
    FROM forms f
    JOIN form_elements e ON f.id = e.form_id
    """

    forms = defaultdict(list)

    for row in con.execute(query):
        forms[row["form_id"]].append(dict(row))

    con.close()
    return forms

def normalize_element(el):
    return {
        "label": el.get("label_text") or el.get("text") or el.get("android_text"),
        "hint": el.get("hint") or el.get("android_hint"),
        "type": el.get("input_type") or el.get("android_input_type"),
        "autofill": el.get("autofill_hints") or el.get("android_autofill_hints"),
        "id": el.get("id_name") or el.get("android_id")
    } 

# build payload to send to api
def build_form_payload(elements):
    fields = []

    for el in elements:

        # norm = normalize_element(el)

        # # skip completely empty fields
        # if not any(norm.values()):
        #     continue

        fields.append(el)

    return {"fields": fields}

# iterate forms for individual analysis
def iterate_forms(db_path):
    forms = fetch_forms(db_path)

    for form_id, elements in forms.items():
        payload = build_form_payload(elements)

        if not payload["fields"]:
            continue
            
        yield form_id, payload


# Make call to OpenAI endpoint for PI Classification
def pi_analysis(payload):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": f"""
Please analyze the form and identify the types of personal data that are being requested in the form fields.

"Personal data" (or "personal information") should be understood according to the following definitions in privacy laws:

1. **California Consumer Privacy Act (CCPA)**
2. **General Data Protection Regulation (GDPR)**

Please analyze the given extracted XML form elements and identify fields that may collect personal data as per these definitions.

The output should be in JSON format and include concise and easily interpretable noun phrases that clearly indicate each type of personal data being requested, for example: `\{{ "personal_data_types": ["Name", "Email Address", "Phone Number"] }}`

STRICT RULES:
- Return ONLY raw JSON
- Do NOT use markdown code blocks
- Do NOT include ``` or any formatting
- Always return:
  {{ "personal_data_types": ["..."] }}
- If none:
  {{ "personal_data_types": [] }}

Form:
{payload}
"""
        }]
    )

    return response.output[0].content[0].text

def create_analysis_tables(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS form_analysis (
        form_id INTEGER PRIMARY KEY,
        pi_types_json TEXT
    );

    CREATE TABLE IF NOT EXISTS form_pi_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER,
        pi_type TEXT
    );
    """)

# clean json result if needed
def clean_json_string(s):
    if not s:
        return s

    # remove ```json ... ``` or ``` ... ```
    s = re.sub(r"^```(?:json)?\s*", "", s.strip())
    s = re.sub(r"\s*```$", "", s.strip())

    return s

# store json results back to db
def store_results(con, form_id, result_json):
    cleaned = clean_json_string(result_json)

    try:
        data = json.loads(cleaned)
    except Exception:
        print(f"Bad JSON for form {form_id}: {result_json}")
        data = {"personal_data_types": []}

    pi_types = data.get("personal_data_types", [])

    # clear old entries
    con.execute("DELETE FROM form_pi_types WHERE form_id = ?", (form_id,))

    # insert normalized rows
    for pi in pi_types:
        con.execute(
            "INSERT INTO form_pi_types (form_id, pi_type) VALUES (?, ?)",
            (form_id, pi)
        )

# get count of pi types
def get_pi_counts(con):
    rows = con.execute("""
        SELECT pi_type, COUNT(*) 
        FROM form_pi_types 
        GROUP BY pi_type
        ORDER BY COUNT(*) DESC
    """).fetchall()

    return rows

# get list of pi stuff
def get_pi_types(con, form_id):
    rows = con.execute(
        "SELECT pi_type FROM form_pi_types WHERE form_id = ?",
        (form_id,)
    ).fetchall()

    return [r[0] for r in rows]

# Create payload for form classification
def classiy_form_payload(pi_types, fields):
    return{
        "pi_types": pi_types,
        "fields": fields
    }

# OpenAI api call for form classification
def classify_form(payload):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": f"""

Analyze the provided collected privacy information and xml form elements from an app form and infer the purpose of that form (i.e signup, purchase, profile, etc.)

Please use a simple phrase to describe the usage of the form.

If insufficient information is available to determine the usage, classify the form as "unknown".

The response should be in JSON format with a single key "Classification".

Return JSON:
{{ "Classification": "<formtype>" }}

Rules:
- always return a json output
- Return ONLY raw JSON
- Do NOT use markdown code blocks
- Do NOT include ``` or any formatting

Data:
{payload}
"""
        }]
    )
    return response.output[0].content[0].text

# create classification table for DB
def create_classification_tables(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS form_classification (
        form_id INTEGER PRIMARY KEY,
        form_type TEXT
    );
    """)

# store classifiation into db
def store_form_classification(con, form_id, result_json):
    data = json.loads(result_json)
    form_type = data.get("Classification", "other")

    con.execute(
        "INSERT OR REPLACE INTO form_classification (form_id, form_type) VALUES (?, ?)",
        (form_id, form_type)
    )

#_____________Main_____________________ #
# Create open AI Clients
client = OpenAI(api_key="")

con = sqlite3.connect(db_path)

create_analysis_tables(con)

 # analyze for PI classification
for form_id, payload in iterate_forms(db_path):
    try:
        result = pi_analysis(payload)
        store_results(con, form_id, result)

        print(f"Processed form {form_id}")
        print(result)

    except Exception as e:
        print(f"Error on form {form_id}: {e}")

print(get_pi_counts(con))

create_classification_tables(con)

# analyze for form classification
for form_id, payload in iterate_forms(db_path):
    try:
        pi_types = get_pi_types(con, form_id)
        classifier_payload = classiy_form_payload(pi_types, payload["fields"])

        result = classify_form(classifier_payload)

        store_form_classification(con, form_id, result)
        print(result)

        print(f"Classified form {form_id}")
    
    except Exception as e:
            print(f"Error on form {form_id}: {e}")

con.commit()
con.close()

