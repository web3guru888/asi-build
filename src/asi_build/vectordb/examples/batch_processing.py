#!/usr/bin/env python3
"""
Batch processing example for Kenny Vector Database System.

This script demonstrates:
1. Batch document indexing
2. File and directory processing
3. Progress tracking and monitoring
4. Error handling and recovery
5. Performance optimization
"""

import logging
import sys
import os
import time
import json
from pathlib import Path
from typing import List

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenny_vectordb import VectorDBConfig, UnifiedVectorDB
from kenny_vectordb.api.indexing import IndexingAPI, Document

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_files(data_dir: Path) -> List[Path]:
    """Create sample text files for batch processing."""
    data_dir.mkdir(exist_ok=True)
    
    sample_documents = [
        {
            "filename": "ai_research_2023.txt",
            "content": """
            Artificial Intelligence Research Trends in 2023
            
            The year 2023 has been remarkable for AI research, with significant breakthroughs
            in large language models, computer vision, and reinforcement learning. 
            
            Key developments include:
            - GPT-4 and advanced language modeling
            - Stable diffusion and AI-generated art
            - Autonomous vehicle improvements
            - Medical AI diagnostic tools
            
            These advances are reshaping industries from healthcare to entertainment,
            demonstrating the transformative power of artificial intelligence.
            """
        },
        {
            "filename": "climate_solutions.txt", 
            "content": """
            Climate Change Solutions and Innovations
            
            Addressing climate change requires innovative solutions across multiple sectors.
            Recent technological advances are providing hope for a sustainable future.
            
            Promising technologies include:
            - Advanced solar panel efficiency
            - Carbon capture and storage systems
            - Electric vehicle battery improvements
            - Smart grid energy management
            - Green hydrogen production
            
            Governments and companies worldwide are investing billions in these clean
            technologies to achieve net-zero emissions goals.
            """
        },
        {
            "filename": "quantum_computing_basics.txt",
            "content": """
            Quantum Computing Fundamentals
            
            Quantum computing represents a fundamental shift in how we process information.
            Unlike classical bits that are either 0 or 1, quantum bits (qubits) can exist
            in superposition states.
            
            Key concepts:
            - Superposition: qubits can be in multiple states simultaneously
            - Entanglement: qubits can be correlated across distances
            - Interference: quantum states can amplify correct answers
            
            Applications include cryptography, drug discovery, financial modeling,
            and optimization problems that are intractable for classical computers.
            """
        },
        {
            "filename": "space_exploration_2023.txt",
            "content": """
            Space Exploration Milestones
            
            2023 has been an exciting year for space exploration with multiple successful
            missions and technological demonstrations.
            
            Notable achievements:
            - James Webb Space Telescope discoveries
            - Mars rover sample collection progress  
            - Private space company launches
            - International Space Station research
            - Artemis program lunar preparations
            
            These missions are expanding our understanding of the universe and paving
            the way for human exploration of Mars and beyond.
            """
        },
        {
            "filename": "biotechnology_advances.txt",
            "content": """
            Biotechnology Breakthroughs
            
            Biotechnology continues to advance at an unprecedented pace, offering new
            solutions for health, agriculture, and environmental challenges.
            
            Recent breakthroughs:
            - CRISPR gene editing improvements
            - mRNA vaccine platform expansion
            - Personalized medicine developments
            - Synthetic biology applications
            - Bioengineered materials
            
            These technologies are revolutionizing how we treat diseases, produce food,
            and create sustainable materials for various industries.
            """
        },
        {
            "filename": "renewable_energy_trends.txt",
            "content": """
            Renewable Energy Market Trends
            
            The renewable energy sector continues to grow rapidly as costs decrease
            and efficiency improves. Solar and wind power are now the cheapest
            sources of electricity in many regions.
            
            Market trends:
            - Solar panel cost reductions
            - Offshore wind farm expansion
            - Energy storage improvements
            - Grid modernization efforts
            - Electric vehicle integration
            
            Government policies and corporate commitments are driving unprecedented
            investment in clean energy infrastructure worldwide.
            """
        }
    ]
    
    created_files = []
    
    for doc in sample_documents:
        file_path = data_dir / doc["filename"]
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(doc["content"].strip())
        created_files.append(file_path)
        
    # Also create some JSON files
    json_docs = [
        {
            "filename": "research_data.json",
            "data": {
                "title": "AI Research Dataset",
                "content": "This dataset contains research papers on artificial intelligence, machine learning algorithms, and neural network architectures. The data includes paper abstracts, keywords, and citation information.",
                "category": "research",
                "tags": ["ai", "research", "dataset", "machine learning"],
                "metadata": {
                    "papers_count": 1500,
                    "date_range": "2020-2023",
                    "languages": ["english"]
                }
            }
        },
        {
            "filename": "product_catalog.json",
            "data": {
                "title": "Green Technology Product Catalog",
                "content": "Comprehensive catalog of environmentally friendly technology products including solar panels, wind turbines, electric vehicle components, and energy storage systems.",
                "category": "catalog",
                "tags": ["green technology", "products", "renewable energy", "sustainability"],
                "metadata": {
                    "product_count": 250,
                    "suppliers": 45,
                    "last_updated": "2023-08-15"
                }
            }
        }
    ]
    
    for doc in json_docs:
        file_path = data_dir / doc["filename"]
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(doc["data"], f, indent=2)
        created_files.append(file_path)
        
    return created_files

