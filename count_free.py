import json
with open('models/registry.json', encoding='utf-8') as f:
    data = json.load(f)
free_models = [m for m in data['models'].values() if m.get('free')]
print(f'Free models: {len(free_models)}')
for m in free_models[:10]:
    print(f'  {m["id"]} - ctx: {m.get("context_window")}')