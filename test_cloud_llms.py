import os
import time
from dotenv import load_dotenv
from tradingagents.llm_clients import create_llm_client

load_dotenv()

def test_google():
    print("\n--- Testing Google (Gemini) ---")
    api_key = os.environ.get("GOOGLE_API_KEY")
    print(f"GOOGLE_API_KEY present: {bool(api_key)}")
    if not api_key:
        return False
    try:
        # Try gemini-2.5-flash
        client = create_llm_client(provider="google", model="gemini-2.5-flash")
        llm = client.get_llm()
        start = time.time()
        res = llm.invoke("Say 'Google Gemini OK'")
        print(f"Success in {time.time() - start:.2f}s: {res.content.strip()}")
        return True
    except Exception as e:
        print(f"Google Gemini Failed: {e}")
        return False

def test_openai():
    print("\n--- Testing OpenAI ---")
    api_key = os.environ.get("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY present: {bool(api_key)}")
    if not api_key:
        return False
    try:
        client = create_llm_client(provider="openai", model="gpt-4o-mini")
        llm = client.get_llm()
        start = time.time()
        res = llm.invoke("Say 'OpenAI OK'")
        print(f"Success in {time.time() - start:.2f}s: {res.content.strip()}")
        return True
    except Exception as e:
        print(f"OpenAI Failed: {e}")
        return False

def test_dashscope():
    print("\n--- Testing Qwen Cloud (DashScope) ---")
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    print(f"DASHSCOPE_API_KEY present: {bool(api_key)}")
    if not api_key:
        return False
    try:
        client = create_llm_client(provider="qwen", model="qwen-plus")
        llm = client.get_llm()
        start = time.time()
        res = llm.invoke("Say 'Qwen Cloud OK'")
        print(f"Success in {time.time() - start:.2f}s: {res.content.strip()}")
        return True
    except Exception as e:
        print(f"Qwen Cloud Failed: {e}")
        return False

if __name__ == "__main__":
    test_google()
    test_openai()
    test_dashscope()
