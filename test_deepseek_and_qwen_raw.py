import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_deepseek():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("No DEEPSEEK_API_KEY found.")
        return
    print(f"DEEPSEEK_API_KEY: {api_key[:10]}...")
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Say 'DeepSeek Direct OK'"}]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"DeepSeek Status Code: {response.status_code}")
        print(f"DeepSeek Response: {response.text}")
    except Exception as e:
        print(f"DeepSeek Error: {e}")

def test_dashscope():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("No DASHSCOPE_API_KEY found.")
        return
    print(f"DASHSCOPE_API_KEY: {api_key[:10]}...")
    url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "Say 'Qwen Cloud Direct OK'"}]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"DashScope Status Code: {response.status_code}")
        print(f"DashScope Response: {response.text}")
    except Exception as e:
        print(f"DashScope Error: {e}")

if __name__ == "__main__":
    test_deepseek()
    test_dashscope()
