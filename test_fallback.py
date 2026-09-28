from hermes_fallback import HermesFallback
fb = HermesFallback()

# Test fallback chain resolution
chain = fb._resolve_fallback_chain(['best_available_coder', 'fast_coder', 'reasoning_model'], free_mode=True)
print('Fallback chain resolved:')
for c in chain:
    print(f'  {c["role"]}: {c["model_id"]} ({c["provider"]})')