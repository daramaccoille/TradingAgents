import urllib.request
import json
import time

url = "http://localhost:11434/v1/chat/completions"
headers = {"Content-Type": "application/json"}
data = {
    "model": "qwen2.5:0.5b",
    "messages": [{"role": "user", "content": "Say 'Ollama OK' in one word."}],
    "temperature": 0.0
}

print("Sending direct HTTP POST request to Ollama with 0.5b model...")
start = time.time()
try:
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        res_body = response.read().decode("utf-8")
        res_json = json.loads(res_body)
        content = res_json["choices"][0]["message"]["content"]
        print(f"Success in {time.time() - start:.2f}s: {content.strip()}")
except Exception as e:
    print(f"Failed in {time.time() - start:.2f}s: {e}")