def demonstrate_single_document_batch(indexing_api: IndexingAPI):
    """Demonstrate batch indexing of individual documents."""
    print("\n📄 Single Document Batch Processing")
    print("-" * 50)
    
    # Create multiple documents
    documents = []
    topics = [
        ("Machine Learning Applications", "technology", "Machine learning is being applied across industries from healthcare to finance. Predictive models help doctors diagnose diseases, while algorithmic trading systems manage financial portfolios automatically."),
        ("Sustainable Agriculture", "environment", "Modern agriculture is adopting sustainable practices to reduce environmental impact. Precision farming, vertical growing, and organic methods are helping feed growing populations while protecting ecosystems."),
        ("Quantum Sensors", "science", "Quantum sensors use quantum mechanical effects to achieve unprecedented precision in measurements. These devices are revolutionizing fields like navigation, medical imaging, and fundamental physics research."),
        ("Digital Health Platforms", "health", "Digital health platforms are transforming patient care through telemedicine, remote monitoring, and AI-assisted diagnosis. Patients can now access medical expertise from anywhere in the world."),
        ("Smart Cities Infrastructure", "urban", "Smart cities use IoT sensors, data analytics, and automation to optimize urban services. Traffic management, energy distribution, and waste collection are becoming more efficient and responsive.")
    ]
    
    for i, (title, category, content) in enumerate(topics):
        doc = Document(
            content=content,
            title=title,
            category=category,
            tags=[category, "batch_example"],
            metadata={"batch_id": "single_batch_1", "doc_index": i}
        )
        documents.append(doc)
    
    print(f"📋 Created {len(documents)} documents for batch processing")
    
    # Start batch indexing
    job = indexing_api.index_documents_batch(
        documents=documents,
        batch_size=2,  # Small batch size for demonstration
        parallel=True
    )
    
    print(f"🚀 Started batch job: {job.job_id}")
    
    # Monitor progress
    while job.status in ["pending", "processing"]:
        time.sleep(1)
        current_job = indexing_api.get_job_status(job.job_id)
        if current_job:
            print(f"📊 Progress: {current_job.progress:.1%} ({current_job.processed_count}/{current_job.total_count})")
        
    # Final status
    final_job = indexing_api.get_job_status(job.job_id)
    if final_job:
        duration = final_job.end_time - final_job.start_time if final_job.end_time else 0
        print(f"✅ Batch job completed in {duration:.2f}s")
        print(f"📈 Status: {final_job.status}")
        print(f"📊 Processed: {final_job.processed_count}/{final_job.total_count}")

