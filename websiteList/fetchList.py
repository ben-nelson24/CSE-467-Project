import argparse
import csv
import sqlite3

#Based off of fetch-tranco-list.py

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="SQLite database path")
    args = parser.parse_args()
    con = sqlite3.connect(args.database)
    con.execute('''
    CREATE TABLE IF NOT EXISTS apk_data (
        sha256 TEXT,
        sha1 TEXT,
        md5 TEXT,
        dex_date TEXT,
        apk_size INTEGER,
        pkg_name TEXT,
        vercode INTEGER,
        vt_detection INTEGER,
        vt_scan_date TEXT,
        dex_size INTEGER,
        markets TEXT
    )''')

    rows = []

    with open('filtered.csv', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if(len(row) != 11):
                continue
            rows.append(tuple(row))

    con.executemany('''INSERT INTO apk_data (
                        sha256, sha1, md5, dex_date, apk_size,
                        pkg_name, vercode, vt_detection,
                        vt_scan_date, dex_size, markets
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', rows)
    con.commit()
    con.close()
    print("Done.")


if __name__ == "__main__":
    main()

#@inproceedings{Allix:2016:ACM:2901739.2903508,
#    author = {Allix, Kevin and Bissyand{\'e}, Tegawend{\'e} F. and Klein, Jacques and Le Traon, Yves},
#    title = {AndroZoo: Collecting Millions of Android Apps for the Research Community},
#    booktitle = {Proceedings of the 13th International Conference on Mining Software Repositories},
#    series = {MSR '16},
#    year = {2016},
#    isbn = {978-1-4503-4186-8},
#    location = {Austin, Texas},
#    pages = {468--471},
#    numpages = {4},
#    url = {http://doi.acm.org/10.1145/2901739.2903508},
#    doi = {10.1145/2901739.2903508},
#    acmid = {2903508},
#    publisher = {ACM},
#    address = {New York, NY, USA},
#    keywords = {APK, android applications, software repository},
#    }