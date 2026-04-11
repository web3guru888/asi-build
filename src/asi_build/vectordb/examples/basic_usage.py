#!/usr/bin/env python3
"""
Basic usage example for Kenny Vector Database System.

This script demonstrates:
1. Setting up the vector database
2. Indexing documents
3. Performing searches
4. Managing configurations
"""

import logging
import os
import sys

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenny_vectordb import IndexingAPI, RetrievalAPI, UnifiedVectorDB, VectorDBConfig
from kenny_vectordb.api.indexing import Document
from kenny_vectordb.core.embeddings import EmbeddingPipeline

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main example function."""
    print("🚀 Kenny Vector Database - Basic Usage Example")
    print("=" * 60)

    # Step 1: Initialize Configuration
    print("\n📋 Step 1: Initializing configuration...")
    config = VectorDBConfig()

    # You can customize the configuration
    config.embedding.model_name = "sentence-transformers/all-MiniLM-L6-v2"
    config.embedding.batch_size = 16
    config.search.top_k = 5

    print(f"✅ Using embedding model: {config.embedding.model_name}")
    print(f"✅ Search top_k: {config.search.top_k}")

    # Step 2: Initialize Vector Database
    print("\n🗄️  Step 2: Initializing vector database...")
    vector_db = UnifiedVectorDB(config)

    # Initialize databases (this creates indexes/collections if they don't exist)
    init_results = vector_db.initialize_databases()
    print(f"✅ Database initialization results: {init_results}")

    # Step 3: Create Sample Documents
    print("\n📄 Step 3: Creating sample documents...")
    documents = [
        Document(
            content="Artificial intelligence is transforming the way we work and live. "
            "Machine learning algorithms can now process vast amounts of data "
            "and make predictions with remarkable accuracy.",
            title="AI Revolution",
            category="technology",
            tags=["ai", "machine learning", "technology"],
        ),
        Document(
            content="Climate change is one of the most pressing challenges of our time. "
            "Rising global temperatures are causing sea levels to rise, "
            "extreme weather events to become more frequent, and ecosystems to shift.",
            title="Climate Change Impact",
            category="environment",
            tags=["climate", "environment", "global warming"],
        ),
        Document(
            content="Space exploration has captured human imagination for decades. "
            "Recent missions to Mars have provided valuable insights about "
            "the Red Planet's geology and potential for supporting life.",
            title="Mars Exploration",
            category="science",
            tags=["space", "mars", "exploration", "science"],
        ),
        Document(
            content="Quantum computing represents a paradigm shift in computational power. "
            "Unlike classical computers that use bits, quantum computers use qubits "
            "that can exist in multiple states simultaneously.",
            title="Quantum Computing Basics",
            category="technology",
            tags=["quantum", "computing", "technology", "physics"],
        ),
        Document(
            content="Renewable energy sources like solar and wind power are becoming "
            "increasingly cost-effective. Many countries are investing heavily "
            "in clean energy infrastructure to reduce carbon emissions.",
            title="Renewable Energy Growth",
            category="environment",
            tags=["renewable", "energy", "solar", "wind", "clean energy"],
        ),
    ]

    print(f"✅ Created {len(documents)} sample documents")

    # Step 4: Index Documents
    print("\n🔍 Step 4: Indexing documents...")
    indexing_api = IndexingAPI(vector_db)

    # Index documents one by one
    successful_indexing = 0
    for i, doc in enumerate(documents):
        success = indexing_api.index_document(doc)
        if success:
            successful_indexing += 1
            print(f"✅ Indexed document {i+1}: {doc.title}")
        else:
            print(f"❌ Failed to index document {i+1}: {doc.title}")

    print(f"✅ Successfully indexed {successful_indexing}/{len(documents)} documents")

    # Step 5: Perform Searches
    print("\n🔎 Step 5: Performing searches...")
    retrieval_api = RetrievalAPI(vector_db)

    # Example searches
    search_queries = [
        "artificial intelligence and machine learning",
        "climate change effects",
        "space missions to mars",
        "quantum computing technology",
        "clean renewable energy",
    ]

    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")

        # Perform semantic search
        results = vector_db.semantic_search(query, top_k=3)

        if results:
            for i, result in enumerate(results, 1):
                print(
                    f"  {i}. {result.metadata.get('title', 'Untitled')} (Score: {result.score:.3f})"
                )
                print(f"     Category: {result.metadata.get('category', 'Unknown')}")
                print(f"     Tags: {result.metadata.get('tags', [])}")
                print(f"     Content preview: {result.content[:100]}...")
        else:
            print("  No results found")

    # Step 6: Advanced Search Examples
    print("\n🎯 Step 6: Advanced search examples...")

    # Hybrid search
    print("\n🔄 Hybrid Search (combining vector + keyword):")
    hybrid_results = vector_db.hybrid_search(
        query="machine learning algorithms", top_k=3, vector_weight=0.7, keyword_weight=0.3
    )

    for i, result in enumerate(hybrid_results, 1):
        print(f"  {i}. {result.metadata.get('title', 'Untitled')} (Score: {result.score:.3f})")

    # Filtered search
    print("\n🎛️  Filtered Search (technology category only):")
    from kenny_vectordb.api.retrieval import RetrievalQuery

    filtered_query = RetrievalQuery(
        query="computing and algorithms", top_k=5, category_filter=["technology"]
    )

    filtered_results = retrieval_api.search(filtered_query)

    for i, result in enumerate(filtered_results.results, 1):
        print(f"  {i}. {result.metadata.get('title', 'Untitled')} (Score: {result.score:.3f})")
        print(f"     Category: {result.metadata.get('category', 'Unknown')}")

    # Step 7: Get Statistics
    print("\n📊 Step 7: System statistics...")

    # Vector database statistics
    db_stats = vector_db.get_statistics()
    print("\n🗄️  Database Statistics:")
    print(f"  Operations: {db_stats['operation_stats']}")
    print(f"  Embedding info: {db_stats['embedding_info']['model_name']}")

    # Indexing statistics
    indexing_stats = indexing_api.get_statistics()
    print("\n📥 Indexing Statistics:")
    print(f"  Documents indexed: {indexing_stats['stats']['total_documents_indexed']}")
    print(f"  Success rate: {indexing_stats['stats']['success_rate']:.2%}")

    # Retrieval statistics
    retrieval_stats = retrieval_api.get_analytics()
    print("\n📤 Retrieval Statistics:")
    print(f"  Total queries: {retrieval_stats['retrieval_stats']['total_queries']}")
    print(f"  Successful queries: {retrieval_stats['retrieval_stats']['successful_queries']}")
    print(f"  Average query time: {retrieval_stats['retrieval_stats']['avg_query_time']:.3f}s")

    # Step 8: Cleanup
    print("\n🧹 Step 8: Cleanup (optional)...")
    print("Note: Uncomment the lines below to clear all data")

    # Uncomment to clear all data
    # print("Clearing all data...")
    # clear_results = vector_db.clear_all_data(confirm=True)
    # print(f"Clear results: {clear_results}")

    print("\n✅ Basic usage example completed successfully!")
    print("🎉 You've successfully used Kenny Vector Database!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running example: {str(e)}")
        logger.exception("Example failed with error:")
    finally:
        print("\n👋 Thanks for trying Kenny Vector Database!")