def demonstrate_file_processing(indexing_api: IndexingAPI):
    """Demonstrate processing individual files."""
    print("\n📁 File Processing")
    print("-" * 30)
    
    # Create sample data directory
    data_dir = Path("/tmp/kenny_vectordb_samples")
    sample_files = create_sample_files(data_dir)
    
    print(f"📂 Created {len(sample_files)} sample files in {data_dir}")
    
    # Process files one by one
    successful_files = 0
    for file_path in sample_files:
        print(f"\n📄 Processing: {file_path.name}")
        success = indexing_api.index_file(file_path)
        
        if success:
            successful_files += 1
            print(f"   ✅ Successfully indexed")
        else:
            print(f"   ❌ Failed to index")
    
    print(f"\n📊 File processing summary: {successful_files}/{len(sample_files)} files indexed")

def demonstrate_directory_processing(indexing_api: IndexingAPI):
    """Demonstrate processing entire directories."""
    print("\n📂 Directory Processing")
    print("-" * 35)
    
    data_dir = Path("/tmp/kenny_vectordb_samples")
    
    if not data_dir.exists():
        print("❌ Sample data directory not found. Run file processing first.")
        return
    
    # Process entire directory
    print(f"📁 Processing directory: {data_dir}")
    print(f"🔍 Looking for: *.txt, *.json files")
    
    job = indexing_api.index_directory(
        directory_path=data_dir,
        file_patterns=["*.txt", "*.json"],
        recursive=True
    )
    
    print(f"🚀 Started directory processing job: {job.job_id}")
    print(f"📋 Documents to process: {len(job.documents)}")
    
    # Monitor progress with more frequent updates
    last_progress = -1
    while job.status in ["pending", "processing"]:
        time.sleep(0.5)
        current_job = indexing_api.get_job_status(job.job_id)
        if current_job and current_job.progress != last_progress:
            print(f"📊 Progress: {current_job.progress:.1%} ({current_job.processed_count}/{current_job.total_count})")
            last_progress = current_job.progress
    
    # Final results
    final_job = indexing_api.get_job_status(job.job_id)
    if final_job:
        duration = final_job.end_time - final_job.start_time if final_job.end_time else 0
        print(f"\n✅ Directory processing completed in {duration:.2f}s")
        print(f"📈 Status: {final_job.status}")
        print(f"📊 Results: {final_job.processed_count}/{final_job.total_count} documents indexed")

def demonstrate_large_batch_processing(indexing_api: IndexingAPI):
    """Demonstrate processing large batches with progress monitoring."""
    print("\n🏭 Large Batch Processing")
    print("-" * 40)
    
    # Generate a larger dataset
    print("📋 Generating large dataset...")
    large_dataset = []
    
    base_topics = [
        "artificial intelligence", "machine learning", "data science",
        "quantum computing", "biotechnology", "renewable energy",
        "space exploration", "climate change", "medical research",
        "cybersecurity", "robotics", "blockchain technology"
    ]
    
    for i in range(50):  # Create 50 documents
        topic = base_topics[i % len(base_topics)]
        doc = Document(
            content=f"This is document {i+1} about {topic}. " * 10 + 
                   f"It contains detailed information about the latest developments in {topic} "
                   f"and its applications across various industries. The research shows promising "
                   f"results for future innovations in this field.",
            title=f"Research Paper #{i+1}: {topic.title()}",
            category="research" if i % 2 == 0 else "technology",
            tags=[topic.replace(" ", "_"), "research", "large_batch"],
            metadata={
                "doc_id": f"large_batch_{i+1}",
                "priority": "high" if i % 5 == 0 else "normal",
                "batch_size": 50
            }
        )
        large_dataset.append(doc)
    
    print(f"📊 Generated {len(large_dataset)} documents")
    
    # Process with different batch sizes to show performance difference
    batch_sizes = [5, 10, 20]
    
    for batch_size in batch_sizes:
        print(f"\n⚙️  Testing batch size: {batch_size}")
        
        # Use a subset for timing comparison
        test_docs = large_dataset[:20]  # Use first 20 documents
        
        start_time = time.time()
        
        job = indexing_api.index_documents_batch(
            documents=test_docs,
            batch_size=batch_size,
            parallel=True
        )
        
        # Monitor without too much output
        while job.status in ["pending", "processing"]:
            time.sleep(0.2)
            current_job = indexing_api.get_job_status(job.job_id)
        
        final_job = indexing_api.get_job_status(job.job_id)
        total_time = time.time() - start_time
        
        if final_job:
            print(f"   ⏱️  Total time: {total_time:.2f}s")
            print(f"   📊 Success rate: {final_job.processed_count}/{final_job.total_count}")
            print(f"   ⚡ Throughput: {final_job.processed_count/total_time:.1f} docs/sec")

