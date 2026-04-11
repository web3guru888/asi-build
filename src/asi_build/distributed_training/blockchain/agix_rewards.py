"""
AGIX Token Rewards System for Compute Contribution
Integrates with SingularityNET's AGIX token for incentivizing decentralized training
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from eth_account import Account
from web3 import Web3


@dataclass
class ComputeContribution:
    """Represents compute contribution by a node"""

    node_id: str
    round_id: str
    data_processed: int  # Number of samples
    compute_time: float  # Seconds
    gpu_hours: float
    model_accuracy: float
    bandwidth_used: int  # Bytes
    timestamp: float


@dataclass
class RewardCalculation:
    """Reward calculation details"""

    node_id: str
    base_reward: Decimal
    quality_bonus: Decimal
    consistency_bonus: Decimal
    early_submission_bonus: Decimal
    total_reward: Decimal
    agix_amount: Decimal


class AGIXRewardCalculator:
    """Calculate AGIX rewards based on various contribution factors"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Reward parameters
        self.base_reward_per_sample = Decimal(str(config.get("base_reward_per_sample", "0.001")))
        self.quality_multiplier = Decimal(str(config.get("quality_multiplier", "2.0")))
        self.consistency_multiplier = Decimal(str(config.get("consistency_multiplier", "1.5")))
        self.early_submission_multiplier = Decimal(
            str(config.get("early_submission_multiplier", "1.2"))
        )

        # Quality thresholds
        self.high_accuracy_threshold = config.get("high_accuracy_threshold", 0.85)
        self.consistency_threshold = config.get("consistency_threshold", 0.9)

        # Pool settings
        self.round_reward_pool = Decimal(
            str(config.get("round_reward_pool", "10000"))
        )  # 10k AGIX per round
        self.min_reward_per_node = Decimal(str(config.get("min_reward_per_node", "1")))

        self.logger = logging.getLogger(__name__)

    def calculate_reward(
        self,
        contribution: ComputeContribution,
        node_history: List[ComputeContribution],
        round_deadline: float,
    ) -> RewardCalculation:
        """Calculate AGIX reward for a node's contribution"""

        # Base reward based on data processed
        base_reward = self.base_reward_per_sample * Decimal(str(contribution.data_processed))

        # Quality bonus based on model accuracy
        quality_bonus = Decimal("0")
        if contribution.model_accuracy >= self.high_accuracy_threshold:
            quality_bonus = base_reward * (self.quality_multiplier - Decimal("1"))

        # Consistency bonus for reliable nodes
        consistency_bonus = self._calculate_consistency_bonus(base_reward, node_history)

        # Early submission bonus
        early_submission_bonus = Decimal("0")
        if contribution.timestamp < round_deadline * 0.8:  # Submitted in first 80% of round
            early_submission_bonus = base_reward * (self.early_submission_multiplier - Decimal("1"))

        # Total reward
        total_reward = base_reward + quality_bonus + consistency_bonus + early_submission_bonus

        # Ensure minimum reward
        total_reward = max(total_reward, self.min_reward_per_node)

        return RewardCalculation(
            node_id=contribution.node_id,
            base_reward=base_reward,
            quality_bonus=quality_bonus,
            consistency_bonus=consistency_bonus,
            early_submission_bonus=early_submission_bonus,
            total_reward=total_reward,
            agix_amount=total_reward,  # 1:1 mapping for now
        )

    def _calculate_consistency_bonus(
        self, base_reward: Decimal, history: List[ComputeContribution]
    ) -> Decimal:
        """Calculate consistency bonus based on node's historical performance"""
        if len(history) < 3:
            return Decimal("0")

        # Calculate participation rate in last 10 rounds
        recent_history = history[-10:]
        participation_rate = len(recent_history) / 10.0

        # Calculate average accuracy
        avg_accuracy = np.mean([c.model_accuracy for c in recent_history])

        # Bonus for consistent high-quality participation
        if (
            participation_rate >= self.consistency_threshold
            and avg_accuracy >= self.high_accuracy_threshold
        ):
            return base_reward * (self.consistency_multiplier - Decimal("1"))

        return Decimal("0")

    def distribute_round_rewards(
        self,
        contributions: List[ComputeContribution],
        node_histories: Dict[str, List[ComputeContribution]],
        round_deadline: float,
    ) -> List[RewardCalculation]:
        """Distribute rewards for an entire round"""

        # Calculate individual rewards
        reward_calculations = []
        total_calculated_rewards = Decimal("0")

        for contribution in contributions:
            history = node_histories.get(contribution.node_id, [])
            calc = self.calculate_reward(contribution, history, round_deadline)
            reward_calculations.append(calc)
            total_calculated_rewards += calc.total_reward

        # Scale rewards to fit within round pool if necessary
        if total_calculated_rewards > self.round_reward_pool:
            scale_factor = self.round_reward_pool / total_calculated_rewards
            for calc in reward_calculations:
                calc.agix_amount = calc.total_reward * scale_factor

        return reward_calculations


