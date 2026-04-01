from google import genai
from google.genai import types
from ai_worker.factory import Factory


class Gemini(Factory):
    """Gemini provider implementation"""
    
    def __init__(self, model, api_key):
        super().__init__("gemini", model, api_key)
        self.client = genai.Client(api_key=api_key)
        self.model = model
    
    def _make_request(self, prompt, temperature=0.7):
        """Make API request to Gemini"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature
            )
        )
        return response.text
    
    def design_sanity_schema_model(self, prompt, schema=None):
        """Design sanity schema validation"""
        if schema:
            prompt = f"{prompt}\n\nPlease respond with valid JSON only."
        return self._make_request(prompt)
    
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        return self._make_request(prompt)
    
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        return self._make_request(prompt)
    
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        return self._make_request(prompt, temperature=temperature)