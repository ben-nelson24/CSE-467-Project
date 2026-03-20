# CSE-467-Project Website List and Categorization

In this section we will show how we get and filter the data set for use

We Use fetchList.py and save it to a SQLite known as (`domain.db`)

### Step 1
Use the link below and scroll to (`latest.csv.gz`)

https://androzoo.uni.lu/api_doc

Place the csv into a folder (Download may take a while)

### Step 2

Navigate to the same directory as the file then input this command:
```console
$ cd website-list/
$ zcat latest.csv.gz | awk -F, '$5 > 10000000 && $8 == 0 {print; if (++count == 20000) exit}' > filtered.csv
```

### Step 3

Copy the newly created (`filtered.csv`) to the same directory as fetchList.py

Run the Command:
```console
$ python fetchList.py domain.db
```

Remember the fetchList.py is located inside the websiteList folder.