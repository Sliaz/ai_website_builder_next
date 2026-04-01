from openai import OpenAI as OpenAIClient
from ai_worker.factory import Factory


class OpenAI(Factory):
    """OpenAI provider implementation"""
    
    def __init__(self, model, api_key):
        super().__init__("openai", model, api_key)
        self.client = OpenAIClient(api_key=api_key)
    
    def _make_request(self, messages, response_format=None, temperature=0.7):
        """Make API request to OpenAI"""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            params["response_format"] = response_format
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def design_sanity_schema_model(self, prompt, schema=None):
        """Design sanity schema validation"""
        messages = [{"role": "user", "content": prompt}]
        response_format = {"type": "json_object"} if schema else None
        return self._make_request(messages, response_format=response_format)
    
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._make_request(messages)
    
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages)
    
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._make_request(messages, temperature=temperature)