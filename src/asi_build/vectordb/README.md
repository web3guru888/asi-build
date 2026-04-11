# Kenny Vector Database System

A comprehensive vector database system with multi-database support, advanced search capabilities, and intelligent document processing.

## 🌟 Features

### Multi-Database Support
- **Pinecone**: Cloud-native vector database with high performance
- **Weaviate**: Open-source vector database with GraphQL API
- **Qdrant**: Vector similarity search engine with advanced filtering

### Advanced Embedding Pipeline
- **Multiple Models**: Support for Sentence Transformers, OpenAI, Cohere, and HuggingFace models
- **Intelligent Caching**: Automatic embedding caching to improve performance
- **Batch Processing**: Efficient batch embedding generation
- **Text Preprocessing**: Automatic text cleaning and optimization

### Semantic Search Engine
- **Multi-Modal Search**: Semantic, keyword, and hybrid search modes
- **Query Expansion**: Automatic query enhancement for better results
- **Result Reranking**: Intelligent result ordering based on multiple factors
- **Faceted Search**: Advanced filtering and aggregation capabilities

### Unified API
- **Single Interface**: Work with multiple vector databases through one API
- **Automatic Failover**: Seamless switching between healthy databases
- **Load Balancing**: Intelligent routing and performance optimization
- **Health Monitoring**: Real-time database health checks

### Batch Processing
- **Large-Scale Indexing**: Efficient processing of thousands of documents
- **Progress Tracking**: Real-time job monitoring and progress updates
- **Error Recovery**: Robust error handling and retry mechanisms
- **File Processing**: Direct indexing from files and directories

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/kenny-agi/vectordb.git
cd vectordb

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Basic Usage

```python
from kenny_vectordb import VectorDBConfig, UnifiedVectorDB
from kenny_vectordb.api.indexing import IndexingAPI, Document

# Initialize configuration
config = VectorDBConfig()

# Create unified vector database
vector_db = UnifiedVectorDB(config)

# Initialize indexing API
indexing_api = IndexingAPI(vector_db)

# Create and index documents
documents = [
    Document(
        content="Artificial intelligence is transforming industries.",
        title="AI Revolution",
        category="technology",
        tags=["ai", "technology", "innovation"]
    ),
    Document(
        content="Climate change requires immediate action.",
        title="Climate Action",
        category="environment",
        tags=["climate", "environment", "sustainability"]
    )
]

# Index documents
for doc in documents:
    indexing_api.index_document(doc)

# Search for relevant documents
results = vector_db.search("artificial intelligence technology", top_k=5)

for result in results:
    print(f"Title: {result.metadata.get('title')}")
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.content[:100]}...")
    print()
```

## 📖 Documentation

### Configuration

The system uses YAML configuration files with environment variable overrides:

```yaml
# config.yaml
embedding:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  model_type: "sentence_transformers"
  batch_size: 32
  cache_embeddings: true

search:
  top_k: 10
  score_threshold: 0.7
  rerank: true

pinecone:
  api_key: null  # Set via PINECONE_API_KEY
  environment: "us-east1-aws"
  index_name: "kenny-vectors"
  dimension: 1536

weaviate:
  host: "localhost"
  port: 8080
  scheme: "http"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "kenny-collection"
  vector_size: 1536
```

Environment variables:
```bash
# Create .env file
cp .env.example .env

# Edit with your API keys
PINECONE_API_KEY=your_pinecone_key
OPENAI_API_KEY=your_openai_key
WEAVIATE_API_KEY=your_weaviate_key
QDRANT_API_KEY=your_qdrant_key
```

### Advanced Search

```python
from kenny_vectordb.api.retrieval import RetrievalAPI, RetrievalQuery

retrieval_api = RetrievalAPI(vector_db)

# Semantic search with query expansion
query = RetrievalQuery(
    query="machine learning algorithms",
    search_mode="semantic",
    top_k=10,
    expand_query=True,
    rerank=True
)

results = retrieval_api.search(query)

# Hybrid search (vector + keyword)
hybrid_results = vector_db.hybrid_search(
    query="deep learning neural networks",
    vector_weight=0.7,
    keyword_weight=0.3
)

# Faceted search
faceted_query = RetrievalQuery(
    query="artificial intelligence",
    facets=["category", "tags"],
    category_filter=["technology"]
)

faceted_results = retrieval_api.search(faceted_query)
```

### Batch Processing

```python
# Batch document indexing
documents = [Document(content=f"Document {i}") for i in range(100)]

job = indexing_api.index_documents_batch(
    documents=documents,
    batch_size=20,
    parallel=True
)

# Monitor progress
while job.status in ["pending", "processing"]:
    current_job = indexing_api.get_job_status(job.job_id)
    print(f"Progress: {current_job.progress:.1%}")
    time.sleep(1)

# Index entire directories
job = indexing_api.index_directory(
    directory_path="/path/to/documents",
    file_patterns=["*.txt", "*.pdf", "*.md"],
    recursive=True
)
```

### Database Management

```python
# Initialize databases
init_results = vector_db.initialize_databases()
print(f"Initialized: {init_results}")

# Check database health
health = vector_db._check_database_health()
for db_name, status in health.items():
    print(f"{db_name}: {'✅' if status.is_healthy else '❌'}")

# Get statistics
stats = vector_db.get_statistics()
print(f"Total operations: {stats['operation_stats']}")
print(f"Database health: {stats['database_health']}")
```

## 🔧 Configuration Options

