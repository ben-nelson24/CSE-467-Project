## Step 1: Website List and Categorization

In Section 3.2 (Web Forms Dataset) of our paper, we describe how we selected the top websites from the Tranco List and used the Cloudflare API to categorize them. The corresponding code is provided here.

### Step 1.1: Fetching the Tranco List

Use `fetch-tranco-list.py` to download the Tranco List (default version `82NJV`) and save it into a SQLite database (`domain.db`):

```console
$ cd website-list/
$ python fetch-tranco-list.py domain.db
```

You can verify the list by checking the `tranco_list` table in the database:

```console
$ sqlite3 -header domain.db 'SELECT * FROM tranco_list LIMIT 4'
ranking|domain
1|google.com
2|facebook.com
3|amazonaws.com
4|microsoft.com
```

### Step 1.2: Domain Categorization

Use `fetch-cf-intel.py` to retrieve domain categorization data via Cloudflare's domain intelligence API. A Cloudflare API key/token is required:

```console
$ export CLOUDFLARE_ACCOUNT_ID=...
$ export CLOUDFLARE_EMAIL=...
$ export CLOUDFLARE_API_KEY=...
$ python fetch-cf-intel.py domain.db
```

The results will be saved into the `domain_info` table in the database:

```console
$ sqlite3 -header domain.db "SELECT * FROM domain_info WHERE domain = 'chase.com'"
domain|application|content_categories|additional_information|type|notes
chase.com|{"id":786,"name":"Chase Bank (Do Not Inspect)"}|[{"id":89,"super_category_id":3,"name":"Economy & Finance"},{"id":3,"name":"Business & Economy"}]|{}|Apex domain|Apex domain given.
```

### Step 1.3: Probing HTTP Services

Use `test-http-connection.py` to check whether a reachable HTTP(s) service exists on each domain:

```console
$ python test-http-connection.py domain.db
```

The results will be stored in the `http_info` table in the database. This table also contains information about HTTP redirections and homepage language:

```console
$ sqlite3 -header domain.db "SELECT * FROM http_info WHERE domain = 'chase.com'"
domain|ip|url|redirected_url|lang|domain_has_changed
chase.com|159.53.224.21|http://chase.com|https://www.chase.com/|en|0
```

### Step 1.4: Generating the List of Websites

Finally, use `filter-websites.py` to generate a list of domains and homepage URLs to crawl. This script takes into account the information from previous steps and excludes domains that meet exclusion criteria (e.g., malicious websites) as described in the paper:

```console
$ python filter-websites.py domain.db
google.com http://google.com
facebook.com http://facebook.com
microsoft.com http://microsoft.com
......
```

### Artifacts

In our released artifacts, `domain.db.zst` is a compressed SQLite database containing the results up to this step. You can decompress it to get `domain.db` using the following command:

```console
$ zstd -d domain.db.zst
```
