import urllib.request
import urllib.error
import json

req = urllib.request.Request(
    "http://localhost:8201/gateway/chat/completions",
    data=json.dumps({"model": "ollama/qwen2.5-coder", "messages": [{"role": "user", "content": "hi"}]}).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer rl_test_0W1cpxMV2ce2NKzH7ZpPq4RfhwMBY4i-eDHaIzOpQqI"
    }
)

try:
    resp = urllib.request.urlopen(req)
    print("SUCCESS:", resp.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    print(f"HTTP ERROR {exc.code}:")
    print(exc.read().decode("utf-8"))
