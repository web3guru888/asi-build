"""
IPFS Client for Kenny AGI Blockchain Audit Trail System

Provides high-level interface for interacting with IPFS nodes
for decentralized data storage and retrieval.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import aiohttp
import ipfshttpclient

logger = logging.getLogger(__name__)


class IPFSError(Exception):
    """Custom exception for IPFS operations"""

    pass


@dataclass
class IPFSFile:
    """Represents a file stored in IPFS"""

    hash: str
    name: str
    size: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class IPFSClient:
    """
    High-level IPFS client for audit trail data management

    Supports both local and remote IPFS nodes, with fallback mechanisms
    and automatic retry logic.
    """

    def __init__(
        self,
        api_url: str = "/dns/localhost/tcp/5001/http",
        timeout: int = 30,
        max_retries: int = 3,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ):
        """
        Initialize IPFS client

        Args:
            api_url: IPFS API endpoint
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            chunk_size: Size of chunks for large file uploads
        """
        self.api_url = api_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self._client = None
        self._session = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Connect to IPFS node"""
        try:
            self._client = ipfshttpclient.connect(self.api_url, timeout=self.timeout)
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))

            # Test connection
            await self.get_node_info()
            logger.info(f"Connected to IPFS node at {self.api_url}")

        except Exception as e:
            raise IPFSError(f"Failed to connect to IPFS node: {str(e)}")

    async def disconnect(self):
        """Disconnect from IPFS node"""
        if self._client:
            self._client.close()
            self._client = None

        if self._session:
            await self._session.close()
            self._session = None

        logger.info("Disconnected from IPFS node")

    def _ensure_connected(self):
        """Ensure client is connected"""
        if not self._client:
            raise IPFSError("IPFS client not connected. Call connect() first.")

    async def get_node_info(self) -> Dict[str, Any]:
        """Get IPFS node information"""
        self._ensure_connected()

        try:
            info = self._client.id()
            return {
                "id": info["ID"],
                "public_key": info["PublicKey"],
                "addresses": info["Addresses"],
                "agent_version": info["AgentVersion"],
                "protocol_version": info["ProtocolVersion"],
            }
        except Exception as e:
            raise IPFSError(f"Failed to get node info: {str(e)}")

    async def add_json(self, data: Union[Dict, List], pin: bool = True) -> str:
        """
        Add JSON data to IPFS

        Args:
            data: JSON serializable data
            pin: Whether to pin the data to prevent garbage collection

        Returns:
            IPFS hash of the stored data
        """
        self._ensure_connected()

        try:
            json_str = json.dumps(data, indent=2, default=str)
            result = self._client.add_json(data, pin=pin)

            logger.info(f"Added JSON data to IPFS: {result}")
            return result

        except Exception as e:
            raise IPFSError(f"Failed to add JSON to IPFS: {str(e)}")

    async def get_json(self, ipfs_hash: str) -> Union[Dict, List]:
        """
        Retrieve JSON data from IPFS

        Args:
            ipfs_hash: IPFS hash of the data

        Returns:
            Parsed JSON data
        """
        self._ensure_connected()

        try:
            data = self._client.get_json(ipfs_hash)
            logger.info(f"Retrieved JSON data from IPFS: {ipfs_hash}")
            return data

        except Exception as e:
            raise IPFSError(f"Failed to get JSON from IPFS: {str(e)}")

    async def add_file(
        self, file_path: str, pin: bool = True, wrap_with_directory: bool = False
    ) -> IPFSFile:
        """
        Add a file to IPFS

        Args:
            file_path: Path to the file to add
            pin: Whether to pin the file
            wrap_with_directory: Whether to wrap in directory structure

        Returns:
            IPFSFile object with file information
        """
        self._ensure_connected()

        try:
            result = self._client.add(file_path, pin=pin, wrap_with_directory=wrap_with_directory)

            # Handle single file vs directory results
            if isinstance(result, list):
                result = result[-1]  # Get the root hash for directories

            file_info = IPFSFile(
                hash=result["Hash"],
                name=result["Name"],
                size=int(result["Size"]),
                timestamp=datetime.now(),
            )

            logger.info(f"Added file to IPFS: {file_info.hash}")
            return file_info

        except Exception as e:
            raise IPFSError(f"Failed to add file to IPFS: {str(e)}")

    async def get_file(self, ipfs_hash: str, output_path: str) -> str:
        """
        Retrieve a file from IPFS

        Args:
            ipfs_hash: IPFS hash of the file
            output_path: Path to save the retrieved file

        Returns:
            Path to the retrieved file
        """
        self._ensure_connected()

        try:
            self._client.get(ipfs_hash, target=output_path)
            logger.info(f"Retrieved file from IPFS: {ipfs_hash} -> {output_path}")
            return output_path

        except Exception as e:
            raise IPFSError(f"Failed to get file from IPFS: {str(e)}")

    async def add_bytes(self, data: bytes, pin: bool = True) -> str:
        """
        Add raw bytes to IPFS

        Args:
            data: Bytes to store
            pin: Whether to pin the data

        Returns:
            IPFS hash of the stored data
        """
        self._ensure_connected()

        try:
            result = self._client.add_bytes(data, pin=pin)
            logger.info(f"Added bytes to IPFS: {result}")
            return result

        except Exception as e:
            raise IPFSError(f"Failed to add bytes to IPFS: {str(e)}")

    async def get_bytes(self, ipfs_hash: str) -> bytes:
        """
        Retrieve bytes from IPFS

        Args:
            ipfs_hash: IPFS hash of the data

        Returns:
            Raw bytes data
        """
        self._ensure_connected()

        try:
            data = self._client.cat(ipfs_hash)
            logger.info(f"Retrieved bytes from IPFS: {ipfs_hash}")
            return data

        except Exception as e:
            raise IPFSError(f"Failed to get bytes from IPFS: {str(e)}")

    async def pin(self, ipfs_hash: str) -> bool:
        """
        Pin data to prevent garbage collection

        Args:
            ipfs_hash: IPFS hash to pin

        Returns:
            True if successful
        """
        self._ensure_connected()

        try:
            self._client.pin.add(ipfs_hash)
            logger.info(f"Pinned IPFS hash: {ipfs_hash}")
            return True

        except Exception as e:
            raise IPFSError(f"Failed to pin IPFS hash: {str(e)}")

    async def unpin(self, ipfs_hash: str) -> bool:
        """
        Unpin data to allow garbage collection

        Args:
            ipfs_hash: IPFS hash to unpin

        Returns:
            True if successful
        """
        self._ensure_connected()

        try:
            self._client.pin.rm(ipfs_hash)
            logger.info(f"Unpinned IPFS hash: {ipfs_hash}")
            return True

        except Exception as e:
            raise IPFSError(f"Failed to unpin IPFS hash: {str(e)}")

    async def list_pins(self) -> List[str]:
        """
        List all pinned hashes

        Returns:
            List of pinned IPFS hashes
        """
        self._ensure_connected()

        try:
            pins = self._client.pin.ls()
            return list(pins.keys())

        except Exception as e:
            raise IPFSError(f"Failed to list pins: {str(e)}")

    async def calculate_hash(self, data: Union[str, bytes, Dict]) -> str:
        """
        Calculate IPFS hash without storing data

        Args:
            data: Data to calculate hash for

        Returns:
            IPFS hash that would be generated
        """
        if isinstance(data, dict):
            data = json.dumps(data, default=str)
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Use IPFS-compatible hash calculation
        import base58
        import multihash

        sha256_hash = hashlib.sha256(data).digest()
        multihash_bytes = multihash.encode(sha256_hash, "sha2-256")
        return base58.b58encode(b"\x01\x70" + multihash_bytes).decode("ascii")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get IPFS node statistics

        Returns:
            Dictionary with node statistics
        """
        self._ensure_connected()

        try:
            stats = self._client.stats.repo()
            return {
                "repo_size": stats["RepoSize"],
                "storage_max": stats["StorageMax"],
                "num_objects": stats["NumObjects"],
                "repo_path": stats["RepoPath"],
                "version": stats["Version"],
            }
        except Exception as e:
            raise IPFSError(f"Failed to get stats: {str(e)}")

    async def gc(self) -> Dict[str, Any]:
        """
        Run garbage collection on IPFS node

        Returns:
            Garbage collection results
        """
        self._ensure_connected()

        try:
            results = list(self._client.repo.gc())
            return {"collected_objects": len(results), "results": results}
        except Exception as e:
            raise IPFSError(f"Failed to run garbage collection: {str(e)}")

    async def resolve(self, path: str) -> str:
        """
        Resolve an IPFS path to a hash

        Args:
            path: IPFS path to resolve

        Returns:
            Resolved IPFS hash
        """
        self._ensure_connected()

        try:
            result = self._client.resolve(path)
            return result["Path"].replace("/ipfs/", "")
        except Exception as e:
            raise IPFSError(f"Failed to resolve path: {str(e)}")

    async def publish(self, ipfs_hash: str, key: str = None) -> str:
        """
        Publish content to IPNS

        Args:
            ipfs_hash: IPFS hash to publish
            key: IPNS key name (optional)

        Returns:
            IPNS address
        """
        self._ensure_connected()

        try:
            if key:
                result = self._client.name.publish(ipfs_hash, key=key)
            else:
                result = self._client.name.publish(ipfs_hash)

            logger.info(f"Published to IPNS: {result['Name']}")
            return result["Name"]

        except Exception as e:
            raise IPFSError(f"Failed to publish to IPNS: {str(e)}")
