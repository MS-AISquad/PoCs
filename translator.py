import os
import google.generativeai as genai
from typing import List, Optional
import time


class GeminiTranslator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        prompt = f"""Translate the following text from {source_lang} to {target_lang}. 
Only provide the translation, no explanations or additional text.

Text: {text}"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Translation failed: {str(e)}")
    
    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        translations = []
        for i, text in enumerate(texts):
            try:
                translation = self.translate_text(text, source_lang, target_lang)
                translations.append(translation)
                if i < len(texts) - 1:
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error translating text {i+1}: {str(e)}")
                translations.append("")
        
        return translations