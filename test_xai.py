import os
import time
from dotenv import load_dotenv

load_dotenv()

print("Testing xAI with model 'grok-2'...")
try:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model="grok-2",
        openai_api_key=os.environ.get("XAI_API_KEY"),
        openai_api_base="https://api.x.ai/v1",
        timeout=15
    )
    start = time.time()
    res = llm.invoke("Say 'Grok OK'")
    print(f"Success in {time.time() - start:.2f}s: {res.content.strip()}")
except Exception as e:
    print(f"Failed: {e}")