def demonstrate_error_handling_and_recovery(indexing_api: IndexingAPI):
    """Demonstrate error handling and recovery mechanisms."""
    print("\n🛠️  Error Handling & Recovery")
    print("-" * 45)
    
    # Create documents with some that will cause issues
    problematic_docs = [
        Document(content="Normal document content", title="Good Doc 1"),
        Document(content="", title="Empty Content Doc"),  # Empty content
        Document(content="Very short", title="Short Doc"),  # Very short
        Document(content="A" * 10000, title="Very Long Doc"),  # Very long
        Document(content="Normal document content", title="Good Doc 2"),
        Document(content=None, title="Null Content Doc"),  # This should cause an error
    ]
    
    print(f"📋 Testing with {len(problematic_docs)} documents (some problematic)")
    
    # Process and handle errors gracefully
    successful = 0
    failed = 0
    
    for i, doc in enumerate(problematic_docs):
        try:
            # Fix null content before processing
            if doc.content is None:
                doc.content = "Placeholder content for null document"
                
            success = indexing_api.index_document(doc)
            if success:
                successful += 1
                print(f"  ✅ Document {i+1}: {doc.title}")
            else:
                failed += 1
                print(f"  ❌ Document {i+1}: {doc.title} (indexing failed)")
                
        except Exception as e:
            failed += 1
            print(f"  💥 Document {i+1}: {doc.title} (exception: {str(e)[:50]}...)")
    
    print(f"\n📊 Error handling summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success rate: {successful/(successful+failed):.1%}")

def demonstrate_job_management(indexing_api: IndexingAPI):
    """Demonstrate job management and monitoring capabilities."""
    print("\n👔 Job Management")
    print("-" * 25)
    
    # Start multiple jobs
    job_docs = [
        [Document(content=f"Job 1 document {i}", title=f"Job1-Doc{i}") for i in range(5)],
        [Document(content=f"Job 2 document {i}", title=f"Job2-Doc{i}") for i in range(3)],
        [Document(content=f"Job 3 document {i}", title=f"Job3-Doc{i}") for i in range(7)],
    ]
    
    jobs = []
    for i, docs in enumerate(job_docs):
        job = indexing_api.index_documents_batch(docs, batch_size=2, parallel=False)
        jobs.append(job)
        print(f"🚀 Started job {i+1}: {job.job_id[:8]}... ({len(docs)} docs)")
    
    # Monitor all jobs
    print("\n📊 Monitoring job progress...")
    while any(job.status in ["pending", "processing"] for job in jobs):
        time.sleep(0.5)
        
        print("\r📈 Job status: ", end="")
        for i, job in enumerate(jobs):
            current_job = indexing_api.get_job_status(job.job_id)
            if current_job:
                status_symbol = {
                    "pending": "⏳",
                    "processing": "⚙️",
                    "completed": "✅",
                    "failed": "❌"
                }.get(current_job.status, "❓")
                print(f"Job{i+1}:{status_symbol} ", end="")
        print("", end="", flush=True)
    
    print("\n")
    
    # List all jobs
    all_jobs = indexing_api.list_jobs()
    print(f"\n📋 Job Summary ({len(all_jobs)} total jobs):")
    
    status_counts = {}
    for job in all_jobs[-10:]:  # Show last 10 jobs
        status_counts[job.status] = status_counts.get(job.status, 0) + 1
        duration = (job.end_time - job.start_time) if job.end_time else 0
        print(f"  {job.job_id[:12]}... | {job.status:10} | {job.processed_count:2}/{job.total_count:2} docs | {duration:.2f}s")
    
    print(f"\n📊 Status distribution: {status_counts}")