class AGIXTokenManager:
    """Manages AGIX token operations for rewards"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Web3 setup
        self.w3 = Web3(Web3.HTTPProvider(config["ethereum_rpc_url"]))
        self.account = Account.from_key(config["treasury_private_key"])

        # AGIX token contract
        self.agix_contract = self.w3.eth.contract(
            address=config["agix_token_address"], abi=config["agix_token_abi"]
        )

        # Reward distribution contract
        self.reward_contract = self.w3.eth.contract(
            address=config["reward_contract_address"], abi=config["reward_contract_abi"]
        )

        self.logger = logging.getLogger(__name__)

    async def distribute_rewards(self, reward_calculations: List[RewardCalculation]) -> List[str]:
        """Distribute AGIX rewards to nodes"""
        transaction_hashes = []

        for calc in reward_calculations:
            try:
                # Convert node_id to address (assuming it's already an address)
                recipient_address = calc.node_id

                # Convert AGIX amount to wei (AGIX has 8 decimals)
                agix_wei = int(calc.agix_amount * (10**8))

                # Execute reward distribution
                tx_hash = await self._send_agix_reward(recipient_address, agix_wei)

                if tx_hash:
                    transaction_hashes.append(tx_hash)
                    self.logger.info(f"Distributed {calc.agix_amount} AGIX to {recipient_address}")

            except Exception as e:
                self.logger.error(f"Failed to distribute reward to {calc.node_id}: {e}")

        return transaction_hashes

    async def _send_agix_reward(self, recipient: str, amount_wei: int) -> Optional[str]:
        """Send AGIX reward to a recipient"""
        try:
            # Build transaction
            transaction = self.agix_contract.functions.transfer(
                recipient, amount_wei
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": 100000,
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
                return tx_hash.hex()
            else:
                self.logger.error(f"Transaction failed: {tx_hash.hex()}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to send AGIX reward: {e}")
            return None

    def get_treasury_balance(self) -> Decimal:
        """Get current AGIX balance of treasury"""
        balance_wei = self.agix_contract.functions.balanceOf(self.account.address).call()
        balance_agix = Decimal(balance_wei) / (10**8)
        return balance_agix

    def get_node_balance(self, node_address: str) -> Decimal:
        """Get AGIX balance of a node"""
        balance_wei = self.agix_contract.functions.balanceOf(node_address).call()
        balance_agix = Decimal(balance_wei) / (10**8)
        return balance_agix


class ReputationBasedRewards:
    """Enhanced reward system incorporating reputation scores"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.reputation_weight = config.get("reputation_weight", 0.3)
        self.contribution_weight = config.get("contribution_weight", 0.7)

        self.logger = logging.getLogger(__name__)

    def calculate_reputation_adjusted_reward(
        self, base_reward: Decimal, reputation_score: float, node_stake: Decimal
    ) -> Decimal:
        """Calculate reward adjusted for reputation and stake"""

        # Normalize reputation score (0-1 range)
        normalized_reputation = max(0, min(1, reputation_score))

        # Stake influence (log scale to prevent extreme concentration)
        stake_multiplier = 1 + np.log10(
            max(1, float(node_stake) / 1000)
        )  # Log base relative to 1k AGIX
        stake_multiplier = min(stake_multiplier, 3.0)  # Cap at 3x

        # Combined multiplier
        reputation_multiplier = 0.5 + (normalized_reputation * 1.5)  # 0.5x to 2x range

        adjusted_reward = (
            base_reward * Decimal(str(reputation_multiplier)) * Decimal(str(stake_multiplier))
        )

        return adjusted_reward


class AntiSybilMechanism:
    """Prevents Sybil attacks in reward distribution"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_stake_for_rewards = Decimal(str(config.get("min_stake_for_rewards", "100")))
        self.max_reward_per_identity = Decimal(str(config.get("max_reward_per_identity", "1000")))

        # Identity clustering detection
        self.ip_clustering_threshold = config.get("ip_clustering_threshold", 10)
        self.timing_correlation_threshold = config.get("timing_correlation_threshold", 0.8)

        self.logger = logging.getLogger(__name__)

    def detect_sybil_nodes(
        self, contributions: List[ComputeContribution], node_metadata: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Detect potential Sybil nodes based on behavioral patterns"""
        suspicious_nodes = []

        # Group by IP address
        ip_groups = {}
        for contrib in contributions:
            node_meta = node_metadata.get(contrib.node_id, {})
            ip_addr = node_meta.get("ip_address", "unknown")

            if ip_addr not in ip_groups:
                ip_groups[ip_addr] = []
            ip_groups[ip_addr].append(contrib.node_id)

        # Flag nodes with too many from same IP
        for ip_addr, nodes in ip_groups.items():
            if len(nodes) > self.ip_clustering_threshold:
                suspicious_nodes.extend(nodes)
                self.logger.warning(
                    f"Suspicious IP clustering detected: {ip_addr} ({len(nodes)} nodes)"
                )

        # Timing correlation detection
        submission_times = {c.node_id: c.timestamp for c in contributions}
        for i, node_a in enumerate(contributions):
            for node_b in contributions[i + 1 :]:
                time_diff = abs(submission_times[node_a.node_id] - submission_times[node_b.node_id])

                # If submissions are suspiciously synchronized
                if time_diff < 5.0:  # Within 5 seconds
                    if node_a.node_id not in suspicious_nodes:
                        suspicious_nodes.append(node_a.node_id)
                    if node_b.node_id not in suspicious_nodes:
                        suspicious_nodes.append(node_b.node_id)

        return list(set(suspicious_nodes))

    def filter_rewards_for_sybils(
        self, reward_calculations: List[RewardCalculation], suspicious_nodes: List[str]
    ) -> List[RewardCalculation]:
        """Reduce or eliminate rewards for suspicious nodes"""
        filtered_rewards = []

        for calc in reward_calculations:
            if calc.node_id in suspicious_nodes:
                # Reduce reward by 90% for suspicious nodes
                calc.agix_amount = calc.agix_amount * Decimal("0.1")
                self.logger.warning(f"Reduced reward for suspicious node {calc.node_id}")

            filtered_rewards.append(calc)

        return filtered_rewards