### Embedding Models

The system supports multiple embedding model types:

#### Sentence Transformers (Default)
```python
config.embedding.model_type = "sentence_transformers"
config.embedding.model_name = "all-MiniLM-L6-v2"  # Fast and efficient
# config.embedding.model_name = "all-mpnet-base-v2"  # Higher quality
```

#### OpenAI
```python
config.embedding.model_type = "openai"
config.embedding.model_name = "text-embedding-ada-002"
config.embedding.api_key = "your-openai-key"
```

#### Cohere
```python
config.embedding.model_type = "cohere"
config.embedding.model_name = "embed-english-v3.0"
config.embedding.api_key = "your-cohere-key"
```

### Search Configuration

```python
# Basic search settings
config.search.top_k = 10
config.search.score_threshold = 0.7
config.search.rerank = True

# Hybrid search settings
config.search.enable_hybrid_search = True
config.search.alpha = 0.5  # Balance between vector (1.0) and keyword (0.0)
```

### Performance Tuning

```python
# Embedding performance
config.embedding.batch_size = 64  # Larger batches for better throughput
config.embedding.cache_embeddings = True  # Enable caching
config.embedding.normalize_embeddings = True  # Better similarity matching

# Search performance
config.search.rerank_top_k = 100  # Rerank top results only
```

## 📊 Monitoring and Analytics

### System Statistics

```python
# Get comprehensive statistics
stats = vector_db.get_statistics()

print("Operation Stats:")
print(f"  Insertions: {stats['operation_stats']['insertions']}")
print(f"  Searches: {stats['operation_stats']['searches']}")
print(f"  Errors: {stats['operation_stats']['errors']}")

print("Database Health:")
for db, health in stats['database_health'].items():
    print(f"  {db}: {'Healthy' if health['is_healthy'] else 'Unhealthy'}")

print("Embedding Info:")
print(f"  Model: {stats['embedding_info']['model_name']}")
print(f"  Dimension: {stats['embedding_info']['dimension']}")
```

### Search Analytics

```python
retrieval_api = RetrievalAPI(vector_db)

# Perform searches...
# ...

# Get analytics
analytics = retrieval_api.get_analytics()

print("Search Performance:")
print(f"  Total queries: {analytics['retrieval_stats']['total_queries']}")
print(f"  Average time: {analytics['retrieval_stats']['avg_query_time']:.3f}s")
print(f"  Cache hit rate: {analytics['cache_stats']['cache_hit_rate']:.1%}")

print("Popular Terms:")
for term, count in analytics['query_stats']['popular_terms']:
    print(f"  {term}: {count}")
```

## 🔍 Examples

The `examples/` directory contains comprehensive examples:

- **`basic_usage.py`**: Getting started with the system
- **`advanced_search.py`**: Complex search scenarios and features
- **`batch_processing.py`**: Large-scale document processing

Run examples:
```bash
python examples/basic_usage.py
python examples/advanced_search.py
python examples/batch_processing.py
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=kenny_vectordb --cov-report=html

# Run specific test categories
pytest tests/test_basic_functionality.py -v
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/kenny-agi/vectordb.git
cd vectordb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality

The project uses several tools for code quality:

```bash
# Format code
black kenny_vectordb/ examples/ tests/

# Check code style
flake8 kenny_vectordb/ examples/ tests/

# Type checking
mypy kenny_vectordb/

# Run all quality checks
pre-commit run --all-files
```

## 📈 Performance

### Benchmarks

The system is designed for high performance with:

- **Batch Processing**: 1000+ documents/second (depending on model and hardware)
- **Search Latency**: <100ms for semantic search (typical)
- **Memory Usage**: Efficient caching and streaming for large datasets
- **Scalability**: Horizontal scaling with multiple database backends

### Optimization Tips

1. **Use appropriate batch sizes**: 32-64 for most use cases
2. **Enable caching**: Significant speedup for repeated operations
3. **Choose the right model**: Balance between speed and quality
4. **Use hybrid search**: When you need both semantic and keyword matching
5. **Monitor performance**: Use built-in analytics to identify bottlenecks

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

CMD ["python", "-m", "kenny_vectordb.server"]
```

### Kubernetes

Use the provided Helm charts or Kubernetes manifests:

```bash
# Using Helm
helm install kenny-vectordb ./helm/kenny-vectordb

# Using kubectl
kubectl apply -f k8s/
```

### Environment Variables

Set these environment variables for production:

```bash
# Database connections
PINECONE_API_KEY=your_pinecone_key
WEAVIATE_HOST=weaviate.example.com
QDRANT_HOST=qdrant.example.com

# Embedding models
OPENAI_API_KEY=your_openai_key
COHERE_API_KEY=your_cohere_key

# System configuration
KENNY_VECTORDB_ENV=production
KENNY_VECTORDB_LOG_LEVEL=INFO
KENNY_VECTORDB_CACHE_DIR=/data/cache
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Reference](docs/API_REFERENCE.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

### Community
- [GitHub Issues](https://github.com/kenny-agi/vectordb/issues)
- [Discussions](https://github.com/kenny-agi/vectordb/discussions)
- [Wiki](https://github.com/kenny-agi/vectordb/wiki)

### Professional Support
For enterprise support and consulting, contact: support@kenny-agi.com

---

**Kenny Vector Database** - Powering intelligent search and retrieval for the Kenny AGI ecosystem.

Built with ❤️ by the Kenny AGI team.