#!/usr/bin/env python3
"""
Advanced search example for Kenny Vector Database System.

This script demonstrates:
1. Complex query construction
2. Faceted search
3. Query optimization
4. Result reranking
5. Recommendation systems
"""

import logging
import sys
import os
import time
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenny_vectordb import VectorDBConfig, UnifiedVectorDB
from kenny_vectordb.api.indexing import IndexingAPI, Document
from kenny_vectordb.api.retrieval import RetrievalAPI, RetrievalQuery

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_dataset() -> List[Document]:
    """Create a larger sample dataset for advanced search examples."""
    documents = [
        # Technology documents
        Document(
            content="Deep learning neural networks have revolutionized artificial intelligence. "
                   "Convolutional neural networks excel at image recognition tasks, while "
                   "recurrent neural networks are powerful for sequential data processing.",
            title="Deep Learning Revolution",
            category="technology",
            tags=["ai", "deep learning", "neural networks", "cnn", "rnn"],
            metadata={"author": "Dr. Smith", "year": 2023, "views": 1500}
        ),
        Document(
            content="Natural language processing enables machines to understand human language. "
                   "Large language models like GPT and BERT have achieved remarkable performance "
                   "in text generation, translation, and question answering tasks.",
            title="NLP Breakthroughs",
            category="technology",
            tags=["nlp", "language models", "gpt", "bert", "ai"],
            metadata={"author": "Prof. Johnson", "year": 2023, "views": 2100}
        ),
        Document(
            content="Computer vision algorithms can analyze and interpret visual information. "
                   "Applications include autonomous vehicles, medical imaging, facial recognition, "
                   "and augmented reality systems.",
            title="Computer Vision Applications",
            category="technology",
            tags=["computer vision", "autonomous vehicles", "medical imaging", "ar"],
            metadata={"author": "Dr. Chen", "year": 2022, "views": 890}
        ),
        
        # Science documents
        Document(
            content="CRISPR-Cas9 technology allows precise editing of DNA sequences. "
                   "This gene editing tool has potential applications in treating genetic diseases, "
                   "improving crop yields, and advancing biological research.",
            title="CRISPR Gene Editing",
            category="science",
            tags=["crispr", "gene editing", "dna", "biotechnology", "genetics"],
            metadata={"author": "Dr. Martinez", "year": 2023, "views": 1800}
        ),
        Document(
            content="Quantum entanglement is a phenomenon where particles become correlated. "
                   "Einstein called it 'spooky action at a distance.' It's fundamental to "
                   "quantum computing and quantum communication technologies.",
            title="Quantum Entanglement Explained",
            category="science",
            tags=["quantum", "entanglement", "physics", "quantum computing"],
            metadata={"author": "Prof. Wilson", "year": 2022, "views": 750}
        ),
        Document(
            content="The James Webb Space Telescope has captured stunning images of distant galaxies. "
                   "Its infrared capabilities allow us to see further into space and time than "
                   "ever before, revealing the early universe's secrets.",
            title="James Webb Telescope Discoveries",
            category="science",
            tags=["space", "telescope", "astronomy", "galaxies", "infrared"],
            metadata={"author": "Dr. Brown", "year": 2023, "views": 3200}
        ),
        
        # Environment documents
        Document(
            content="Solar panel efficiency has improved dramatically with perovskite technology. "
                   "These next-generation solar cells can achieve higher energy conversion rates "
                   "at lower costs than traditional silicon panels.",
            title="Next-Gen Solar Technology",
            category="environment",
            tags=["solar", "renewable energy", "perovskite", "clean technology"],
            metadata={"author": "Dr. Green", "year": 2023, "views": 1200}
        ),
        Document(
            content="Carbon capture and storage technologies can help reduce atmospheric CO2. "
                   "Direct air capture systems pull carbon dioxide from the atmosphere and "
                   "store it underground or convert it into useful products.",
            title="Carbon Capture Solutions",
            category="environment",
            tags=["carbon capture", "climate change", "co2", "environmental technology"],
            metadata={"author": "Prof. Davis", "year": 2023, "views": 950}
        ),
        Document(
            content="Electric vehicle adoption is accelerating globally. Improvements in battery "
                   "technology, charging infrastructure, and government incentives are driving "
                   "the transition from fossil fuel vehicles.",
            title="Electric Vehicle Revolution",
            category="environment",
            tags=["electric vehicles", "battery", "clean transport", "sustainability"],
            metadata={"author": "Dr. White", "year": 2023, "views": 2800}
        ),
        
        # Health documents
        Document(
            content="Personalized medicine uses genetic information to tailor treatments. "
                   "By analyzing a patient's DNA, doctors can prescribe medications and "
                   "therapies that are most likely to be effective for that individual.",
            title="Personalized Medicine Advances",
            category="health",
            tags=["personalized medicine", "genetics", "healthcare", "precision medicine"],
            metadata={"author": "Dr. Taylor", "year": 2023, "views": 1350}
        ),
        Document(
            content="Telemedicine has transformed healthcare delivery. Remote consultations, "
                   "digital health monitoring, and AI-assisted diagnosis are making "
                   "healthcare more accessible and efficient.",
            title="Telemedicine Revolution",
            category="health",
            tags=["telemedicine", "digital health", "remote care", "healthcare technology"],
            metadata={"author": "Dr. Anderson", "year": 2022, "views": 2200}
        ),
        Document(
            content="Immunotherapy harnesses the body's immune system to fight cancer. "
                   "CAR-T cell therapy and checkpoint inhibitors have shown remarkable "
                   "success in treating various types of cancer.",
            title="Cancer Immunotherapy",
            category="health",
            tags=["immunotherapy", "cancer", "car-t", "medical treatment"],
            metadata={"author": "Prof. Lee", "year": 2023, "views": 1750}
        ),
    ]
    
    return documents