def demonstrate_performance_monitoring(indexing_api: IndexingAPI, vector_db: UnifiedVectorDB):
    """Demonstrate performance monitoring and statistics."""
    print("\n📈 Performance Monitoring")
    print("-" * 35)
    
    # Get comprehensive statistics
    indexing_stats = indexing_api.get_statistics()
    db_stats = vector_db.get_statistics()
    
    print("📊 Indexing Performance:")
    stats = indexing_stats['stats']
    print(f"  📄 Total documents indexed: {stats['total_documents_indexed']}")
    print(f"  ⏱️  Average processing time: {stats['avg_processing_time']:.3f}s")
    print(f"  ✅ Successful indexing: {stats['successful_indexing']}")
    print(f"  ❌ Failed indexing: {stats['failed_indexing']}")
    print(f"  📈 Success rate: {stats['success_rate']:.1%}")
    
    if stats['last_indexing_time']:
        last_indexing = time.time() - stats['last_indexing_time']
        print(f"  🕐 Last indexing: {last_indexing:.1f}s ago")
    
    print("\n📋 Job Statistics:")
    job_stats = indexing_stats['jobs']
    print(f"  📊 Total jobs: {job_stats['total_jobs']}")
    print(f"  ⏳ Pending jobs: {job_stats['pending_jobs']}")
    print(f"  ⚙️  Processing jobs: {job_stats['processing_jobs']}")
    print(f"  ✅ Completed jobs: {job_stats['completed_jobs']}")
    print(f"  ❌ Failed jobs: {job_stats['failed_jobs']}")
    
    print("\n🗄️  Database Statistics:")
    print(f"  📈 Total operations: {db_stats['operation_stats']}")
    
    # Database health
    print("\n🏥 Database Health:")
    for db_name, health in db_stats['database_health'].items():
        status = "✅ Healthy" if health['is_healthy'] else "❌ Unhealthy"
        print(f"  {db_name}: {status} (Response: {health['response_time']:.3f}s)")

def main():
    """Main batch processing demonstration."""
    print("🚀 Kenny Vector Database - Batch Processing Examples")
    print("=" * 70)
    
    # Initialize system
    print("\n⚙️  Initializing system...")
    config = VectorDBConfig()
    
    # Optimize for batch processing
    config.embedding.batch_size = 32
    config.embedding.cache_embeddings = True
    
    vector_db = UnifiedVectorDB(config)
    indexing_api = IndexingAPI(vector_db, max_workers=4)
    
    # Initialize databases
    print("🗄️  Initializing databases...")
    init_results = vector_db.initialize_databases()
    healthy_dbs = [db for db, success in init_results.items() if success]
    print(f"✅ Initialized databases: {healthy_dbs}")
    
    if not healthy_dbs:
        print("❌ No databases available. Please check configuration.")
        return
    
    # Run demonstrations
    try:
        demonstrate_single_document_batch(indexing_api)
        time.sleep(1)
        
        demonstrate_file_processing(indexing_api) 
        time.sleep(1)
        
        demonstrate_directory_processing(indexing_api)
        time.sleep(1)
        
        demonstrate_large_batch_processing(indexing_api)
        time.sleep(1)
        
        demonstrate_error_handling_and_recovery(indexing_api)
        time.sleep(1)
        
        demonstrate_job_management(indexing_api)
        time.sleep(1)
        
        demonstrate_performance_monitoring(indexing_api, vector_db)
        
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        indexing_api.cleanup_completed_jobs(keep_recent=5)
        
        # Clean up sample files
        import shutil
        sample_dir = Path("/tmp/kenny_vectordb_samples")
        if sample_dir.exists():
            shutil.rmtree(sample_dir)
            print("🗑️  Removed sample files")
    
    print("\n✅ Batch processing examples completed!")
    print("🎉 You've mastered batch processing with Kenny Vector Database!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Batch processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in batch processing: {str(e)}")
        logger.exception("Batch processing failed:")
    finally:
        print("\n👋 Thanks for exploring Kenny Vector Database batch processing!")