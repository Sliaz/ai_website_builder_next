import anthropic
from ai_worker.factory import Factory


class Claude(Factory):
    """Claude provider implementation"""
    
    def __init__(self, model, api_key):
        super().__init__("claude", model, api_key)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def _make_request(self, messages, system_prompt=None, temperature=0.7, max_tokens=4096):
        """Make API request to Claude"""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if system_prompt:
            params["system"] = system_prompt
        
        response = self.client.messages.create(**params)
        return response.content[0].text
    
    def design_sanity_schema_model(self, prompt, schema=None):
        """Design sanity schema validation"""
        messages = [{"role": "user", "content": prompt}]
        system_prompt = None
        if schema:
            system_prompt = "You must respond with valid JSON matching the provided schema."
        return self._make_request(messages, system_prompt=system_prompt)
    
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages, system_prompt=system_prompt)
    
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages)
    
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages, system_prompt=system_prompt, temperature=temperature)