import json
import google.generativeai as genai
import os
from prompts import EXTRACTION_PROMPT

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_structured_data(raw_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            EXTRACTION_PROMPT + "\n\n" + raw_text
        )
        content = response.text
        print("--- RAW LLM RESPONSE ---")
        print(content)
        print("------------------------")

        # Clean up markdown if any
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            return json.loads(content)
        except Exception as e:
            print("JSON Parsing Error:", e)
            print("Extracted content to parse:", content)
            return None
    except Exception as e:
        print("LLM Extraction Error:", e)
        import traceback
        traceback.print_exc()
        return None