def demonstrate_basic_search(retrieval_api: RetrievalAPI):
    """Demonstrate basic search capabilities."""
    print("\n🔍 Basic Search Examples")
    print("-" * 40)
    
    queries = [
        "artificial intelligence machine learning",
        "quantum physics computing",
        "renewable energy solar panels",
        "gene editing CRISPR technology"
    ]
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        
        # Simple semantic search
        simple_query = RetrievalQuery(
            query=query,
            search_mode="semantic",
            top_k=3
        )
        
        result = retrieval_api.search(simple_query)
        
        print(f"📊 Found {result.total_found} results in {result.query_time:.3f}s")
        
        for i, res in enumerate(result.results[:2], 1):
            print(f"  {i}. {res.metadata.get('title', 'Untitled')} (Score: {res.score:.3f})")
            print(f"     Author: {res.metadata.get('author', 'Unknown')}")
            print(f"     Category: {res.metadata.get('category', 'Unknown')}")

def demonstrate_faceted_search(retrieval_api: RetrievalAPI):
    """Demonstrate faceted search with aggregations."""
    print("\n🎯 Faceted Search Examples")
    print("-" * 40)
    
    # Search with facets
    faceted_query = RetrievalQuery(
        query="technology artificial intelligence",
        search_mode="semantic",
        top_k=10,
        facets=["category", "tags", "content_length"]
    )
    
    result = retrieval_api.search(faceted_query)
    
    print(f"📊 Query: '{faceted_query.query}'")
    print(f"📈 Results: {result.total_found} documents in {result.query_time:.3f}s")
    
    # Display facets
    for facet_name, facet_result in result.facets.items():
        print(f"\n🏷️  {facet_name.upper()} Facet:")
        for value, count in sorted(facet_result.values.items(), key=lambda x: x[1], reverse=True):
            print(f"    {value}: {count}")

def demonstrate_filtered_search(retrieval_api: RetrievalAPI):
    """Demonstrate advanced filtering."""
    print("\n🎛️  Filtered Search Examples")
    print("-" * 40)
    
    # Category filtering
    print("\n📂 Filtering by category 'technology':")
    tech_query = RetrievalQuery(
        query="learning algorithms neural networks",
        search_mode="semantic",
        top_k=5,
        category_filter=["technology"]
    )
    
    result = retrieval_api.search(tech_query)
    for i, res in enumerate(result.results, 1):
        print(f"  {i}. {res.metadata.get('title', 'Untitled')}")
        print(f"     Category: {res.metadata.get('category')}")
    
    # Tag filtering
    print("\n🏷️  Filtering by tags containing 'ai':")
    tag_query = RetrievalQuery(
        query="machine learning",
        search_mode="semantic", 
        top_k=5,
        tag_filter=["ai", "deep learning"]
    )
    
    result = retrieval_api.search(tag_query)
    for i, res in enumerate(result.results, 1):
        print(f"  {i}. {res.metadata.get('title', 'Untitled')}")
        print(f"     Tags: {res.metadata.get('tags')}")

def demonstrate_hybrid_search(vector_db: UnifiedVectorDB):
    """Demonstrate hybrid search combining vector and keyword search."""
    print("\n🔄 Hybrid Search Examples")
    print("-" * 40)
    
    queries = [
        ("neural networks deep learning", 0.8, 0.2),  # More semantic
        ("CRISPR gene editing", 0.5, 0.5),  # Balanced
        ("James Webb telescope", 0.3, 0.7),  # More keyword
    ]
    
    for query, vector_weight, keyword_weight in queries:
        print(f"\n📝 Query: '{query}' (Vector: {vector_weight}, Keyword: {keyword_weight})")
        
        results = vector_db.hybrid_search(
            query=query,
            top_k=3,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight
        )
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.metadata.get('title', 'Untitled')} (Score: {result.score:.3f})")
            print(f"     Source DB: {result.source_db}")

