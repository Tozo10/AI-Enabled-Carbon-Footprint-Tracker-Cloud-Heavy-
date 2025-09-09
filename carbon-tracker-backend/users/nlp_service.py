# users/nlp_service.py
import re
import json
from decouple import config
from ibm_watson_machine_learning.foundation_models import Model
from ibm_watson_machine_learning.metanames import GenTextParamsMetaNames as GenParams
from ibm_watson_machine_learning.foundation_models.utils.enums import ModelTypes

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

        model_id = "ibm/granite-13b-instruct-v2"
    
        
        parameters = {
            GenParams.MAX_NEW_TOKENS: 50,
            GenParams.TEMPERATURE: 0
        }

        prompt_template = """
[INST]
From the user's sentence, extract the activity type, distance, and unit.
The activity type must be one of: 'TRANSPORT', 'FOOD', or 'ENERGY'.
Respond with ONLY a valid JSON object.

Sentence: "I took a 25 mile cab ride yesterday."
[/INST]
{{ "activity_type": "TRANSPORT", "distance": 25, "unit": "mile" }}

[INST]
Sentence: "{}"
[/INST]
"""
        # --- Instantiate the Model with explicit keyword arguments ---
        model = Model(
            model_id=model_id,
            params=parameters,
            credentials=credentials,
            project_id=project_id
        )

        prompt = prompt_template.format(text_to_analyze)
        raw_response_text = model.generate_text(prompt=prompt)
        print("Raw Model Response:", raw_response_text)

        # --- Parse the response ---
        json_match = re.search(r"\{.*\}", raw_response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            return json.loads(json_string)
        else:
            return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None