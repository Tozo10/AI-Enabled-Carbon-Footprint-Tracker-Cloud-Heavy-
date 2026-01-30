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

        print(f"--- DEBUG: NLP Service connecting... ---")

        credentials = {
            "apikey": api_key,
            "url": watsonx_url
        }

        # Using the model that worked for you previously
        model_id = "ibm/granite-3-3-8b-instruct"

        parameters = {
            GenParams.MAX_NEW_TOKENS: 100,
            GenParams.TEMPERATURE: 0.1, 
            GenParams.REPETITION_PENALTY: 1.0
        }
        
        # --- PROMPT: USING THE [INST] FORMAT THAT WORKED ---
        # We give it clear examples for Transport, Food, and Energy
        prompt_template = """[INST]
You are a Carbon Footprint Extractor. extract 'activity_type', 'key', 'quantity', and 'unit'.
- activity_type: "TRANSPORT", "FOOD", or "ENERGY".
- key: "car", "beef", "burger", "electricity", etc.
- quantity: number.
- unit: "km", "serving", "kWh".

Input: "I took a 25 mile cab ride"
Output: {{ "activity_type": "TRANSPORT", "key": "car", "quantity": 25, "unit": "miles" }}

Input: "I ate 2 burgers"
Output: {{ "activity_type": "FOOD", "key": "beef", "quantity": 2, "unit": "serving" }}

Input: "I used 50 kWh of electricity"
Output: {{ "activity_type": "ENERGY", "key": "electricity", "quantity": 50, "unit": "kWh" }}

Input: "{}"
Output:
[/INST]"""

        model = Model(
            model_id=model_id,
            params=parameters,
            credentials=credentials,
            project_id=project_id
        )

        prompt = prompt_template.format(text_to_analyze)
        
        # Generate
        raw_response_text = model.generate_text(prompt=prompt)
        print(f"DEBUG: NLP Raw Response: {raw_response_text}")

        # --- CLEANUP & PARSE (The Robust Part) ---
        # 1. Remove Markdown code blocks if present
        clean_text = raw_response_text.replace("```json", "").replace("```", "").strip()
        
        # 2. Extract JSON using Regex (Finds { ... })
        json_match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        
        if json_match:
            json_string = json_match.group(0)
            return json.loads(json_string)
        else:
            print("DEBUG: Could not find JSON in response.")
            return None

    except Exception as e:
        print(f"NLP Service Error: {e}")
        return None