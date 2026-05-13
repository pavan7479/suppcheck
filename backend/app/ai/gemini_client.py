import os
import google.generativeai as genai
from dotenv import load_dotenv
 

load_dotenv(override=True)

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-3.1-flash-lite')
        

        

        

    async def generate_content(self, prompt: str):
        print(f"\n[AI] Sending generation request (Length: {len(prompt)} characters)...")
        try:
            import time
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration = time.time() - start_time
            print(f"[AI] Received response in {duration:.2f}s")
            
            # Check if the response was blocked
            if response.candidates:
                return response.text
            else:
                print(f"[AI] Error: No candidates returned. Safety filters might have blocked it.")
                return "{}"
        except Exception as e:
            print(f"[AI] API Error: {str(e)}")
            raise e
        

gemini_client = GeminiClient()
