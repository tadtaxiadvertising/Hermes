import json
with open('models/registry.json', encoding='utf-8') as f:
    data = json.load(f)
free_models = [m for m in data['models'].values() if m.get('free')]
print('Free models:')
for m in free_models[:20]:
    print(f'  {m["id"]}')