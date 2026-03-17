import argparse
import json
import os
import sqlite3

import CloudFlare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="SQLite database path")
    args = parser.parse_args()

    con = sqlite3.connect(args.database)
    con.execute('''
    CREATE TABLE IF NOT EXISTS domain_info (
        domain TEXT UNIQUE NOT NULL,
        application TEXT NOT NULL,
        content_categories TEXT NOT NULL,
        additional_information TEXT NOT NULL,
        type TEXT NOT NULL,
        notes TEXT NOT NULL
    ) STRICT
    ''')

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    batch_size = 8

    done_set = set()

    for domain in con.execute('SELECT domain FROM domain_info'):
        done_set.add(domain)

    with CloudFlare.CloudFlare() as cf:
        cur = con.execute('''
        SELECT domain
        FROM tranco_list t
        WHERE NOT EXISTS(SELECT NULL FROM domain_info d WHERE t.domain = d.domain)
        ORDER BY ranking
        ''')

        while True:
            domain_batch = [i[0] for i in cur.fetchmany(batch_size)]

            if not domain_batch:
                break

            print("Batch:", ", ".join(domain_batch))

            params = [("domain", d) for d in domain_batch]
            answers = cf.accounts.intel.domain.bulk.get(account_id, params=params)
            rows = []

            for ans in answers:
                print(ans)
                rows.append((
                    ans["domain"],
                    json.dumps(ans["application"]),
                    json.dumps(ans.get("content_categories", [])),
                    json.dumps(ans["additional_information"]),
                    ans["type"],
                    ans["notes"],
                ))

            con.executemany('INSERT INTO domain_info VALUES (?, ?, ?, ?, ?, ?)', rows)
            con.commit()

    print("Done!")


if __name__ == "__main__":
    main()
