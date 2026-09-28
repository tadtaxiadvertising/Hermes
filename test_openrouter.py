import requests, os

headers = {'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}', 'Content-Type': 'application/json'}
payload = {'model': 'google/gemma-4-26b-a4b-it:free', 'messages': [{'role': 'user', 'content': 'test'}], 'max_tokens': 100}
r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=30)
print('Status:', r.status_code)
print('Response:', r.text[:500])