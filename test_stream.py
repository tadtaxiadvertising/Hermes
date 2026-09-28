import requests, os, json, time

headers = {'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}', 'Content-Type': 'application/json'}
payload = {'model': 'nvidia/nemotron-3.5-lightning:free', 'messages': [{'role': 'user', 'content': 'Write a Python fibonacci function'}], 'max_tokens': 200}

start = time.time()
with requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=60, stream=True) as resp:
    print('Status:', resp.status_code)
    full = ""
    for line in resp.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            full += delta["content"]
                except:
                    pass

print('Full response:', full[:300])
print('Latency:', (time.time() - start) * 1000)