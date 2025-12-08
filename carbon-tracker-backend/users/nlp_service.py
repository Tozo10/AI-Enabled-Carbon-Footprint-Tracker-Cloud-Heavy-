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
From the user's sentence, extract the 'activity_type', 'quantity', 'unit', and a specific 'key'.
- 'activity_type': 'TRANSPORT', 'FOOD', or 'ENERGY'.
- 'key': specific item (e.g., 'car', 'bus', 'steak', 'burger', 'electricity').
- 'quantity': the numeric amount (e.g., 10, 2, 0.5).
- 'unit': the unit of measure (e.g., 'km', 'mile', 'serving', 'kg', 'kWh'). 
If no unit is mentioned for food, assume 'serving'.
If no vehicle is mentioned for transport, assume 'car'.

Respond with ONLY a single, valid JSON object.

Sentence: "I took a 25 mile cab ride yesterday."
[/INST]
{{ "activity_type": "TRANSPORT", "key": "cab", "quantity": 25, "unit": "mile" }}

[INST]
Sentence: "I ate 2 steaks for dinner."
[/INST]
{{ "activity_type": "FOOD", "key": "steak", "quantity": 2, "unit": "serving" }}

[INST]
Sentence: "I used 50 kWh of electricity."
[/INST]
{{ "activity_type": "ENERGY", "key": "electricity", "quantity": 50, "unit": "kWh" }}

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