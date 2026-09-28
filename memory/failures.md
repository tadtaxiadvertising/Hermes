# FAILURES

## Historical Failures (None yet - Initialization)

### Template for Future Failures
```
### F1: [Description]
- **id**: fail-XXX
- **type**: FAILURE
- **created_at**: ISO8601
- **confidence**: 1.0
- **source**: execution
- **status**: active | resolved
- **task**: tarea donde ocurrió
- **model**: modelo usado
- **provider**: proveedor usado
- **error**: descripción del error
- **root_cause**: causa raíz
- **impact**: qué se perdió/afectó
- **recovery**: cómo se recuperó (o no)
- **lesson_id**: referencia a lesson aprendida
- **fix_applied**: corrección implementada
- **verification**: cómo se verificó la corrección
```

## Known Failure Patterns to Watch
- Context loss during model switch
- Quota exhaustion without detection
- Silent paid fallback
- Credential exposure in logs/memory
- Checkpoint corruption/loss
- Recovery failure (hallucinated state)
- Routing to unsupported capability
- Provider degradation without failover