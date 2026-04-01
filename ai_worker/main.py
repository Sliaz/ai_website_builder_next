import os
from ai_worker.factory import Factory


def get_ai_client():
    """
    Prompts the user to select an AI provider and returns a ready-to-use AI client.
    
    Returns:
        Factory: An initialized AI client instance (OpenAI, Claude, or Gemini)
    """
    print("\n=== AI Provider Selection ===")
    print("Available providers:")
    print("1. OpenAI (GPT-4, GPT-3.5, etc.)")
    print("2. Claude (Claude 3 Opus, Sonnet, Haiku)")
    print("3. Gemini (Gemini Pro, etc.)")
    
    # Get provider choice
    while True:
        choice = input("\nSelect provider (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    provider_map = {
        '1': ('openai', 'gpt-4', 'OPENAI_API_KEY'),
        '2': ('claude', 'claude-3-5-sonnet-20241022', 'ANTHROPIC_API_KEY'),
        '3': ('gemini', 'gemini-pro', 'GOOGLE_API_KEY')
    }
    
    provider_name, default_model, env_key = provider_map[choice]
    
    # Get model name
    model = input(f"Enter model name (default: {default_model}): ").strip()
    if not model:
        model = default_model
    
    # Get API key
    api_key = os.getenv(env_key)
    if not api_key:
        api_key = input(f"Enter your {provider_name.upper()} API key: ").strip()
        if not api_key:
            raise ValueError("API key is required")
    else:
        print(f"Using API key from environment variable: {env_key}")
    
    # Create and return AI client
    print(f"\nInitializing {provider_name.upper()} with model: {model}")
    ai_client = Factory.create(provider_name, model, api_key)
    print("✓ AI client ready!\n")
    
    return ai_client


def main():
    """Main entry point for the AI website builder"""
    try:
        # Get AI client from user
        ai_client = get_ai_client()
        
        # Now you can use ai_client with component_worker
        # Example usage:
        # from component_worker import app, ComponentState
        # 
        # initial_state = ComponentState(
        #     component_name="Button",
        #     figma_screenshot="",
        #     component_code="",
        #     query_code="",
        #     typescript_type_code="",
        #     sanity_schema_code="",
        #     done=False
        # )
        # 
        # You can pass ai_client methods to the worker functions:
        # ai_client.design_component_model(prompt, system_prompt)
        # ai_client.design_query_model(prompt, system_prompt)
        # ai_client.design_typescript_type(prompt, context)
        # ai_client.design_sanity_schema_model(prompt, schema)
        
        print("AI client is ready for use!")
        print(f"Provider: {ai_client.provider}")
        print(f"Model: {ai_client.model}")
        
        # TODO: step 1: open the website with playwright and try getting a screenshot of a single component
        # TODO: step 2: integrate with component_worker
        
        return ai_client
        
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    main()