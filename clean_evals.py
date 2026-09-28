import json
results = []
with open('evals/eval_results.jsonl', encoding='utf-8') as f:
    for line in f:
        results.append(json.loads(line))

# Keep only last occurrence of each test_name per family
seen = {}
for r in reversed(results):
    key = (r['family'], r['test_name'])
    if key not in seen:
        seen[key] = r

# Write back in original order
clean = list(reversed(list(seen.values())))
with open('evals/eval_results.jsonl', 'w', encoding='utf-8') as f:
    for r in clean:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print('Cleaned: {} -> {} entries'.format(len(results), len(clean)))
for r in clean:
    status = 'PASS' if r['passed'] else 'FAIL'
    print('  {}: {} - {}'.format(status, r['family'], r['test_name']))

passed = sum(1 for r in clean if r['passed'])
print('\nTotal: {}/{} passed'.format(passed, len(clean)))