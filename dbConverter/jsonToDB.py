import argparse
import glob
import json
import sqlite3


def create_tables(con):
    con.executescript('''
                      CREATE TABLE IF NOT EXISTS apks (
                                                          sha256      TEXT PRIMARY KEY,
                                                          pkg_name    TEXT,
                                                          forms_found INTEGER
                      );

                      CREATE TABLE IF NOT EXISTS forms (
                                                           id          INTEGER PRIMARY KEY AUTOINCREMENT,
                                                           sha256      TEXT NOT NULL REFERENCES apks(sha256),
                          source_file TEXT
                          );

                      CREATE TABLE IF NOT EXISTS form_elements (
                                                                   id                        INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                   form_id                   INTEGER NOT NULL REFERENCES forms(id),
                          tag                       TEXT,
                          android_id                TEXT,
                          android_text              TEXT,
                          android_hint              TEXT,
                          android_input_type        TEXT,
                          android_content_desc      TEXT,
                          android_checked           TEXT,
                          android_enabled           TEXT,
                          android_max_length        TEXT,
                          android_autofill_hints    TEXT,
                          id_name                   TEXT,
                          text                      TEXT,
                          hint                      TEXT,
                          autofill_hints            TEXT,
                          input_type                TEXT,
                          label_for                 TEXT,
                          label_text                TEXT
                          );
                      ''')


def ingest_file(con, path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    sha256      = data.get('sha256')
    pkg_name    = data.get('pkg_name')
    forms_found = data.get('forms_found', 0)
    forms       = data.get('forms', [])

    con.execute('''
                INSERT OR IGNORE INTO apks (sha256, pkg_name, forms_found)
        VALUES (?, ?, ?)
                ''', (sha256, pkg_name, forms_found))

    for form in forms:
        source_file = form.get('source_file')

        cur = con.execute('''
                          INSERT INTO forms (sha256, source_file)
                          VALUES (?, ?)
                          ''', (sha256, source_file))
        form_id = cur.lastrowid

        elements = form.get('elements', [])
        rows = []
        for el in elements:
            rows.append((
                form_id,
                el.get('tag'),
                el.get('android:id'),
                el.get('android:text'),
                el.get('android:hint'),
                el.get('android:inputType'),
                el.get('android:contentDescription'),
                el.get('android:checked'),
                el.get('android:enabled'),
                el.get('android:maxLength'),
                el.get('android:autofillHints'),
                el.get('id_name'),
                el.get('text'),
                el.get('hint'),
                el.get('autofill_hints'),
                el.get('input_type'),
                el.get('label_for'),
                el.get('label_text'),
            ))

        con.executemany('''
                        INSERT INTO form_elements (
                            form_id, tag,
                            android_id, android_text, android_hint,
                            android_input_type, android_content_desc,
                            android_checked, android_enabled, android_max_length,
                            android_autofill_hints,
                            id_name, text, hint, autofill_hints,
                            input_type, label_for, label_text
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', rows)

    print(f"Used {sha256[:16]}… ({pkg_name})  —  {len(forms)} forms")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("database", help="SQLite database path (created if absent)")
    parser.add_argument("json_files", nargs="+", help="One or more JSON files to use",)
    args = parser.parse_args()

    paths = []
    for pattern in args.json_files:
        expanded = glob.glob(pattern)
        paths.extend(expanded if expanded else [pattern])

    con = sqlite3.connect(args.database)
    con.execute("PRAGMA foreign_keys = ON")
    create_tables(con)

    for path in paths:
        try:
            ingest_file(con, path)
        except Exception as e:
            print(f"ERROR at {path}: {e}")

    con.commit()
    con.close()
    print(f"\nDone. Files created: {len(paths)}")


if __name__ == "__main__":
    main()


# @inproceedings{Allix:2016:ACM:2901739.2903508,
#     author = {Allix, Kevin and Bissyand{\'e}, Tegawend{\'e} F. and Klein, Jacques and Le Traon, Yves},
#     title = {AndroZoo: Collecting Millions of Android Apps for the Research Community},
#     booktitle = {Proceedings of the 13th International Conference on Mining Software Repositories},
#     series = {MSR '16},
#     year = {2016},
#     isbn = {978-1-4503-4186-8},
#     location = {Austin, Texas},
#     pages = {468--471},
#     numpages = {4},
#     url = {http://doi.acm.org/10.1145/2901739.2903508},
#     doi = {10.1145/2901739.2903508},
#     acmid = {2903508},
#     publisher = {ACM},
#     address = {New York, NY, USA},
#     keywords = {APK, android applications, software repository},
# }
