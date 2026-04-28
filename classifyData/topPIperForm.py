import pandas as pd
import sqlite3
from collections import defaultdict


con = sqlite3.connect("./forms.db")

rows = con.execute("""
    SELECT 
        fc.form_type,
        p.pi_type,
        COUNT(*) as count
    FROM form_pi_types p
    JOIN form_classification fc ON p.form_id = fc.form_id
    WHERE fc.form_type IN (
        SELECT form_type
        FROM form_classification
        WHERE form_type NOT IN ('other', 'unknown')
        GROUP BY form_type
        ORDER BY COUNT(*) DESC
        LIMIT 100
    )
    GROUP BY fc.form_type, p.pi_type
    ORDER BY fc.form_type, count DESC
""").fetchall()



form_map = defaultdict(list)

for form_type, pi_type, count in rows:
    form_map[form_type].append((pi_type, count))

TOP_N = 5

df = pd.DataFrame(rows, columns=["form_type", "pi_type", "count"])

from tabulate import tabulate

for form_type, group in df.groupby("form_type"):
    top5 = group.sort_values("count", ascending=False).head(5)

    print(f"\n=== {form_type.upper()} ===")
    print(tabulate(top5[["pi_type", "count"]], headers="keys", tablefmt="github", showindex=False))
