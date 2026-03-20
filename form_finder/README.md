# Form Finder Script

This script decompiles an apk file to extract key XML elements related to forms

## Step 1: Install androguard

```
pip install androguard
```

## Step 2: Have an apk ready to analyze

- In the full final analysis, the apk results from each apk the websiteList step will be passed in as full parameters
- For demo purposes, we have a base.apk of duolingo ready for analysis

### How to get the Duolingo base.apk:

1. Go to https://www.apkmirror.com/apk/duolingo/duolingo-duolingo/duolingo-language-lessons-6-70-3-release/duolingo-language-lessons-6-70-3-android-apk-download/
2. Click DOWNLOAD APK BUNDLE
3. Rename .apkm to .zip and open
4. Extract base.apk to the form_finder folder

## Step 3: Run the script

```
python analyze_apk.py
```

The found XML form elements will be compile into a file called form_elements.csv in the same directory.
