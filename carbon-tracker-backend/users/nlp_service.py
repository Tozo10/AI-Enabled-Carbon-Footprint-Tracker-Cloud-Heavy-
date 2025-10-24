# users/nlp_service.py
import re
import json
from decouple import config
from ibm_watson_machine_learning.foundation_models import Model
from ibm_watson_machine_learning.metanames import GenTextParamsMetaNames as GenParams

def analyze_activity_text(text_to_analyze):
    try:
        watsonx_url = config("WATSONX_URL")
        api_key = config("NLP_API_KEY")
        project_id = config("WATSONX_PROJECT_ID")

        print(f"--- DEBUG: Connecting to URL -> {watsonx_url} ---")

        credentials = {
            "apikey": api_key,
            "url": watsonx_url
        }

        # We use a model ID string directly.
        # ibm/granite-13b-instruct-v2 is deprecated, let's use the new one.
        model_id = "ibm/granite-3-3-8b-instruct"

        parameters = {
            GenParams.MAX_NEW_TOKENS: 50,
            GenParams.TEMPERATURE: 0
        }
        
        # This prompt asks for a SINGLE JSON OBJECT
        prompt_template = """
        [INST]
From the user's sentence, extract the activity type, distance, unit, and a specific "key" for the *first* activity found.
The 'activity_type' must be one of: 'TRANSPORT', 'FOOD', or 'ENERGY'.
The 'key' must be a specific item like 'cab', 'car', 'steak', 'chicken', 'salad'.
Respond with ONLY a single, valid JSON object.
If no activity is found, return a JSON object with null values.

Sentence: "I took a 25 mile cab ride yesterday."
[/INST]
{{ "activity_type": "TRANSPORT", "key": "cab", "distance": 25, "unit": "mile" }}

[INST]
Sentence: "I ate a steak for dinner."
[/INST]
{{ "activity_type": "FOOD", "key": "steak", "distance": null, "unit": "serving" }}

[INST]
Sentence: "I drove my car 100km."
[/INST]
{{ "activity_type": "TRANSPORT", "key": "car", "distance": 100, "unit": "km" }}

[INST]
Sentence: "That was a good movie."
[/INST]
{{ "activity_type": null, "key": null, "distance": null, "unit": null }}

[INST]
Sentence: "{}"
[/INST]
        """

        model = Model(
            model_id=model_id,
            params=parameters,
            credentials=credentials,
            project_id=project_id
        )

        prompt = prompt_template.format(text_to_analyze)
        raw_response_text = model.generate_text(prompt=prompt)
        print("Raw Model Response:", raw_response_text)

        # --- Parse a SINGLE JSON OBJECT ---
        json_match = re.search(r"\{.*\}", raw_response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            return json.loads(json_string)
        else:
            return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None