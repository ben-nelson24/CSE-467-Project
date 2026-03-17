import argparse
import json
import sqlite3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="SQLite database path")
    args = parser.parse_args()

    con = sqlite3.connect(args.database)
    cur = con.execute('''
    SELECT domain, application, content_categories, url
    FROM tranco_list
         JOIN domain_info USING (domain)
         JOIN http_info USING (domain)
    WHERE lang IN ('en', 'guess:en')
          AND domain_has_changed = 0
          AND type = 'Apex domain'
    ORDER BY ranking;
    ''')

    blocked_categories = {'CIPA', 'Adult Themes', 'Questionable Content', 'Blocked'}
    visited_applications = set()

    for domain, application_json, content_categories_json, url in cur:
        application = json.loads(application_json)
        content_categories = json.loads(content_categories_json)

        if not blocked_categories.isdisjoint(i['name'] for i in content_categories):
            continue

        if application:
            if application['name'] in visited_applications:
                continue

            visited_applications.add(application['name'])

        print(domain, url)

if __name__ == '__main__':
    main()
