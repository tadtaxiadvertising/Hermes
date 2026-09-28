import json
with open('evals/eval_summary_20260928_164418.json', encoding='utf-8') as f:
    data = json.load(f)
print(f'Total passed: {data["total_passed"]}/{data["total_tests"]}')
for family, results in data['families'].items():
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    print(f'{family}: {passed}/{total}')
    for r in results:
        status = 'PASS' if r['passed'] else 'FAIL'
        print(f'  {status}: {r["test_name"]}')