def demonstrate_recommendations(retrieval_api: RetrievalAPI, vector_db: UnifiedVectorDB):
    """Demonstrate recommendation system."""
    print("\n🎯 Recommendation System Examples")
    print("-" * 40)
    
    # Simulate user interaction history with document IDs
    # In a real system, these would be actual document IDs from user interactions
    
    # First, get some document IDs by searching
    search_result = vector_db.search("artificial intelligence", top_k=3)
    user_history = [result.id for result in search_result]
    
    if user_history:
        print(f"👤 User interaction history: {len(user_history)} documents")
        
        # Get recommendations
        recommendations = retrieval_api.get_recommendations(
            user_history=user_history,
            top_k=5,
            diversity_factor=0.3
        )
        
        print(f"💡 Generated {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec.metadata.get('title', 'Untitled')} (Score: {rec.score:.3f})")
            print(f"     Category: {rec.metadata.get('category')}")
            print(f"     Reason: Similar to your recent interests")

def demonstrate_query_optimization(retrieval_api: RetrievalAPI):
    """Demonstrate query optimization and suggestions."""
    print("\n⚡ Query Optimization Examples")
    print("-" * 40)
    
    # Test query completions
    partial_queries = [
        "artificial intell",
        "quantum comput",
        "gene edit"
    ]
    
    for partial in partial_queries:
        completions = retrieval_api.suggest_completions(partial, max_suggestions=3)
        print(f"📝 '{partial}' → Suggestions: {completions}")
    
    # Demonstrate query optimization
    test_queries = [
        "the best artificial intelligence algorithms",
        "what are quantum computing applications?",
        "how does gene editing work with CRISPR"
    ]
    
    for query in test_queries:
        optimized = retrieval_api.query_optimizer.optimize_query(query)
        print(f"🔧 Original: '{query}'")
        print(f"   Optimized: '{optimized}'")

def demonstrate_analytics(retrieval_api: RetrievalAPI, indexing_api: IndexingAPI, vector_db: UnifiedVectorDB):
    """Demonstrate analytics and monitoring."""
    print("\n📊 Analytics & Monitoring")
    print("-" * 40)
    
    # Retrieval analytics
    retrieval_analytics = retrieval_api.get_analytics()
    print("\n🔍 Retrieval Analytics:")
    print(f"  Total queries: {retrieval_analytics['retrieval_stats']['total_queries']}")
    print(f"  Success rate: {retrieval_analytics['query_stats']['success_rate']:.2%}")
    print(f"  Cache hit rate: {retrieval_analytics['cache_stats']['cache_hit_rate']:.2%}")
    print(f"  Avg query time: {retrieval_analytics['retrieval_stats']['avg_query_time']:.3f}s")
    
    # Popular terms
    popular_terms = retrieval_analytics['query_stats']['popular_terms']
    if popular_terms:
        print("\n🔥 Popular Search Terms:")
        for term, count in popular_terms[:5]:
            print(f"    {term}: {count} times")
    
    # Indexing analytics  
    indexing_analytics = indexing_api.get_statistics()
    print("\n📥 Indexing Analytics:")
    print(f"  Documents indexed: {indexing_analytics['stats']['total_documents_indexed']}")
    print(f"  Success rate: {indexing_analytics['stats']['success_rate']:.2%}")
    print(f"  Avg processing time: {indexing_analytics['stats']['avg_processing_time']:.3f}s")
    
    # Database health
    db_stats = vector_db.get_statistics()
    print("\n🏥 Database Health:")
    for db_name, health in db_stats['database_health'].items():
        status = "✅ Healthy" if health['is_healthy'] else "❌ Unhealthy"
        print(f"  {db_name}: {status} (Response: {health['response_time']:.3f}s)")

def main():
    """Main advanced search demonstration."""
    print("🚀 Kenny Vector Database - Advanced Search Examples")
    print("=" * 70)
    
    # Initialize system
    print("\n⚙️  Initializing system...")
    config = VectorDBConfig()
    config.search.top_k = 10
    config.search.rerank = True
    
    vector_db = UnifiedVectorDB(config)
    indexing_api = IndexingAPI(vector_db)
    retrieval_api = RetrievalAPI(vector_db)
    
    # Create and index sample dataset
    print("\n📚 Creating sample dataset...")
    documents = create_sample_dataset()
    print(f"Created {len(documents)} documents")
    
    print("\n🔄 Indexing documents...")
    successful = 0
    for doc in documents:
        if indexing_api.index_document(doc):
            successful += 1
    
    print(f"✅ Successfully indexed {successful}/{len(documents)} documents")
    
    # Wait a moment for indexing to complete
    time.sleep(2)
    
    # Run demonstrations
    demonstrate_basic_search(retrieval_api)
    demonstrate_faceted_search(retrieval_api)
    demonstrate_filtered_search(retrieval_api)
    demonstrate_hybrid_search(vector_db)
    demonstrate_recommendations(retrieval_api, vector_db)
    demonstrate_query_optimization(retrieval_api)
    demonstrate_analytics(retrieval_api, indexing_api, vector_db)
    
    print("\n✅ Advanced search examples completed!")
    print("🎉 You've explored the advanced capabilities of Kenny Vector Database!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running example: {str(e)}")
        logger.exception("Advanced search example failed:")
    finally:
        print("\n👋 Thanks for exploring Kenny Vector Database!")