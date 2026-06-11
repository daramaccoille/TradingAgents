import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")
print(f"OPENAI_API_KEY: {api_key[:10]}...")

if not api_key:
    print("No API key found.")
    exit(1)

url = "https://api.openai.com/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}
data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say 'OpenAI Direct OK'"}]
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
