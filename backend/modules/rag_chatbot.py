import google.generativeai as genai
import os
import json

def generate_chat_response(query, structured_data, diet, chat_history):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        context = ""
        if structured_data:
            context += "Patient Data: " + json.dumps(structured_data) + "\n"
        if diet:
            context += "Diet Plan: " + json.dumps(diet) + "\n"
            
        prompt = f"You are a helpful medical AI assistant. Using the following patient context, answer the user's query.\n\nContext:\n{context}\n\nQuery: {query}"
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "I am unable to answer right now due to an error: " + str(e)
