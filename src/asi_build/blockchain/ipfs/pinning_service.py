"""
IPFS Pinning Services for Kenny AGI Blockchain Audit Trail

Provides integration with various IPFS pinning services to ensure
data persistence and availability across the network.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class PinStatus:
    """Represents the status of a pinned item"""

    hash: str
    name: Optional[str]
    status: str  # 'pinned', 'pinning', 'failed'
    created: datetime
    size: Optional[int] = None
    service: Optional[str] = None


class PinningService(ABC):
    """Abstract base class for IPFS pinning services"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def pin(
        self, ipfs_hash: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> PinStatus:
        """Pin content to the service"""
        pass

    @abstractmethod
    async def unpin(self, ipfs_hash: str) -> bool:
        """Unpin content from the service"""
        pass

    @abstractmethod
    async def list_pins(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[PinStatus]:
        """List pinned content"""
        pass

    @abstractmethod
    async def get_pin_status(self, ipfs_hash: str) -> Optional[PinStatus]:
        """Get status of a specific pin"""
        pass


class PinataService(PinningService):
    """
    Pinata IPFS pinning service integration

    Provides enterprise-grade IPFS pinning with additional features
    like file management and analytics.
    """

    def __init__(self, api_key: str, secret_key: str):
        super().__init__("Pinata")
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api.pinata.cloud"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "pinata_api_key": self.api_key,
                "pinata_secret_api_key": self.secret_key,
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _ensure_session(self):
        if not self.session:
            raise RuntimeError("PinataService must be used as async context manager")

    async def pin(
        self, ipfs_hash: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> PinStatus:
        """Pin content by IPFS hash"""
        self._ensure_session()

        url = f"{self.base_url}/pinning/pinByHash"

        data = {"hashToPin": ipfs_hash, "pinataOptions": {"cidVersion": 1}}

        if name:
            data["pinataMetadata"] = {"name": name}
            if metadata:
                data["pinataMetadata"].update(metadata)
        elif metadata:
            data["pinataMetadata"] = metadata

        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return PinStatus(
                        hash=result["ipfsHash"],
                        name=name,
                        status="pinned",
                        created=datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00")),
                        size=result.get("size"),
                        service=self.name,
                    )
                else:
                    error_text = await response.text()
                    raise Exception(f"Pinata API error: {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"Failed to pin {ipfs_hash} to Pinata: {str(e)}")
            return PinStatus(
                hash=ipfs_hash,
                name=name,
                status="failed",
                created=datetime.now(),
                service=self.name,
            )

    async def unpin(self, ipfs_hash: str) -> bool:
        """Unpin content from Pinata"""
        self._ensure_session()

        url = f"{self.base_url}/pinning/unpin/{ipfs_hash}"

        try:
            async with self.session.delete(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to unpin {ipfs_hash} from Pinata: {str(e)}")
            return False

    async def list_pins(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[PinStatus]:
        """List pins from Pinata"""
        self._ensure_session()

        url = f"{self.base_url}/data/pinList"
        params = {"pageLimit": min(limit, 1000), "pageOffset": offset}  # Pinata max is 1000

        if status:
            params["status"] = status

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()

                    pins = []
                    for row in result["rows"]:
                        pins.append(
                            PinStatus(
                                hash=row["ipfs_pin_hash"],
                                name=row["metadata"].get("name") if row.get("metadata") else None,
                                status=row["status"],
                                created=datetime.fromisoformat(
                                    row["date_pinned"].replace("Z", "+00:00")
                                ),
                                size=row.get("size"),
                                service=self.name,
                            )
                        )

                    return pins
                else:
                    logger.error(f"Failed to list pins from Pinata: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Failed to list pins from Pinata: {str(e)}")
            return []

    async def get_pin_status(self, ipfs_hash: str) -> Optional[PinStatus]:
        """Get status of specific pin from Pinata"""
        pins = await self.list_pins()
        for pin in pins:
            if pin.hash == ipfs_hash:
                return pin
        return None

    async def test_authentication(self) -> bool:
        """Test API authentication"""
        self._ensure_session()

        url = f"{self.base_url}/data/testAuthentication"

        try:
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception:
            return False


class InfuraService(PinningService):
    """
    Infura IPFS pinning service integration

    Provides reliable IPFS infrastructure with global availability.
    """

    def __init__(self, project_id: str, project_secret: str):
        super().__init__("Infura")
        self.project_id = project_id
        self.project_secret = project_secret
        self.base_url = f"https://ipfs.infura.io:5001/api/v0"
        self.session = None

    async def __aenter__(self):
        import base64

        credentials = base64.b64encode(f"{self.project_id}:{self.project_secret}".encode()).decode()

        self.session = aiohttp.ClientSession(headers={"Authorization": f"Basic {credentials}"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _ensure_session(self):
        if not self.session:
            raise RuntimeError("InfuraService must be used as async context manager")

    async def pin(
        self, ipfs_hash: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> PinStatus:
        """Pin content using Infura IPFS API"""
        self._ensure_session()

        url = f"{self.base_url}/pin/add"
        params = {"arg": ipfs_hash}

        try:
            async with self.session.post(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    return PinStatus(
                        hash=result["Pins"][0],
                        name=name,
                        status="pinned",
                        created=datetime.now(),
                        service=self.name,
                    )
                else:
                    error_text = await response.text()
                    raise Exception(f"Infura API error: {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"Failed to pin {ipfs_hash} to Infura: {str(e)}")
            return PinStatus(
                hash=ipfs_hash,
                name=name,
                status="failed",
                created=datetime.now(),
                service=self.name,
            )

    async def unpin(self, ipfs_hash: str) -> bool:
        """Unpin content from Infura"""
        self._ensure_session()

        url = f"{self.base_url}/pin/rm"
        params = {"arg": ipfs_hash}

        try:
            async with self.session.post(url, params=params) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to unpin {ipfs_hash} from Infura: {str(e)}")
            return False

    async def list_pins(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[PinStatus]:
        """List pins from Infura"""
        self._ensure_session()

        url = f"{self.base_url}/pin/ls"

        try:
            async with self.session.post(url) as response:
                if response.status == 200:
                    result = await response.json()

                    pins = []
                    for hash_key, pin_info in result.get("Keys", {}).items():
                        pins.append(
                            PinStatus(
                                hash=hash_key,
                                name=None,
                                status="pinned",
                                created=datetime.now(),  # Infura doesn't provide creation time
                                service=self.name,
                            )
                        )

                    # Apply pagination
                    start_idx = offset
                    end_idx = offset + limit
                    return pins[start_idx:end_idx]
                else:
                    logger.error(f"Failed to list pins from Infura: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Failed to list pins from Infura: {str(e)}")
            return []

    async def get_pin_status(self, ipfs_hash: str) -> Optional[PinStatus]:
        """Get status of specific pin from Infura"""
        pins = await self.list_pins()
        for pin in pins:
            if pin.hash == ipfs_hash:
                return pin
        return None


class MultiPinningManager:
    """
    Manager for multiple pinning services

    Provides redundancy and automatic failover across multiple
    IPFS pinning services.
    """

    def __init__(self, services: List[PinningService]):
        """
        Initialize with list of pinning services

        Args:
            services: List of configured pinning services
        """
        self.services = services
        self.service_map = {service.name: service for service in services}

    async def pin_to_all(
        self, ipfs_hash: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, PinStatus]:
        """
        Pin content to all configured services

        Args:
            ipfs_hash: IPFS hash to pin
            name: Optional name for the pin
            metadata: Optional metadata

        Returns:
            Dictionary mapping service names to pin status
        """
        tasks = []
        for service in self.services:
            tasks.append(service.pin(ipfs_hash, name, metadata))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        status_map = {}
        for i, result in enumerate(results):
            service_name = self.services[i].name
            if isinstance(result, Exception):
                logger.error(f"Failed to pin to {service_name}: {str(result)}")
                status_map[service_name] = PinStatus(
                    hash=ipfs_hash,
                    name=name,
                    status="failed",
                    created=datetime.now(),
                    service=service_name,
                )
            else:
                status_map[service_name] = result

        return status_map

    async def unpin_from_all(self, ipfs_hash: str) -> Dict[str, bool]:
        """
        Unpin content from all services

        Args:
            ipfs_hash: IPFS hash to unpin

        Returns:
            Dictionary mapping service names to success status
        """
        tasks = [service.unpin(ipfs_hash) for service in self.services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        status_map = {}
        for i, result in enumerate(results):
            service_name = self.services[i].name
            if isinstance(result, Exception):
                logger.error(f"Failed to unpin from {service_name}: {str(result)}")
                status_map[service_name] = False
            else:
                status_map[service_name] = result

        return status_map

    async def get_pin_status_all(self, ipfs_hash: str) -> Dict[str, Optional[PinStatus]]:
        """Get pin status from all services"""
        tasks = [service.get_pin_status(ipfs_hash) for service in self.services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        status_map = {}
        for i, result in enumerate(results):
            service_name = self.services[i].name
            if isinstance(result, Exception):
                logger.error(f"Failed to get status from {service_name}: {str(result)}")
                status_map[service_name] = None
            else:
                status_map[service_name] = result

        return status_map

    async def pin_with_redundancy(
        self,
        ipfs_hash: str,
        min_replicas: int = 2,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[PinStatus]:
        """
        Pin content ensuring minimum number of successful replicas

        Args:
            ipfs_hash: IPFS hash to pin
            min_replicas: Minimum number of successful pins required
            name: Optional name for the pin
            metadata: Optional metadata

        Returns:
            List of successful pin statuses
        """
        all_results = await self.pin_to_all(ipfs_hash, name, metadata)

        successful_pins = [status for status in all_results.values() if status.status == "pinned"]

        if len(successful_pins) < min_replicas:
            logger.warning(
                f"Only {len(successful_pins)} successful pins out of {min_replicas} required"
            )

        return successful_pins

    def get_service(self, name: str) -> Optional[PinningService]:
        """Get service by name"""
        return self.service_map.get(name)

    def list_services(self) -> List[str]:
        """List all configured service names"""
        return list(self.service_map.keys())
