import requests, os

headers = {'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}', 'Content-Type': 'application/json'}

model = 'nvidia/nemotron-3.5-lightning:free'
payload = {'model': model, 'messages': [{'role': 'user', 'content': 'Write a Python fibonacci function'}], 'max_tokens': 200}
r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=30)
print(f'{model}: Status {r.status_code}')
if r.status_code == 200:
    data = r.json()
    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    print(f'Response: {content[:200]}')
else:
    print(f'Error: {r.text[:200]}')