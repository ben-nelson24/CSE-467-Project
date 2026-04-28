# CSE-467-Project PI Classification and Form Categoriaztion

We make use of the classifier.py script to run analysis on the aggregated .db file as the output from the dbConverter in the previous step.

## Running Classification and Categorization

To keep running streamlined, we created one script that both analyzes and PI data types and classifies the forms in a single run

### Step 1
To get started, make sure that you have a forms.db file in this directory to run analysis on
 - For the zip demo, we the current forms.db is the database we used for our entire analysis
 - If you want to use a smaller db you made from the previous steps, just replace it in this directory and make sure it is named "forms.db"

 ### Step 2
 - Make sure the openAI dependency is installed
 ```
 pip install openai
 ```

 ### Step 3
 Ensure you have a valid open AI API key
 - For the zip demo, that should be covered and you should be set to run

 ### Step 4
 You are now good to run the analysis scripts!
 ```
 python classifier.py
 ```

 ## (Optional) Data visualizer scripts
 plotData.py and topPIperForm.py are two helper scripts to help display some data outputs, feel free to run them to take a look at their outputs!

 ```
python plotData.py
python topPIperForm.py
 ```

