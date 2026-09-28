#!/usr/bin/env python3
"""
Hermes Benchmark Harness - Internal benchmarks for model evaluation.
"""
import json
import os
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class BenchmarkResult:
    model_id: str
    provider: str
    task_type: str
    timestamp: str
    latency_ms: float
    ttft_ms: float
    tokens_per_second: float
    quality_score: float
    success: bool
    failure_reason: Optional[str]
    input_tokens: int
    output_tokens: int
    context_length: int


@dataclass
class AggregatedBenchmark:
    model_id: str
    task_type: str
    runs: List[BenchmarkResult] = field(default_factory=list)
    avg_latency_ms: float = 0.0
    avg_ttft_ms: float = 0.0
    avg_tps: float = 0.0
    avg_quality: float = 0.0
    success_rate: float = 0.0
    run_count: int = 0
    last_run: Optional[str] = None


class BenchmarkHarness:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(os.environ.get("HERMES_BASE", "C:/Users/Arismendy/AppData/Local/hermes"))
        self.performance_file = self.base_path / "models" / "performance.json"
        self.registry_file = self.base_path / "models" / "registry.json"
        self.benchmarks_dir = self.base_path / "routing" / "benchmarks"
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, AggregatedBenchmark] = {}
        self._load_performance()

    def _load_performance(self):
        if self.performance_file.exists():
            data = json.loads(self.performance_file.read_text(encoding="utf-8"))
            for model_id, mdata in data.get("models", {}).items():
                for bench in mdata.get("benchmarks", []):
                    key = f"{model_id}:{bench['task_type']}"
                    agg = AggregatedBenchmark(
                        model_id=model_id,
                        task_type=bench["task_type"],
                        runs=[BenchmarkResult(**r) for r in bench.get("runs", [])],
                        avg_latency_ms=bench.get("aggregated", {}).get("avg_latency_ms", 0),
                        avg_ttft_ms=bench.get("aggregated", {}).get("avg_ttft_ms", 0),
                        avg_tps=bench.get("aggregated", {}).get("avg_tps", 0),
                        avg_quality=bench.get("aggregated", {}).get("avg_quality", 0),
                        success_rate=bench.get("aggregated", {}).get("success_rate", 0),
                        run_count=bench.get("aggregated", {}).get("run_count", 0),
                        last_run=bench.get("aggregated", {}).get("last_run")
                    )
                    self.results[key] = agg

    def _save_performance(self):
        models_data = {}
        for key, agg in self.results.items():
            model_id = agg.model_id
            if model_id not in models_data:
                models_data[model_id] = {"benchmarks": []}
            
            models_data[model_id]["benchmarks"].append({
                "task_type": agg.task_type,
                "runs": [asdict(r) for r in agg.runs],
                "aggregated": {
                    "avg_latency_ms": agg.avg_latency_ms,
                    "avg_ttft_ms": agg.avg_ttft_ms,
                    "avg_tps": agg.avg_tps,
                    "avg_quality": agg.avg_quality,
                    "success_rate": agg.success_rate,
                    "run_count": agg.run_count,
                    "last_run": agg.last_run
                }
            })
        
        data = {
            "models": models_data,
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
        self.performance_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _call_model(self, model_id: str, prompt: str, max_tokens: int = 500) -> Dict:
        provider, model_name = model_id.split("/", 1)
        
        if provider == "openrouter":
            return self._call_openrouter(model_name, prompt, max_tokens)
        elif provider == "nvidia":
            return self._call_nvidia(model_name, prompt, max_tokens)
        elif provider == "qwencloud":
            return self._call_qwencloud(model_name, prompt, max_tokens)
        else:
            return {"success": False, "error": f"Unknown provider: {provider}"}

    def _call_openrouter(self, model: str, prompt: str, max_tokens: int, retries: int = 3) -> Dict:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        for attempt in range(retries):
            start = time.time()
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, json=payload, timeout=60
                )
                
                if resp.status_code == 429:
                    wait = (attempt + 1) * 5
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
                
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                
                latency = (time.time() - start) * 1000
                
                return {
                    "success": True,
                    "response": content,
                    "latency_ms": latency,
                    "ttft_ms": latency,
                    "output_tokens": usage.get("completion_tokens", len(content.split()) * 1.3),
                    "input_tokens": usage.get("prompt_tokens", len(prompt.split()) * 1.3)
                }
            except Exception as e:
                if attempt == retries - 1:
                    return {"success": False, "error": str(e)}
                time.sleep(2)
        
        return {"success": False, "error": "Max retries exceeded"}

    def _call_nvidia(self, model: str, prompt: str, max_tokens: int) -> Dict:
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        start = time.time()
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers, json=payload, timeout=60
            )
            latency = (time.time() - start) * 1000
            
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            
            return {
                "success": True,
                "response": content,
                "latency_ms": latency,
                "ttft_ms": latency,
                "output_tokens": usage.get("completion_tokens", len(content.split()) * 1.3),
                "input_tokens": usage.get("prompt_tokens", len(prompt.split()) * 1.3)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _call_qwencloud(self, model: str, prompt: str, max_tokens: int) -> Dict:
        api_key = os.environ.get("QWENCLOUD_API_KEY")
        base_url = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        start = time.time()
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers, json=payload, timeout=60
            )
            latency = (time.time() - start) * 1000
            
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            
            return {
                "success": True,
                "response": content,
                "latency_ms": latency,
                "ttft_ms": latency,
                "output_tokens": usage.get("completion_tokens", len(content.split()) * 1.3),
                "input_tokens": usage.get("prompt_tokens", len(prompt.split()) * 1.3)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _evaluate_coding(self, response: str, expected: str) -> float:
        if not response:
            return 0.0
        response_lower = response.lower()
        expected_lower = expected.lower()
        
        score = 0.0
        if "def " in response_lower or "function " in response_lower:
            score += 0.3
        if "return" in response_lower:
            score += 0.2
        if any(kw in response_lower for kw in ["if", "for", "while", "try", "except"]):
            score += 0.2
        if len(response) > 50:
            score += 0.1
        if expected_lower in response_lower:
            score += 0.2
        return min(score, 1.0)

    def _evaluate_reasoning(self, response: str, expected: str) -> float:
        if not response:
            return 0.0
        response_lower = response.lower()
        expected_lower = expected.lower()
        
        score = 0.0
        if any(kw in response_lower for kw in ["because", "therefore", "thus", "since", "given that"]):
            score += 0.3
        if any(kw in response_lower for kw in ["step", "first", "second", "then", "finally"]):
            score += 0.2
        if len(response) > 100:
            score += 0.2
        if expected_lower in response_lower:
            score += 0.3
        return min(score, 1.0)

    def _evaluate_generic(self, response: str, expected: str) -> float:
        if not response:
            return 0.0
        if expected and expected.lower() in response.lower():
            return 1.0
        return 0.5 if len(response) > 20 else 0.2

    def run_benchmark(self, model_id: str, task_type: str, runs: int = 3) -> List[BenchmarkResult]:
        prompts = self._get_prompts(task_type)
        results = []
        
        for i, (prompt, expected) in enumerate(prompts[:runs]):
            print(f"  Run {i+1}/{runs} for {model_id} [{task_type}]...")
            
            result = self._call_model(model_id, prompt, max_tokens=500)
            
            if result["success"]:
                response = result.get("response", "")
                latency = result.get("latency_ms", 0)
                ttft = result.get("ttft_ms", 0)
                output_tokens = result.get("output_tokens", 0)
                input_tokens = result.get("input_tokens", len(prompt.split()) * 1.3)
                
                if task_type == "CODING":
                    quality = self._evaluate_coding(response, expected)
                elif task_type == "REASONING":
                    quality = self._evaluate_reasoning(response, expected)
                else:
                    quality = self._evaluate_generic(response, expected)
                
                tps = (output_tokens / (latency / 1000)) if latency > 0 else 0
                
                bench_result = BenchmarkResult(
                    model_id=model_id,
                    provider=model_id.split("/")[0],
                    task_type=task_type,
                    timestamp=datetime.now().isoformat(),
                    latency_ms=latency,
                    ttft_ms=ttft,
                    tokens_per_second=tps,
                    quality_score=quality,
                    success=True,
                    failure_reason=None,
                    input_tokens=int(input_tokens),
                    output_tokens=int(output_tokens),
                    context_length=len(prompt) + len(response)
                )
            else:
                # Retry once on failure
                print(f"    Failed: {result.get('error')}, retrying...")
                time.sleep(3)
                result = self._call_model(model_id, prompt, max_tokens=500)
                
                if result["success"]:
                    response = result.get("response", "")
                    latency = result.get("latency_ms", 0)
                    ttft = result.get("ttft_ms", 0)
                    output_tokens = result.get("output_tokens", 0)
                    input_tokens = result.get("input_tokens", len(prompt.split()) * 1.3)
                    
                    if task_type == "CODING":
                        quality = self._evaluate_coding(response, expected)
                    elif task_type == "REASONING":
                        quality = self._evaluate_reasoning(response, expected)
                    else:
                        quality = self._evaluate_generic(response, expected)
                    
                    tps = (output_tokens / (latency / 1000)) if latency > 0 else 0
                    
                    bench_result = BenchmarkResult(
                        model_id=model_id,
                        provider=model_id.split("/")[0],
                        task_type=task_type,
                        timestamp=datetime.now().isoformat(),
                        latency_ms=latency,
                        ttft_ms=ttft,
                        tokens_per_second=tps,
                        quality_score=quality,
                        success=True,
                        failure_reason=None,
                        input_tokens=int(input_tokens),
                        output_tokens=int(output_tokens),
                        context_length=len(prompt) + len(response)
                    )
                else:
                    bench_result = BenchmarkResult(
                        model_id=model_id,
                        provider=model_id.split("/")[0],
                        task_type=task_type,
                        timestamp=datetime.now().isoformat(),
                        latency_ms=0,
                        ttft_ms=0,
                        tokens_per_second=0,
                        quality_score=0,
                        success=False,
                        failure_reason=result.get("error", "Unknown error"),
                        input_tokens=0,
                        output_tokens=0,
                        context_length=0
                    )
            
            results.append(bench_result)
            time.sleep(2)  # Rate limiting
        
        return results

    def _get_prompts(self, task_type: str) -> List[Tuple[str, str]]:
        prompts = {
            "CODING": [
                ("Write a Python function to calculate fibonacci numbers with memoization", "memoization"),
                ("Create a binary search implementation in Python", "binary search"),
                ("Write a decorator that measures function execution time", "decorator"),
            ],
            "REASONING": [
                ("If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly? Explain.", "no"),
                ("A train leaves at 60 mph. Another leaves 1 hour later at 80 mph. When does the second catch the first?", "3 hours"),
                ("Explain why the sky is blue using Rayleigh scattering", "Rayleigh"),
            ],
            "PLANNING": [
                ("Plan a 3-day trip to Tokyo with budget constraints", "Tokyo"),
                ("Create a project plan for building a REST API", "REST API"),
                ("Design a study schedule for learning Python in 30 days", "Python"),
            ],
            "TOOL_USE": [
                ("Describe how you would use a calculator tool to compute 15% of 247", "calculator"),
                ("Explain the steps to call a weather API for current temperature", "weather API"),
                ("How would you use a file search tool to find all .py files?", "file search"),
            ],
            "FAST_QA": [
                ("What is the capital of Australia?", "Canberra"),
                ("Who wrote '1984'?", "George Orwell"),
                ("What is 2^10?", "1024"),
            ],
            "ARCHITECTURE": [
                ("Design a microservices architecture for an e-commerce platform", "microservices"),
                ("Explain the tradeoffs between monolith and microservices", "tradeoffs"),
                ("Design a caching strategy for a high-traffic web app", "caching"),
            ],
            "SUMMARIZATION": [
                ("Summarize the key points of the Pareto principle in 3 sentences", "80/20"),
                ("Summarize how a hash table works", "hash table"),
                ("Summarize the CAP theorem", "CAP theorem"),
            ],
            "EXTRACTION": [
                ("Extract all dates from: 'Meeting on Jan 15, follow up Feb 20, deadline Mar 1'", "Jan 15, Feb 20, Mar 1"),
                ("Extract the error code from: 'Error 404: Not Found at /api/users'", "404"),
                ("Extract all email addresses from: 'Contact john@test.com or jane@test.com'", "john@test.com, jane@test.com"),
            ],
            "LONG_CONTEXT": [
                ("Analyze this long text... [placeholder for long context test]", "analysis"),
            ],
            "STRUCTURED_OUTPUT": [
                ("Return a JSON object with name, age, and city fields", "json"),
                ("Output a valid YAML with server config", "yaml"),
                ("Generate a CSV header for user data", "csv"),
            ],
        }
        return prompts.get(task_type, prompts["FAST_QA"])

    def run_model_benchmarks(self, model_id: str, task_types: List[str] = None, runs: int = 3):
        if task_types is None:
            task_types = ["CODING", "REASONING", "PLANNING", "TOOL_USE", "FAST_QA", "ARCHITECTURE", "SUMMARIZATION", "EXTRACTION"]
        
        print(f"\nBenchmarking {model_id}...")
        for task_type in task_types:
            results = self.run_benchmark(model_id, task_type, runs)
            self._aggregate_results(model_id, task_type, results)
            self._save_performance()
            
            success_count = sum(1 for r in results if r.success)
            avg_quality = sum(r.quality_score for r in results if r.success) / max(success_count, 1)
            avg_latency = sum(r.latency_ms for r in results if r.success) / max(success_count, 1)
            print(f"  {task_type}: {success_count}/{runs} success, avg_quality={avg_quality:.2f}, avg_latency={avg_latency:.0f}ms")

    def _aggregate_results(self, model_id: str, task_type: str, results: List[BenchmarkResult]):
        key = f"{model_id}:{task_type}"
        if key not in self.results:
            self.results[key] = AggregatedBenchmark(model_id=model_id, task_type=task_type)
        
        agg = self.results[key]
        agg.runs.extend(results)
        agg.run_count = len(agg.runs)
        agg.last_run = datetime.now().isoformat()
        
        successful = [r for r in agg.runs if r.success]
        if successful:
            agg.avg_latency_ms = sum(r.latency_ms for r in successful) / len(successful)
            agg.avg_ttft_ms = sum(r.ttft_ms for r in successful) / len(successful)
            agg.avg_tps = sum(r.tokens_per_second for r in successful) / len(successful)
            agg.avg_quality = sum(r.quality_score for r in successful) / len(successful)
            agg.success_rate = len(successful) / len(agg.runs)

    def run_all_free_models(self, task_types: List[str] = None, runs: int = 2):
        with open(self.registry_file, encoding="utf-8") as f:
            data = json.load(f)
        
        free_models = [m for m in data["models"].values() if m.get("free")]
        print(f"Found {len(free_models)} free models to benchmark")
        
        for model in free_models:
            try:
                self.run_model_benchmarks(model["id"], task_types, runs)
            except Exception as e:
                print(f"Error benchmarking {model['id']}: {e}")


def main():
    harness = BenchmarkHarness()
    
    print("Testing single model benchmark...")
    harness.run_model_benchmarks("openrouter/google/gemma-4-26b-a4b-it:free", ["CODING", "REASONING"], runs=1)
    
    print("\nDone!")


if __name__ == "__main__":
    main()