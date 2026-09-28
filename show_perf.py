import json
with open('models/performance.json', encoding='utf-8') as f:
    data = json.load(f)
for model_id, mdata in data['models'].items():
    print(f'{model_id}:')
    for bench in mdata['benchmarks']:
        agg = bench['aggregated']
        print(f'  {bench["task_type"]}: success_rate={agg["success_rate"]:.2f}, avg_quality={agg["avg_quality"]:.2f}, avg_latency={agg["avg_latency_ms"]:.0f}ms, runs={agg["run_count"]}')