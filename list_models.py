import urllib.request
import json

API_KEY = "AIzaSyAYS6xenjAaupprcROGr9DO1alxuhWcQ3c"
URL = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    with urllib.request.urlopen(URL) as response:
        data = json.loads(response.read().decode('utf-8'))
        print("Available Models:")
        for model in data.get('models', []):
            if 'generateContent' in model.get('supportedGenerationMethods', []):
                print(f"- {model['name']}")
except Exception as e:
    print(f"Error: {e}")
