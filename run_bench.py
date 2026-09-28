from hermes_benchmark import BenchmarkHarness

harness = BenchmarkHarness()
harness.run_model_benchmarks("openrouter/nvidia/nemotron-3.5-lightning:free", ["CODING", "REASONING"], runs=2)
print("Done!")