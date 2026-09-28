import requests, os, json, time

headers = {'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}', 'Content-Type': 'application/json'}
payload = {'model': 'nvidia/nemotron-3.5-lightning:free', 'messages': [{'role': 'user', 'content': 'Say hello'}], 'max_tokens': 50}

r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=30)
print('Status:', r.status_code)
print('Raw:', r.text[:500])
if r.status_code == 200:
    data = r.json()
    print('Parsed:', json.dumps(data, indent=2)[:500])