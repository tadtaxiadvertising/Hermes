import requests, os

headers = {'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}', 'Content-Type': 'application/json'}

models_to_test = [
    'nvidia/nemotron-3.5-lightning:free',
    'stealth/space-bunny-alpha',
    'qwen/qwen3.8-27b:free',
    'liquid/lfm-2.5-2.6b:free',
]

for model in models_to_test:
    payload = {'model': model, 'messages': [{'role': 'user', 'content': 'Say hello'}], 'max_tokens': 50}
    r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=30)
    print(f'{model}: Status {r.status_code}')
    if r.status_code != 200:
        print(f'  Error: {r.text[:200]}')
    else:
        data = r.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f'  Response: {content[:50]}')
    print()