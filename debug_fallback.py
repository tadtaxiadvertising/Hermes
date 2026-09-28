from hermes_router import HermesRouter
from hermes_fallback import HermesFallback

router = HermesRouter()
fb = HermesFallback()

# Test router.get_models directly
models = router.get_models(free_only=True, capability_min={"coding": 0.8, "tool_use": 0.8})
print(f"Models with coding>=0.8, tool_use>=0.8: {len(models)}")
for m in models[:5]:
    print(f'  {m["id"]} - coding={m["capabilities"]["coding"]}, tool_use={m["capabilities"]["tool_use"]}')

models = router.get_models(free_only=True, capability_min={"coding": 0.6, "speed": 0.7})
print(f"\nModels with coding>=0.6, speed>=0.7: {len(models)}")
for m in models[:5]:
    print(f'  {m["id"]} - coding={m["capabilities"]["coding"]}, speed={m["capabilities"]["speed"]}')

models = router.get_models(free_only=True, capability_min={"reasoning": 0.85})
print(f"\nModels with reasoning>=0.85: {len(models)}")
for m in models[:5]:
    print(f'  {m["id"]} - reasoning={m["capabilities"]["reasoning"]}')