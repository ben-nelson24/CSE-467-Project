# CSE-467-Project Website List and Categorization

In this section we will show how to gather and scrape the data from Android Apps

We Use run_pipeline.py

Be sure to also have an Androzoo API key readily available.

Also be sure to have a prefiltered csv (filtered.csv) available.

For the purposes of the submission, we should have all the required paths configured for testing

### Step 1
Get the latest version of Apktools

(can be downloaded from (https://apktool.org/docs/install/))

Make sure that the apktool.jar file is in the apk_tool folder in this directory (should already be taken care of in zip file)

### Step 2

Ensure the csv file (filtered.csv) is in the the form_finder folder. 

### Step 3

Ensure you have a valid Androzoo API key (should be provided for zip demo)


### Step 4

Change APKTOOL_JAR's directory in run_pipeline.py is set correctly

### Step 5

Change MAX_APPS to the desired amount of apps you want to test.

For the project we used 750, but for demo we have it currently set to 10

### Step 6

Run the program with:
```console
python run_pipeline.py
```

### What to do next

The scraper will continously run. (THIS WILL TAKE A VERY LONG TIME ESPECIALLY IF MAX_APPS IS SET TO A HIGH NUMBER)

Once all the data has been scraped and converted into JSON files, we need to convert them into a [singular database to use](/dbConverter/README.md).

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
