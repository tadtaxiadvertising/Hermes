# MEMORY INDEX

## Structure
```
memory/
├── INDEX.md           (this file)
├── identity.md
├── mission.md
├── goals.md
├── principles.md
├── facts.md
├── preferences.md
├── decisions.md
├── lessons.md
├── failures.md
├── entities.md
├── projects/
├── sessions/
└── journal/
```

## Memory Classes
- FACT: Hechos confirmados
- DECISION: Decisiones arquitectónicas
- PREFERENCE: Preferencias estables del usuario
- GOAL: Objetivos declarados
- LESSON: Aprendizajes de ejecuciones
- FAILURE: Errores históricos
- TASK: Estado de tareas
- PROJECT: Metadatos de proyectos
- CONSTRAINT: Limitaciones técnicas/económicas
- ENTITY: Entidades relevantes (modelos, proveedores, herramientas)
- MODEL: Capacidades y métricas de modelos
- PROVIDER: Estado y configuración de proveedores
- STRATEGY: Estrategias aprendidas

## Entry Format
```yaml
id: unique-id
type: CLASS
created_at: ISO8601
updated_at: ISO8601
confidence: 0.0-1.0
source: origen (user, observation, benchmark, etc.)
status: active | superseded | archived
content: contenido principal
related: [ids relacionados]
supersedes: id previo si aplica
```

## Index Maintenance
- Actualizar al crear/modificar cualquier memoria
- Marcar superseded cuando una decisión cambia
- No borrar: archivar con status=archived