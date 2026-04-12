# Deployment

> **Maturity**: `experimental` · **Adapter**: None

CI/CD integration and deployment automation for ASI:BUILD components. Contains deployment scripts for CUDO compute platform and HuggingFace model hosting, container management utilities, and infrastructure-as-code templates. Currently a minimal module with no public API exports — primarily operational scripts.

## Key Classes

| Class | Description |
|-------|-------------|
| *(No public API classes — deployment scripts only)* | |

## Example Usage

```python
# deployment module contains operational scripts rather than a Python API
# Usage is primarily through CLI tools:
# python -m asi_build.deployment.deploy --target cudo --model reasoning_v2
# python -m asi_build.deployment.deploy --target huggingface --repo asi-build/model
```

## Blackboard Integration

No blackboard adapter. Deployment operations are triggered externally, not through the cognitive blackboard.
