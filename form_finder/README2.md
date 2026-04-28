# CSE-467-Project Website List and Categorization

In this section we will show how to gather and scrape the data from Android Apps

We Use run_pipeline.py

Be sure to also have an Androzoo API key readily available.

Also be sure to have a prefiltered csv (filtered.csv) available.

### Step 1
Get the latest version of Apktools

(can be downloaded from (https://apktool.org/docs/install/))

Place the a copy of the jar both in the form_finder folder as well as the project folder (You need two copies)

### Step 2

Ensure the csv file (filtered.csv) is in the the form_finder folder. 

### Step 3

Change the code to fit your needs. 

First Change the API_KEY to your Androzoo Api Key

Remove the code snipped:
```console
os.environ.get("ANDROZOO API KEY HERE")
```

and replace it with:

```console
"ANDROZOO API KEY HERE"
```

### Step 4

Change APKTOOL_JAR's directory, to the same directory as your apktool.jar

Remember that the default download name for the latest version of apktool.jar, is not called apktool.jar. 

Ensure the names align

### Step 5

Change MAX_APPS to the desired amount of apps you want to test.

For the project we used 750.

### Step 6

Run the program with python run_pipeline.py

### Error debugging:

Certain potential errors may occur. 

If you run into issues such as androguard.misc import AnalyzeAPK, then ensure you install androguard with:

```console
pip install androguard
```

If you run into issues with requests package being missing, run:

```console
pip install requests
```
