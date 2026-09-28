from hermes_benchmark import BenchmarkHarness

harness = BenchmarkHarness()

# Test multiple working free models
models = [
    "openrouter/nvidia/nemotron-3.5-lightning:free",
    "openrouter/stealth/space-bunny-alpha",
    "openrouter/liquid/lfm-2.5-2.6b:free",
    "openrouter/nvidia/nemotron-3.5-content-safety:free",
]

for model in models:
    try:
        harness.run_model_benchmarks(model, ["CODING", "REASONING", "FAST_QA"], runs=1)
    except Exception as e:
        print(f"Error with {model}: {e}")

print("\nAll benchmarks complete!")