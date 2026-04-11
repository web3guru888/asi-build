"""
Indexing API for Kenny Vector Database System

This module provides comprehensive indexing capabilities including:
- Batch document processing and indexing
- Real-time indexing with queue management
- Document preprocessing and chunking
- Metadata extraction and enrichment
- Index optimization and management
"""

import asyncio
import json
import logging
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from ..core.embeddings import EmbeddingPipeline
from ..core.utils import TextUtils, timed_operation
from .unified_client import UnifiedVectorDB

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document representation for indexing."""

    id: Optional[str] = None
    content: str = ""
    title: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Set defaults after initialization."""
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class IndexingJob:
    """Indexing job for batch processing."""

    job_id: str
    documents: List[Document]
    status: str = "pending"  # pending, processing, completed, failed
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    processed_count: int = 0
    total_count: int = 0

    def __post_init__(self):
        """Set total count after initialization."""
        self.total_count = len(self.documents)


@dataclass
class IndexingStats:
    """Statistics for indexing operations."""

    total_documents_indexed: int = 0
    total_chunks_created: int = 0
    total_embeddings_generated: int = 0
    avg_processing_time: float = 0.0
    successful_indexing: int = 0
    failed_indexing: int = 0
    last_indexing_time: Optional[float] = None


class DocumentProcessor:
    """Document preprocessing and enrichment."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        extract_keywords: bool = True,
        keyword_count: int = 10,
    ):
        """
        Initialize document processor.

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            extract_keywords: Whether to extract keywords
            keyword_count: Number of keywords to extract
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.extract_keywords = extract_keywords
        self.keyword_count = keyword_count

    def process_document(self, document: Document) -> List[Document]:
        """
        Process document into chunks with metadata enrichment.

        Args:
            document: Input document

        Returns:
            List of processed document chunks
        """
        processed_docs = []

        # Clean and prepare content
        cleaned_content = TextUtils.clean_text(document.content)

        # Extract keywords if enabled
        keywords = []
        if self.extract_keywords:
            keywords = TextUtils.extract_keywords(cleaned_content, self.keyword_count)

        # Create chunks
        if len(cleaned_content) <= self.chunk_size:
            # Document is small enough, don't chunk
            chunks = [cleaned_content]
        else:
            chunks = TextUtils.split_text_chunks(
                cleaned_content,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
                preserve_sentences=True,
            )

        # Create document for each chunk
        for i, chunk in enumerate(chunks):
            chunk_doc = Document(
                id=f"{document.id}_{i}" if len(chunks) > 1 else document.id,
                content=chunk,
                title=document.title,
                source=document.source,
                category=document.category,
                tags=document.tags.copy(),
                metadata=document.metadata.copy(),
                timestamp=document.timestamp,
            )

            # Add chunk-specific metadata
            chunk_doc.metadata.update(
                {
                    "original_id": document.id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk),
                    "keywords": keywords,
                    "word_count": len(chunk.split()),
                    "character_count": len(chunk),
                }
            )

            processed_docs.append(chunk_doc)

        return processed_docs

    def process_file(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Process file into documents.

        Args:
            file_path: Path to file

        Returns:
            List of processed documents
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content based on extension
        if file_path.suffix.lower() == ".txt":
            content = file_path.read_text(encoding="utf-8")
        elif file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    content = data.get("content", json.dumps(data, indent=2))
                elif isinstance(data, list):
                    content = "\n".join(str(item) for item in data)
                else:
                    content = str(data)
        else:
            # Try to read as text
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                logger.error(f"Cannot read file {file_path}: unsupported format or encoding")
                return []

        # Create document
        document = Document(
            content=content,
            title=file_path.stem,
            source=str(file_path),
            category="file",
            metadata={
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "file_extension": file_path.suffix,
                "file_modified": file_path.stat().st_mtime,
            },
        )

        return self.process_document(document)


class IndexingAPI:
    """
    Advanced indexing API for Kenny Vector Database System.

    Provides comprehensive document indexing capabilities with batch processing,
    real-time indexing, and intelligent document preprocessing.
    """

    def __init__(self, vector_db: UnifiedVectorDB, max_workers: int = 4):
        """
        Initialize indexing API.

        Args:
            vector_db: Unified vector database client
            max_workers: Maximum number of worker threads
        """
        self.vector_db = vector_db
        self.max_workers = max_workers

        # Document processor
        self.document_processor = DocumentProcessor()

        # Job management
        self.jobs: Dict[str, IndexingJob] = {}
        self.job_queue = queue.Queue()
        self.worker_pool = ThreadPoolExecutor(max_workers=max_workers)

        # Statistics
        self.stats = IndexingStats()

        # Real-time indexing
        self._realtime_queue = queue.Queue()
        self._realtime_thread = None
        self._realtime_running = False

    def index_document(self, document: Union[Document, Dict[str, Any]]) -> bool:
        """
        Index a single document.

        Args:
            document: Document to index

        Returns:
            Success status
        """
        if isinstance(document, dict):
            document = Document(**document)

        try:
            start_time = time.time()

            # Process document
            processed_docs = self.document_processor.process_document(document)

            # Convert to dict format for database
            doc_dicts = [doc.to_dict() for doc in processed_docs]

            # Insert into database
            result = self.vector_db.insert_documents(doc_dicts)

            if result.success:
                # Update statistics
                self.stats.total_documents_indexed += 1
                self.stats.total_chunks_created += len(processed_docs)
                self.stats.successful_indexing += 1
                self.stats.last_indexing_time = time.time()

                processing_time = time.time() - start_time
                self._update_avg_processing_time(processing_time)

                logger.info(f"Successfully indexed document {document.id}")
                return True
            else:
                self.stats.failed_indexing += 1
                logger.error(f"Failed to index document {document.id}: {result.errors}")
                return False

        except Exception as e:
            self.stats.failed_indexing += 1
            logger.error(f"Error indexing document {document.id}: {str(e)}")
            return False

    def index_documents_batch(
        self,
        documents: List[Union[Document, Dict[str, Any]]],
        batch_size: int = 50,
        parallel: bool = True,
    ) -> IndexingJob:
        """
        Index documents in batch with progress tracking.

        Args:
            documents: List of documents to index
            batch_size: Size of processing batches
            parallel: Whether to use parallel processing

        Returns:
            Indexing job for tracking progress
        """
        # Convert dicts to Document objects
        doc_objects = []
        for doc in documents:
            if isinstance(doc, dict):
                doc_objects.append(Document(**doc))
            else:
                doc_objects.append(doc)

        # Create indexing job
        job_id = str(uuid.uuid4())
        job = IndexingJob(job_id=job_id, documents=doc_objects, status="pending")

        self.jobs[job_id] = job

        # Submit job for processing
        if parallel:
            self.worker_pool.submit(self._process_batch_job_parallel, job, batch_size)
        else:
            self.worker_pool.submit(self._process_batch_job_sequential, job, batch_size)

        logger.info(f"Started batch indexing job {job_id} with {len(doc_objects)} documents")
        return job

    def _process_batch_job_sequential(self, job: IndexingJob, batch_size: int):
        """Process batch job sequentially."""
        job.status = "processing"
        job.start_time = time.time()

        try:
            total_docs = len(job.documents)
            processed_count = 0

            # Process in batches
            for i in range(0, total_docs, batch_size):
                batch = job.documents[i : i + batch_size]

                for document in batch:
                    try:
                        success = self.index_document(document)
                        if success:
                            processed_count += 1
                    except Exception as e:
                        logger.error(f"Error processing document {document.id}: {str(e)}")

                    job.processed_count = processed_count
                    job.progress = processed_count / total_docs

            job.status = "completed"
            job.end_time = time.time()
            logger.info(
                f"Completed batch job {job.job_id}: {processed_count}/{total_docs} documents"
            )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.end_time = time.time()
            logger.error(f"Batch job {job.job_id} failed: {str(e)}")

    def _process_batch_job_parallel(self, job: IndexingJob, batch_size: int):
        """Process batch job with parallel workers."""
        job.status = "processing"
        job.start_time = time.time()

        try:
            total_docs = len(job.documents)
            processed_count = 0

            # Create batches
            batches = [job.documents[i : i + batch_size] for i in range(0, total_docs, batch_size)]

            # Process batches in parallel
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batches))) as executor:
                future_to_batch = {
                    executor.submit(self._process_document_batch, batch): batch for batch in batches
                }

                for future in as_completed(future_to_batch):
                    try:
                        batch_success_count = future.result()
                        processed_count += batch_success_count

                        job.processed_count = processed_count
                        job.progress = processed_count / total_docs

                    except Exception as e:
                        logger.error(f"Batch processing error: {str(e)}")

            job.status = "completed"
            job.end_time = time.time()
            logger.info(
                f"Completed parallel batch job {job.job_id}: {processed_count}/{total_docs} documents"
            )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.end_time = time.time()
            logger.error(f"Parallel batch job {job.job_id} failed: {str(e)}")

    def _process_document_batch(self, documents: List[Document]) -> int:
        """Process a batch of documents and return success count."""
        success_count = 0

        for document in documents:
            try:
                if self.index_document(document):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error processing document {document.id}: {str(e)}")

        return success_count

    def index_file(self, file_path: Union[str, Path]) -> bool:
        """
        Index a single file.

        Args:
            file_path: Path to file

        Returns:
            Success status
        """
        try:
            documents = self.document_processor.process_file(file_path)

            if not documents:
                logger.warning(f"No documents extracted from file {file_path}")
                return False

            # Index all documents from file
            success_count = 0
            for document in documents:
                if self.index_document(document):
                    success_count += 1

            logger.info(f"Indexed {success_count}/{len(documents)} documents from file {file_path}")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {str(e)}")
            return False

    def index_directory(
        self,
        directory_path: Union[str, Path],
        file_patterns: List[str] = None,
        recursive: bool = True,
    ) -> IndexingJob:
        """
        Index all files in a directory.

        Args:
            directory_path: Path to directory
            file_patterns: File patterns to match (e.g., ['*.txt', '*.json'])
            recursive: Whether to search recursively

        Returns:
            Indexing job for tracking progress
        """
        directory_path = Path(directory_path)

        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")

        # Find files
        files = []
        if file_patterns:
            for pattern in file_patterns:
                if recursive:
                    files.extend(directory_path.rglob(pattern))
                else:
                    files.extend(directory_path.glob(pattern))
        else:
            # Default patterns
            default_patterns = ["*.txt", "*.json", "*.md"]
            for pattern in default_patterns:
                if recursive:
                    files.extend(directory_path.rglob(pattern))
                else:
                    files.extend(directory_path.glob(pattern))

        # Process files into documents
        all_documents = []
        for file_path in files:
            try:
                file_documents = self.document_processor.process_file(file_path)
                all_documents.extend(file_documents)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")

        logger.info(f"Found {len(files)} files, created {len(all_documents)} documents")

        # Start batch indexing
        return self.index_documents_batch(all_documents)

    def start_realtime_indexing(self):
        """Start real-time indexing service."""
        if self._realtime_running:
            logger.warning("Real-time indexing already running")
            return

        self._realtime_running = True
        self._realtime_thread = threading.Thread(target=self._realtime_worker, daemon=True)
        self._realtime_thread.start()

        logger.info("Started real-time indexing service")

    def stop_realtime_indexing(self):
        """Stop real-time indexing service."""
        self._realtime_running = False

        if self._realtime_thread:
            self._realtime_thread.join(timeout=5)

        logger.info("Stopped real-time indexing service")

    def queue_for_indexing(self, document: Union[Document, Dict[str, Any]]):
        """
        Queue document for real-time indexing.

        Args:
            document: Document to queue for indexing
        """
        if isinstance(document, dict):
            document = Document(**document)

        self._realtime_queue.put(document)

    def _realtime_worker(self):
        """Real-time indexing worker thread."""
        while self._realtime_running:
            try:
                # Get document from queue with timeout
                document = self._realtime_queue.get(timeout=1)

                # Index document
                self.index_document(document)

                self._realtime_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Real-time indexing error: {str(e)}")

    def get_job_status(self, job_id: str) -> Optional[IndexingJob]:
        """Get status of indexing job."""
        return self.jobs.get(job_id)

    def list_jobs(self, status: Optional[str] = None) -> List[IndexingJob]:
        """
        List indexing jobs.

        Args:
            status: Filter by job status

        Returns:
            List of indexing jobs
        """
        jobs = list(self.jobs.values())

        if status:
            jobs = [job for job in jobs if job.status == status]

        return jobs

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel indexing job.

        Args:
            job_id: Job ID to cancel

        Returns:
            Success status
        """
        job = self.jobs.get(job_id)

        if not job:
            return False

        if job.status in ["completed", "failed"]:
            return False

        job.status = "cancelled"
        job.end_time = time.time()

        logger.info(f"Cancelled indexing job {job_id}")
        return True

    def _update_avg_processing_time(self, processing_time: float):
        """Update average processing time."""
        if self.stats.avg_processing_time == 0:
            self.stats.avg_processing_time = processing_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.avg_processing_time = (
                alpha * processing_time + (1 - alpha) * self.stats.avg_processing_time
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        return {
            "stats": {
                "total_documents_indexed": self.stats.total_documents_indexed,
                "total_chunks_created": self.stats.total_chunks_created,
                "avg_processing_time": self.stats.avg_processing_time,
                "successful_indexing": self.stats.successful_indexing,
                "failed_indexing": self.stats.failed_indexing,
                "last_indexing_time": self.stats.last_indexing_time,
                "success_rate": (
                    self.stats.successful_indexing
                    / max(self.stats.successful_indexing + self.stats.failed_indexing, 1)
                ),
            },
            "jobs": {
                "total_jobs": len(self.jobs),
                "pending_jobs": len([j for j in self.jobs.values() if j.status == "pending"]),
                "processing_jobs": len([j for j in self.jobs.values() if j.status == "processing"]),
                "completed_jobs": len([j for j in self.jobs.values() if j.status == "completed"]),
                "failed_jobs": len([j for j in self.jobs.values() if j.status == "failed"]),
            },
            "realtime": {
                "is_running": self._realtime_running,
                "queue_size": self._realtime_queue.qsize(),
            },
        }

    def cleanup_completed_jobs(self, keep_recent: int = 10):
        """
        Cleanup completed jobs to save memory.

        Args:
            keep_recent: Number of recent jobs to keep
        """
        completed_jobs = [
            job for job in self.jobs.values() if job.status in ["completed", "failed", "cancelled"]
        ]

        # Sort by end time
        completed_jobs.sort(key=lambda x: x.end_time or 0, reverse=True)

        # Remove old jobs
        jobs_to_remove = completed_jobs[keep_recent:]

        for job in jobs_to_remove:
            del self.jobs[job.job_id]

        logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")

    def shutdown(self):
        """Shutdown indexing API and cleanup resources."""
        # Stop real-time indexing
        self.stop_realtime_indexing()

        # Cancel pending jobs
        for job in self.jobs.values():
            if job.status in ["pending", "processing"]:
                self.cancel_job(job.job_id)

        # Shutdown thread pool
        self.worker_pool.shutdown(wait=True)

        logger.info("Indexing API shutdown completed")
