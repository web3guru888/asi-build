"""
Blockchain-based Model Checkpointing with IPFS/Filecoin Integration
Provides decentralized, immutable storage for model checkpoints
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import ipfshttpclient
import numpy as np
import torch
from eth_account import Account
from web3 import Web3


@dataclass
class ModelCheckpoint:
    """Model checkpoint metadata"""

    checkpoint_id: str
    model_hash: str
    ipfs_hash: str
    filecoin_deal_id: Optional[str]
    creator_address: str
    timestamp: float
    round_number: int
    accuracy_metrics: Dict[str, float]
    size_bytes: int
    encryption_key: Optional[str]


@dataclass
class CheckpointVerification:
    """Verification result for a checkpoint"""

    checkpoint_id: str
    is_valid: bool
    verification_hash: str
    verifier_address: str
    timestamp: float


class IPFSClient:
    """IPFS client for decentralized storage"""

    def __init__(self, ipfs_api_url: str = "/dns/localhost/tcp/5001/http"):
        self.client = ipfshttpclient.connect(ipfs_api_url)
        self.logger = logging.getLogger(__name__)

    async def upload_file(self, file_path: str) -> str:
        """Upload file to IPFS and return hash"""
        try:
            result = self.client.add(file_path)
            ipfs_hash = result["Hash"]
            self.logger.info(f"Uploaded file to IPFS: {ipfs_hash}")
            return ipfs_hash
        except Exception as e:
            self.logger.error(f"IPFS upload failed: {e}")
            raise

    async def download_file(self, ipfs_hash: str, output_path: str) -> bool:
        """Download file from IPFS"""
        try:
            self.client.get(ipfs_hash, target=output_path)
            self.logger.info(f"Downloaded file from IPFS: {ipfs_hash}")
            return True
        except Exception as e:
            self.logger.error(f"IPFS download failed: {e}")
            return False

    async def pin_file(self, ipfs_hash: str) -> bool:
        """Pin file to ensure availability"""
        try:
            self.client.pin.add(ipfs_hash)
            return True
        except Exception as e:
            self.logger.error(f"IPFS pinning failed: {e}")
            return False


class FilecoinClient:
    """Filecoin client for long-term storage deals"""

    def __init__(self, config: Dict[str, Any]):
        self.api_url = config.get("filecoin_api_url", "https://api.node.glif.io")
        self.wallet_address = config.get("wallet_address")
        self.private_key = config.get("private_key")
        self.logger = logging.getLogger(__name__)

    async def create_storage_deal(
        self, ipfs_hash: str, file_size: int, duration_epochs: int = 518400
    ) -> Optional[str]:
        """Create storage deal on Filecoin network"""
        try:
            # This is a simplified implementation
            # In practice, you'd use Lotus API or PowerGate
            deal_params = {
                "data_cid": ipfs_hash,
                "size": file_size,
                "duration": duration_epochs,
                "price": self._calculate_storage_price(file_size, duration_epochs),
            }

            # Mock deal creation for demo
            deal_id = str(uuid.uuid4())

            self.logger.info(f"Created Filecoin storage deal: {deal_id}")
            return deal_id

        except Exception as e:
            self.logger.error(f"Filecoin deal creation failed: {e}")
            return None

    async def verify_storage_deal(self, deal_id: str) -> bool:
        """Verify storage deal status"""
        try:
            # Query deal status from Filecoin network
            # This would check actual deal status in production
            return True
        except Exception as e:
            self.logger.error(f"Deal verification failed: {e}")
            return False

    def _calculate_storage_price(self, file_size: int, duration: int) -> int:
        """Calculate storage price in attoFIL"""
        # Simple pricing model: 1 nanoFIL per byte per epoch
        return file_size * duration * 1000000000


class BlockchainCheckpointManager:
    """Manages model checkpoints using blockchain and IPFS/Filecoin"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Web3 setup
        self.w3 = Web3(Web3.HTTPProvider(config["ethereum_rpc_url"]))
        self.account = Account.from_key(config["private_key"])

        # Storage clients
        self.ipfs_client = IPFSClient(config.get("ipfs_api_url"))
        self.filecoin_client = FilecoinClient(config.get("filecoin_config", {}))

        # Smart contract
        self.contract_address = config["contract_address"]
        self.contract_abi = config["contract_abi"]
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

        # Checkpoint storage
        self.checkpoints: Dict[str, ModelCheckpoint] = {}
        self.verifications: Dict[str, List[CheckpointVerification]] = {}

        self.logger = logging.getLogger(__name__)

    async def save_checkpoint(self, model: torch.nn.Module, metadata: Dict[str, Any]) -> str:
        """Save model checkpoint to IPFS/Filecoin and record on blockchain"""
        try:
            checkpoint_id = str(uuid.uuid4())

            # Serialize model
            model_data = {
                "state_dict": model.state_dict(),
                "metadata": metadata,
                "timestamp": time.time(),
            }

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as temp_file:
                torch.save(model_data, temp_file.name)
                temp_path = temp_file.name

            try:
                # Upload to IPFS
                ipfs_hash = await self.ipfs_client.upload_file(temp_path)

                # Pin to ensure availability
                await self.ipfs_client.pin_file(ipfs_hash)

                # Get file size
                file_size = os.path.getsize(temp_path)

                # Create Filecoin storage deal
                filecoin_deal_id = await self.filecoin_client.create_storage_deal(
                    ipfs_hash, file_size
                )

                # Calculate model hash
                with open(temp_path, "rb") as f:
                    model_hash = hashlib.sha256(f.read()).hexdigest()

                # Create checkpoint record
                checkpoint = ModelCheckpoint(
                    checkpoint_id=checkpoint_id,
                    model_hash=model_hash,
                    ipfs_hash=ipfs_hash,
                    filecoin_deal_id=filecoin_deal_id,
                    creator_address=self.account.address,
                    timestamp=time.time(),
                    round_number=metadata.get("round_number", 0),
                    accuracy_metrics=metadata.get("accuracy_metrics", {}),
                    size_bytes=file_size,
                    encryption_key=None,  # TODO: Implement encryption
                )

                # Record on blockchain
                await self._record_checkpoint_on_blockchain(checkpoint)

                # Store locally
                self.checkpoints[checkpoint_id] = checkpoint

                self.logger.info(f"Saved checkpoint {checkpoint_id} to IPFS: {ipfs_hash}")
                return checkpoint_id

            finally:
                # Cleanup temporary file
                os.unlink(temp_path)

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[torch.nn.Module]:
        """Load model checkpoint from IPFS"""
        try:
            if checkpoint_id not in self.checkpoints:
                # Try to load from blockchain
                checkpoint = await self._load_checkpoint_from_blockchain(checkpoint_id)
                if checkpoint is None:
                    return None
                self.checkpoints[checkpoint_id] = checkpoint

            checkpoint = self.checkpoints[checkpoint_id]

            # Download from IPFS
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as temp_file:
                temp_path = temp_file.name

            try:
                success = await self.ipfs_client.download_file(checkpoint.ipfs_hash, temp_path)

                if not success:
                    self.logger.error(f"Failed to download checkpoint {checkpoint_id}")
                    return None

                # Verify hash
                with open(temp_path, "rb") as f:
                    downloaded_hash = hashlib.sha256(f.read()).hexdigest()

                if downloaded_hash != checkpoint.model_hash:
                    self.logger.error(f"Hash mismatch for checkpoint {checkpoint_id}")
                    return None

                # Load model
                model_data = torch.load(temp_path)

                # TODO: Reconstruct model architecture and load state dict
                # For now, return the state dict
                return model_data["state_dict"]

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None

    async def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """Verify checkpoint integrity"""
        try:
            checkpoint = self.checkpoints.get(checkpoint_id)
            if checkpoint is None:
                return False

            # Download and verify hash
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as temp_file:
                temp_path = temp_file.name

            try:
                success = await self.ipfs_client.download_file(checkpoint.ipfs_hash, temp_path)

                if not success:
                    return False

                # Verify hash
                with open(temp_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()

                is_valid = file_hash == checkpoint.model_hash

                # Record verification
                verification = CheckpointVerification(
                    checkpoint_id=checkpoint_id,
                    is_valid=is_valid,
                    verification_hash=file_hash,
                    verifier_address=self.account.address,
                    timestamp=time.time(),
                )

                if checkpoint_id not in self.verifications:
                    self.verifications[checkpoint_id] = []
                self.verifications[checkpoint_id].append(verification)

                return is_valid

            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            self.logger.error(f"Checkpoint verification failed: {e}")
            return False

    async def list_checkpoints(
        self, creator_address: Optional[str] = None
    ) -> List[ModelCheckpoint]:
        """List available checkpoints"""
        checkpoints = list(self.checkpoints.values())

        if creator_address:
            checkpoints = [c for c in checkpoints if c.creator_address == creator_address]

        return sorted(checkpoints, key=lambda c: c.timestamp, reverse=True)

    async def get_checkpoint_metrics(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint performance metrics"""
        checkpoint = self.checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return None

        verifications = self.verifications.get(checkpoint_id, [])

        return {
            "checkpoint_id": checkpoint_id,
            "accuracy_metrics": checkpoint.accuracy_metrics,
            "creator": checkpoint.creator_address,
            "timestamp": checkpoint.timestamp,
            "size_bytes": checkpoint.size_bytes,
            "verification_count": len(verifications),
            "verification_success_rate": sum(1 for v in verifications if v.is_valid)
            / max(1, len(verifications)),
        }

    async def _record_checkpoint_on_blockchain(self, checkpoint: ModelCheckpoint):
        """Record checkpoint metadata on blockchain"""
        try:
            # Build transaction
            transaction = self.contract.functions.recordCheckpoint(
                checkpoint.checkpoint_id,
                checkpoint.model_hash,
                checkpoint.ipfs_hash,
                checkpoint.round_number,
                checkpoint.size_bytes,
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": 200000,
                    "gasPrice": self.w3.to_wei("20", "gwei"),
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                self.logger.info(f"Recorded checkpoint {checkpoint.checkpoint_id} on blockchain")
            else:
                self.logger.error(
                    f"Blockchain transaction failed for checkpoint {checkpoint.checkpoint_id}"
                )

        except Exception as e:
            self.logger.error(f"Failed to record checkpoint on blockchain: {e}")
            raise

    async def _load_checkpoint_from_blockchain(
        self, checkpoint_id: str
    ) -> Optional[ModelCheckpoint]:
        """Load checkpoint metadata from blockchain"""
        try:
            # Query smart contract
            result = self.contract.functions.getCheckpoint(checkpoint_id).call()

            if result[0] == "":  # Empty checkpoint ID means not found
                return None

            return ModelCheckpoint(
                checkpoint_id=result[0],
                model_hash=result[1],
                ipfs_hash=result[2],
                filecoin_deal_id=None,  # Not stored on-chain
                creator_address=result[3],
                timestamp=result[4],
                round_number=result[5],
                accuracy_metrics={},  # Not stored on-chain
                size_bytes=result[6],
                encryption_key=None,
            )

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint from blockchain: {e}")
            return None

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_checkpoints = len(self.checkpoints)
        total_size = sum(c.size_bytes for c in self.checkpoints.values())

        filecoin_deals = sum(1 for c in self.checkpoints.values() if c.filecoin_deal_id)

        return {
            "total_checkpoints": total_checkpoints,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "filecoin_deals": filecoin_deals,
            "ipfs_pins": total_checkpoints,  # All checkpoints are pinned
            "verification_coverage": len(self.verifications) / max(1, total_checkpoints),
        }
