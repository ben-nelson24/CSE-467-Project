# CSE-467-Project Website List and Categorization

In this section we will show how we get and filter the data set for use

We Use fetchList.py and save it to a SQLite known as (`domain.db`)

### Step 1
Get the latest list of apps from AndroZoo (`latest.csv.gz`) and place it into this moduals directory
```cd websiteList```

(can be downloaded from https://androzoo.uni.lu/api_doc)
or run:
```
Invoke-WebRequest -Uri "https://androzoo.uni.lu/static/lists/latest.csv.gz" -OutFile "latest.csv.gz"
```
for Windows or 
```
curl -L -O https://androzoo.uni.lu/static/lists/latest.csv.gz
```

Place the csv into a folder (Download may take a while)

### Step 2

Navigate to the same directory as the file then input this command:
```console
$ cd website-list/
zcat latest.csv.gz | awk -F, '$5 > 15000000 && $8 == 0 && $11 ~ /play\.google\.com/ {print; if (++count == 20000) exit}' > filtered.csv
```
What that command does is it filters out files that are larger than 15,000,000 bytes, doesn't have any antivirus flags, and filters to a max item count of 20,000

### Step 3

With the newly created (`filtered.csv`) in the same directory as fetchList.py

Run the Command:
```console
$ python fetchList.py domain.db
```

Remember the fetchList.py is located inside the websiteList folder.
