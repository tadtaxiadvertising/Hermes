import json

# Read from JSONL results
results = []
with open('evals/eval_results.jsonl', encoding='utf-8') as f:
    for line in f:
        results.append(json.loads(line))

total = len(results)
passed = sum(1 for r in results if r['passed'])

print(f'Total: {passed}/{total} passed')
print()

# Group by family
from collections import defaultdict
by_family = defaultdict(list)
for r in results:
    by_family[r['family']].append(r)

for family, tests in by_family.items():
    fam_passed = sum(1 for t in tests if t['passed'])
    fam_total = len(tests)
    print(f'{family}: {fam_passed}/{fam_total}')
    for t in tests:
        status = 'PASS' if t['passed'] else 'FAIL'
        print(f'  {status}: {t["test_name"]} ({t["duration_ms"]:.1f}ms)')