import sqlite3
import matplotlib.pyplot as plt


con = sqlite3.connect("./forms.db")

# rows = con.execute("""
#     SELECT pi_type, COUNT(*) 
#     FROM form_pi_types
#     GROUP BY pi_type
#     HAVING COUNT(*) >= 30
#     ORDER BY COUNT(*) DESC
# """).fetchall()

rows = con.execute("""
    SELECT form_type, COUNT(*)
    FROM form_classification
    WHERE form_type != "unknown"
    GROUP BY form_type
    HAVING COUNT(*) >= 20
    ORDER BY COUNT(*) DESC
    LIMIT 15
""").fetchall()

labels = [r[0] for r in rows]
counts = [r[1] for r in rows]

plt.figure()
plt.bar(labels, counts)
plt.xticks(rotation=45)
plt.title("PI Type Classification")
plt.tight_layout()
plt.show()


fig, ax = plt.subplots()
ax.axis('off')  # hide axes

table_data = [[l, c] for l, c in zip(labels, counts)]

table = ax.table(
    cellText=table_data,
    colLabels=["Form Type", "Count"],
    loc='center'
)

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.5)

# plt.title("Top PI Types")
plt.show()