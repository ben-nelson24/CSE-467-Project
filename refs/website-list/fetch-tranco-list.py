import argparse
import csv
import io
import sqlite3
import zipfile

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tranco-id", default="82NJV",
                        help="ID of the Tranco list to use")
    parser.add_argument("database", help="SQLite database path")

    args = parser.parse_args()

    con = sqlite3.connect(args.database)
    con.execute('''CREATE TABLE IF NOT EXISTS tranco_list (
        ranking INTEGER PRIMARY KEY,
        domain TEXT UNIQUE NOT NULL
    ) STRICT''')

    url = f"https://tranco-list.s3.amazonaws.com/tranco_{args.tranco_id}-1m.csv.zip"

    r = requests.get(url)
    r.raise_for_status()
    rows = []

    with zipfile.ZipFile(io.BytesIO(r.content)) as zipf:
        with zipf.open('top-1m.csv', 'r') as fb:
            ft = io.TextIOWrapper(fb, encoding='utf-8', newline='')

            for ranking, domain in csv.reader(ft):
                rows.append((int(ranking), domain))

    con.executemany('INSERT INTO tranco_list VALUES (?, ?)', rows)
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
