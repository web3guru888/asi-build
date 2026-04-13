# Deployment Module

The deployment module bridges ASI:BUILD's cognitive architecture with real-world ML infrastructure, enabling any trained model to be deployed to HuggingFace Spaces, HuggingFace Inference Endpoints, CUDO Compute GPU cloud, or local Gradio apps — all from a unified API.

**Location:** `src/asi_build/deployment/`  
**Files:** 9 Python files + 1 Jupyter notebook  
**Total LOC:** ~3,378  
**Tests:** `test_huggingface.py`, `test_huggingface_embedder.py`, `test_huggingface_embeddings.py`

---

## Architecture Overview

```
deployment/
├── universal_huggingface_deployer.py   # Main deployer (1,009 LOC)
├── huggingface.py                      # HF Hub wrapper + embedder
├── cudo_huggingface_integration.py     # CUDO GPU cloud backend
├── cudo_huggingface_live_working.py    # Live CUDO integration
├── deploy_huggingface_to_cudo_live.py  # CLI deploy script
└── tests/
    ├── test_huggingface.py
    ├── test_huggingface_embedder.py
    └── test_huggingface_embeddings.py
```

---

## `universal_huggingface_deployer.py`

The `UniversalHuggingFaceDeployer` class handles every HuggingFace resource type through a single deploy interface.

### Supported Deployment Targets

```python
class DeploymentTarget(Enum):
    HUGGINGFACE_SPACES = "hf_spaces"       # HF Spaces (Gradio/Streamlit)
    HUGGINGFACE_INFERENCE = "hf_inference" # HF Inference Endpoints
    CUDO_COMPUTE = "cudo"                   # CUDO GPU cloud
    LOCAL = "local"                         # Local inference
    GRADIO = "gradio"                       # Local Gradio app
```

### Supported Model Types

```python
class ModelType(Enum):
    CAUSAL_LM = "causal_lm"               # GPT-style autoregressive LM
    SEQ2SEQ = "seq2seq"                    # T5/BART style
    CLASSIFICATION = "classification"      # Text/image classification
    OBJECT_DETECTION = "object_detection"  # DETR, YOLO wrappers
    DIFFUSION = "diffusion"                # StableDiffusion, etc.
    AUDIO = "audio"                        # Whisper, wav2vec2
    EMBEDDING = "embedding"                # Sentence transformers
```

Model type is auto-detected from `AutoConfig` if not specified.

### Basic Usage

```python
from asi_build.deployment.universal_huggingface_deployer import (
    UniversalHuggingFaceDeployer,
    DeploymentTarget,
    DeploymentConfig
)

deployer = UniversalHuggingFaceDeployer(hf_token="hf_xxx")

config = DeploymentConfig(
    model_id="sentence-transformers/all-MiniLM-L6-v2",
    target=DeploymentTarget.HUGGINGFACE_INFERENCE,
    instance_type="cpu-basic",
    min_replicas=1,
    max_replicas=3
)

result = await deployer.deploy(config)
print(f"Endpoint: {result.endpoint_url}")
print(f"Status: {result.status}")
```

### HuggingFace Hub Operations

The deployer wraps the full `huggingface_hub` API surface:

| Operation | Method |
|-----------|--------|
| Get model metadata | `model_info(model_id)` |
| Get space info | `space_info(space_id)` |
| Create inference endpoint | `create_inference_endpoint(...)` |
| Upload files | `upload_file(path, repo_id)` |
| Create repo/space | `create_repo(repo_id, repo_type)` |
| Download snapshot | `snapshot_download(model_id, cache_dir)` |
| List models by task | `list_models(filter=PipelineTag.TEXT_GENERATION)` |

---

## `huggingface.py` — Embedder and API Wrapper

The `HuggingFaceEmbedder` provides a drop-in replacement for OpenAI's embedding API using locally-hosted sentence transformers:

```python
from asi_build.deployment.huggingface import HuggingFaceEmbedder

embedder = HuggingFaceEmbedder(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Single text
embedding = embedder.embed("What is consciousness?")  # shape: (384,)

# Batch
embeddings = embedder.embed_batch([
    "Global Workspace Theory",
    "Integrated Information Theory",
    "Higher Order Thought Theory"
])  # shape: (3, 384)
```

This is used by the VectorDB module as a backend embedding provider, enabling fully offline semantic search without external API calls.

### Supported Embedding Models

