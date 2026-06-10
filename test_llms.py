import time
from langchain_openai import ChatOpenAI

print("Testing LangChain with Ollama qwen2.5:0.5b...")
try:
    llm = ChatOpenAI(
        model="qwen2.5:0.5b",
        openai_api_key="ollama",
        openai_api_base="http://localhost:11434/v1",
        timeout=15
    )
    start = time.time()
    res = llm.invoke("Say 'Ollama OK'")
    print(f"Success in {time.time() - start:.2f}s: {res.content.strip()}")
except Exception as e:
    print(f"Failed: {e}")
