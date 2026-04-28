# Understanding Privacy Norms through Web Forms

> Mobile applications are one of the main ways people interact with digital services today, and with that comes a lot of personal information being collected. Every time a user signs up for an app, makes a purchase, or fills out a form, they are handing over sensitive data. Despite how common this is, the privacy practices of Android apps around form-based data collection are not well studied.
This project extends the work of Cui et al. (2025), "Understanding Privacy Norms through Web Forms," which looked at PI collection across over 11,500 websites by crawling and classifying web forms. Our goal is to replicate and extend this for Android apps, swapping websites for apps and HTML forms for Android UI layouts written in XML.
This is worth studying because Android apps collect personal information in a fundamentally different way than websites, and there is very little research on it. Understanding what apps ask for and whether that aligns with what users would reasonably expect is a useful contribution to the privacy research space.
Our approach follows the same six step pipeline as the original paper: building an app dataset, collecting form data, preprocessing, PI type classification, form type classification, and privacy policy analysis.

More detailed instructions for how to run each module can be found in the README files within their corresponding folders. We have broken down the steps to mirror the data processing pipeline of the original project:

- [Step 1: App List and Categorization (websiteList)](./websiteList/)
- [Step 2: App Form data Extraction (form_finder)](./form_finder)
- [Step 3: Dataset Preporocessing (dbConverter)](./dbConverter)
- [Step 4: PI Type Classification(classifyData)](./classifyData)
- [Step 5: Form Type Classification(classifyData)](./classifyData)
- [Step 6: Privacy Policy Processing (privacyPolicyAnalysis)](./privacyPolicyAnalysis/)