| Model | Dim | Use Case |
|-------|-----|---------|
| `all-MiniLM-L6-v2` | 384 | Fast general-purpose |
| `all-mpnet-base-v2` | 768 | Higher quality general |
| `multi-qa-mpnet-base-dot-v1` | 768 | Q&A retrieval |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Multilingual |

---

## CUDO Compute Integration

[CUDO Compute](https://www.cudocompute.com/) is a distributed GPU cloud marketplace offering lower cost per GPU-hour than AWS or GCP. The `CudoHuggingFaceIntegration` class handles the full deploy lifecycle:

```python
from asi_build.deployment.cudo_huggingface_integration import CudoHuggingFaceIntegration

cudo = CudoHuggingFaceIntegration(
    cudo_api_key="cudo_xxx",
    hf_token="hf_xxx"
)

# Deploy a model to CUDO GPU
result = await cudo.deploy_model(
    model_id="microsoft/phi-2",
    instance_type="gpu-v100-16gb",
    region="no-luster-1"  # Norway, low carbon
)

print(f"Inference URL: {result.endpoint_url}")
print(f"Cost estimate: ${result.hourly_cost:.3f}/hr")
```

### Deployment Lifecycle
1. Download model snapshot via `snapshot_download()`
2. Package as Docker container with runtime dependencies
3. Push to CUDO container registry
4. Launch GPU instance with auto-scaling config
5. Health-check endpoint until ready
6. Return `DeploymentResult` with endpoint URL

---

## Gradio App Scaffolding

The deployer auto-generates Gradio interfaces for any model type:

```python
app = deployer.scaffold_gradio_app(
    model_id="stabilityai/stable-diffusion-2",
    model_type=ModelType.DIFFUSION
)
app.launch(server_name="0.0.0.0", server_port=7860)
```

**Generated UI by model type:**

| Type | Input | Output |
|------|-------|--------|
| `causal_lm` | `gr.Textbox` (prompt) + temperature slider | `gr.Textbox` (generated text) |
| `classification` | `gr.Textbox` | `gr.Label` (top-k classes) |
| `object_detection` | `gr.Image` | `gr.Image` (annotated) + `gr.JSON` |
| `diffusion` | `gr.Textbox` + guidance slider | `gr.Image` |
| `audio` | `gr.Audio` | `gr.Textbox` (transcript) |
| `embedding` | `gr.Textbox` | `gr.Dataframe` (vector) |

---

## Integration Points

### With VectorDB Module
```python
from asi_build.vectordb.embedding_pipeline import EmbeddingPipeline
from asi_build.deployment.huggingface import HuggingFaceEmbedder

# Register HF embedder as VectorDB backend
pipeline = EmbeddingPipeline(
    backend="huggingface",
    embedder=HuggingFaceEmbedder("all-MiniLM-L6-v2")
)
```

### With Reproducibility Module
The `ExperimentTracker` (see [AGI-Reproducibility](AGI-Reproducibility)) can track model deployments:
```python
tracker.log_deployment(
    model_id="microsoft/phi-2",
    target=DeploymentTarget.CUDO_COMPUTE,
    endpoint_url=result.endpoint_url,
    git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
)
```

### Planned: Blackboard Integration
Issue [#84](https://github.com/web3guru888/asi-build/issues/84) tracks wiring deployment events to the Cognitive Blackboard — so the full module stack can react to new model deployments and the knowledge graph can record endpoint provenance bi-temporally.

---

## Running the Tests

```bash
cd /path/to/asi-build

# Unit tests (no HF token required — uses mocks)
python3 -m pytest src/asi_build/deployment/test_huggingface.py -v

# Embedding tests
python3 -m pytest src/asi_build/deployment/test_huggingface_embeddings.py -v

# Live tests (requires HF_TOKEN env var)
HF_TOKEN=hf_xxx python3 -m pytest src/asi_build/deployment/test_cudo_huggingface_live.py -v -m live
```

---

## Open Issues

- Issue [#84](https://github.com/web3guru888/asi-build/issues/84) — Wire deployment events to Cognitive Blackboard
- Future: CognitiveCycle `hot_swap(module_name, model_id)` API for dynamic module loading

---

*See also:* [VectorDB-Module](VectorDB-Module), [AGI-Reproducibility](AGI-Reproducibility), [Cognitive-Blackboard](Cognitive-Blackboard)
