# ASI-Build API Documentation

> ⚠️ **Partially v1 artifact**: The detailed API reference and subsystem API docs in this directory were written for a v1 codebase. The current codebase has **28 modules** in `src/asi_build/`. Cross-reference against actual source code.

## Documentation Files

| File | Description | Status |
|------|-------------|--------|
| [API_REFERENCE.md](API_REFERENCE.md) | Endpoint documentation | v1 artifact — verify against code |
| [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) | Integration tutorials | v1 artifact — verify against code |
| [SUBSYSTEM_APIS.md](SUBSYSTEM_APIS.md) | Subsystem-specific API details | v1 artifact — historical reference |
| [openapi.yaml](openapi.yaml) | OpenAPI specification | v1 artifact — verify against code |

## Current Architecture

The ASI-Build codebase has **28 modules** in `src/asi_build/`. The primary integration mechanism is the **Cognitive Blackboard** + **EventBus** in `src/asi_build/integration/`.

For the actual module list, see [`../modules/README.md`](../modules/README.md).

## Running Locally

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# The project does not currently expose a unified REST API server.
# Individual modules provide their own interfaces — see each module's __init__.py.
```

## License

MIT — see [LICENSE](/LICENSE).