class RewardDistributionManager:
    """Main manager for AGIX reward distribution"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        self.calculator = AGIXRewardCalculator(config.get("reward_calculator", {}))
        self.token_manager = AGIXTokenManager(config.get("token_manager", {}))
        self.reputation_rewards = ReputationBasedRewards(config.get("reputation_rewards", {}))
        self.anti_sybil = AntiSybilMechanism(config.get("anti_sybil", {}))

        # Contribution history
        self.contribution_history: Dict[str, List[ComputeContribution]] = {}
        self.node_metadata: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(__name__)

    async def process_round_rewards(
        self,
        contributions: List[ComputeContribution],
        round_deadline: float,
        node_reputations: Dict[str, float],
        node_stakes: Dict[str, Decimal],
    ) -> Dict[str, Any]:
        """Process rewards for a completed training round"""

        self.logger.info(f"Processing rewards for {len(contributions)} contributions")

        # Update contribution history
        for contrib in contributions:
            if contrib.node_id not in self.contribution_history:
                self.contribution_history[contrib.node_id] = []
            self.contribution_history[contrib.node_id].append(contrib)

            # Keep only last 50 contributions per node
            self.contribution_history[contrib.node_id] = self.contribution_history[contrib.node_id][
                -50:
            ]

        # Calculate base rewards
        reward_calculations = self.calculator.distribute_round_rewards(
            contributions, self.contribution_history, round_deadline
        )

        # Apply reputation and stake adjustments
        for calc in reward_calculations:
            reputation = node_reputations.get(calc.node_id, 0.5)
            stake = node_stakes.get(calc.node_id, Decimal("0"))

            adjusted_reward = self.reputation_rewards.calculate_reputation_adjusted_reward(
                calc.agix_amount, reputation, stake
            )
            calc.agix_amount = adjusted_reward

        # Anti-Sybil filtering
        suspicious_nodes = self.anti_sybil.detect_sybil_nodes(contributions, self.node_metadata)
        reward_calculations = self.anti_sybil.filter_rewards_for_sybils(
            reward_calculations, suspicious_nodes
        )

        # Distribute rewards
        transaction_hashes = await self.token_manager.distribute_rewards(reward_calculations)

        # Calculate statistics
        total_distributed = sum(calc.agix_amount for calc in reward_calculations)
        successful_distributions = len(transaction_hashes)

        result = {
            "total_contributions": len(contributions),
            "total_agix_distributed": float(total_distributed),
            "successful_distributions": successful_distributions,
            "failed_distributions": len(reward_calculations) - successful_distributions,
            "suspicious_nodes_detected": len(suspicious_nodes),
            "transaction_hashes": transaction_hashes,
            "reward_breakdown": [asdict(calc) for calc in reward_calculations],
        }

        self.logger.info(
            f"Distributed {total_distributed} AGIX across {successful_distributions} nodes"
        )

        return result

    def update_node_metadata(self, node_id: str, metadata: Dict[str, Any]):
        """Update metadata for a node (IP, hardware specs, etc.)"""
        self.node_metadata[node_id] = metadata

    def get_node_contribution_stats(self, node_id: str) -> Dict[str, Any]:
        """Get contribution statistics for a node"""
        history = self.contribution_history.get(node_id, [])

        if not history:
            return {"total_contributions": 0}

        total_data = sum(c.data_processed for c in history)
        total_compute = sum(c.compute_time for c in history)
        avg_accuracy = np.mean([c.model_accuracy for c in history])

        return {
            "total_contributions": len(history),
            "total_data_processed": total_data,
            "total_compute_time": total_compute,
            "average_accuracy": avg_accuracy,
            "last_contribution": max(c.timestamp for c in history),
        }

    def get_treasury_status(self) -> Dict[str, Any]:
        """Get treasury and reward system status"""
        treasury_balance = self.token_manager.get_treasury_balance()

        return {
            "treasury_balance_agix": float(treasury_balance),
            "total_nodes_with_history": len(self.contribution_history),
            "round_reward_pool": float(self.calculator.round_reward_pool),
            "suspicious_nodes_count": len(
                self.anti_sybil.detect_sybil_nodes([], self.node_metadata)
            ),
        }
