"""
Smart Contracts for AGI Governance Operations.

This module implements smart contract functionality for decentralized governance
of AGI systems, including automated execution of governance decisions,
token management, and enforcement of ethical constraints.
"""

import asyncio
import hashlib
import hmac
import inspect
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContractState(Enum):
    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    UPGRADEABLE = "upgradeable"


class ExecutionStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERTED = "reverted"


class PermissionLevel(Enum):
    PUBLIC = "public"
    STAKEHOLDER = "stakeholder"
    GOVERNANCE = "governance"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class ContractEvent:
    """Represents an event emitted by a smart contract."""

    contract_address: str
    event_name: str
    parameters: Dict[str, Any]
    block_height: int
    transaction_hash: str
    timestamp: datetime


@dataclass
class Transaction:
    """Represents a transaction on the governance blockchain."""

    id: str
    from_address: str
    to_address: str
    function_name: str
    parameters: Dict[str, Any]
    gas_limit: int
    gas_used: int
    status: ExecutionStatus
    result: Optional[Any]
    events: List[ContractEvent]
    created_at: datetime
    executed_at: Optional[datetime]
    block_height: Optional[int]


@dataclass
class ContractPermission:
    """Defines permissions for contract functions."""

    function_name: str
    required_level: PermissionLevel
    required_roles: List[str]
    custom_conditions: List[str]


class SmartContract(ABC):
    """Abstract base class for all smart contracts."""

    def __init__(self, address: str, deployer: str):
        self.address = address
        self.deployer = deployer
        self.state = ContractState.DEPLOYED
        self.storage: Dict[str, Any] = {}
        self.permissions: List[ContractPermission] = []
        self.events: List[ContractEvent] = []
        self.deployed_at = datetime.now(tz=timezone.utc)
        self.version = "1.0.0"

        # Set up default permissions
        self._setup_permissions()

    @abstractmethod
    def _setup_permissions(self):
        """Setup function permissions for the contract."""
        pass

    def execute_function(
        self,
        function_name: str,
        caller: str,
        parameters: Dict[str, Any],
        transaction_context: Dict[str, Any],
    ) -> Tuple[bool, Any, List[ContractEvent]]:
        """Execute a contract function."""
        try:
            # Check permissions
            if not self._check_permissions(function_name, caller, transaction_context):
                return False, "Permission denied", []

            # Check if function exists
            if not hasattr(self, function_name):
                return False, "Function not found", []

            # Get function and execute
            func = getattr(self, function_name)
            if not callable(func) or function_name.startswith("_"):
                return False, "Function not callable", []

            # Execute function
            events_before = len(self.events)
            result = func(**parameters)
            new_events = self.events[events_before:]

            return True, result, new_events

        except Exception as e:
            logger.error(f"Contract execution error: {e}")
            return False, str(e), []

    def _check_permissions(self, function_name: str, caller: str, context: Dict[str, Any]) -> bool:
        """Check if caller has permission to execute function."""
        permission = next((p for p in self.permissions if p.function_name == function_name), None)
        if not permission:
            return True  # No specific permission required

        caller_level = context.get("permission_level", PermissionLevel.PUBLIC)
        caller_roles = context.get("roles", [])

        # Check permission level
        level_hierarchy = {
            PermissionLevel.PUBLIC: 0,
            PermissionLevel.STAKEHOLDER: 1,
            PermissionLevel.GOVERNANCE: 2,
            PermissionLevel.ADMIN: 3,
            PermissionLevel.SYSTEM: 4,
        }

        if level_hierarchy[caller_level] < level_hierarchy[permission.required_level]:
            return False

        # Check required roles
        if permission.required_roles:
            if not any(role in caller_roles for role in permission.required_roles):
                return False

        # Check custom conditions
        for condition in permission.custom_conditions:
            if not self._evaluate_condition(condition, caller, context):
                return False

        return True

    def _evaluate_condition(self, condition: str, caller: str, context: Dict[str, Any]) -> bool:
        """Evaluate a custom permission condition."""
        # Simplified condition evaluation
        if condition == "is_deployer":
            return caller == self.deployer
        elif condition == "contract_active":
            return self.state == ContractState.ACTIVE
        elif condition == "emergency_mode":
            return context.get("emergency_mode", False)
        return True

    def _emit_event(
        self, event_name: str, parameters: Dict[str, Any], transaction_context: Dict[str, Any]
    ):
        """Emit an event from the contract."""
        event = ContractEvent(
            contract_address=self.address,
            event_name=event_name,
            parameters=parameters,
            block_height=transaction_context.get("block_height", 0),
            transaction_hash=transaction_context.get("transaction_hash", ""),
            timestamp=datetime.now(tz=timezone.utc),
        )
        self.events.append(event)

    def get_storage_value(self, key: str) -> Any:
        """Get value from contract storage."""
        return self.storage.get(key)

    def set_storage_value(self, key: str, value: Any):
        """Set value in contract storage."""
        self.storage[key] = value

    def pause_contract(self, caller: str):
        """Pause contract execution."""
        if caller != self.deployer:
            raise PermissionError("Only deployer can pause contract")
        self.state = ContractState.PAUSED

    def resume_contract(self, caller: str):
        """Resume contract execution."""
        if caller != self.deployer:
            raise PermissionError("Only deployer can resume contract")
        self.state = ContractState.ACTIVE


class GovernanceTokenContract(SmartContract):
    """Smart contract for governance token management."""

    def __init__(self, address: str, deployer: str, initial_supply: int):
        super().__init__(address, deployer)
        self.storage["total_supply"] = initial_supply
        self.storage["balances"] = {deployer: initial_supply}
        self.storage["allowances"] = {}
        self.storage["locked_tokens"] = {}
        self.state = ContractState.ACTIVE

    def _setup_permissions(self):
        """Setup permissions for token contract functions."""
        self.permissions = [
            ContractPermission("mint", PermissionLevel.GOVERNANCE, ["token_minter"], []),
            ContractPermission("burn", PermissionLevel.GOVERNANCE, ["token_burner"], []),
            ContractPermission("pause_contract", PermissionLevel.ADMIN, [], ["is_deployer"]),
            ContractPermission("resume_contract", PermissionLevel.ADMIN, [], ["is_deployer"]),
        ]

    def balance_of(self, account: str) -> int:
        """Get token balance of an account."""
        return self.storage["balances"].get(account, 0)

    def total_supply(self) -> int:
        """Get total token supply."""
        return self.storage["total_supply"]

    def transfer(self, to: str, amount: int, transaction_context: Dict[str, Any]) -> bool:
        """Transfer tokens between accounts."""
        caller = transaction_context["caller"]

        if amount <= 0:
            raise ValueError("Amount must be positive")

        from_balance = self.storage["balances"].get(caller, 0)
        locked_amount = self.storage["locked_tokens"].get(caller, 0)
        available_balance = from_balance - locked_amount

        if available_balance < amount:
            raise ValueError("Insufficient available balance")

        # Execute transfer
        self.storage["balances"][caller] = from_balance - amount
        self.storage["balances"][to] = self.storage["balances"].get(to, 0) + amount

        self._emit_event(
            "Transfer", {"from": caller, "to": to, "amount": amount}, transaction_context
        )

        return True

    def approve(self, spender: str, amount: int, transaction_context: Dict[str, Any]) -> bool:
        """Approve spender to transfer tokens on behalf of caller."""
        caller = transaction_context["caller"]

        if "allowances" not in self.storage:
            self.storage["allowances"] = {}

        if caller not in self.storage["allowances"]:
            self.storage["allowances"][caller] = {}

        self.storage["allowances"][caller][spender] = amount

        self._emit_event(
            "Approval", {"owner": caller, "spender": spender, "amount": amount}, transaction_context
        )

        return True

    def transfer_from(
        self, from_addr: str, to: str, amount: int, transaction_context: Dict[str, Any]
    ) -> bool:
        """Transfer tokens from one account to another using allowance."""
        caller = transaction_context["caller"]

        # Check allowance
        allowance = self.storage["allowances"].get(from_addr, {}).get(caller, 0)
        if allowance < amount:
            raise ValueError("Insufficient allowance")

        # Check balance
        from_balance = self.storage["balances"].get(from_addr, 0)
        locked_amount = self.storage["locked_tokens"].get(from_addr, 0)
        available_balance = from_balance - locked_amount

        if available_balance < amount:
            raise ValueError("Insufficient available balance")

        # Execute transfer
        self.storage["balances"][from_addr] = from_balance - amount
        self.storage["balances"][to] = self.storage["balances"].get(to, 0) + amount
        self.storage["allowances"][from_addr][caller] = allowance - amount

        self._emit_event(
            "Transfer", {"from": from_addr, "to": to, "amount": amount}, transaction_context
        )

        return True

    def lock_tokens(
        self, account: str, amount: int, unlock_time: datetime, transaction_context: Dict[str, Any]
    ) -> bool:
        """Lock tokens for a specific period."""
        balance = self.storage["balances"].get(account, 0)
        current_locked = self.storage["locked_tokens"].get(account, 0)

        if balance < current_locked + amount:
            raise ValueError("Insufficient balance to lock")

        self.storage["locked_tokens"][account] = current_locked + amount

        self._emit_event(
            "TokensLocked",
            {"account": account, "amount": amount, "unlock_time": unlock_time.isoformat()},
            transaction_context,
        )

        return True

    def unlock_tokens(self, account: str, amount: int, transaction_context: Dict[str, Any]) -> bool:
        """Unlock previously locked tokens."""
        current_locked = self.storage["locked_tokens"].get(account, 0)

        if current_locked < amount:
            raise ValueError("Insufficient locked tokens")

        self.storage["locked_tokens"][account] = current_locked - amount

        self._emit_event(
            "TokensUnlocked", {"account": account, "amount": amount}, transaction_context
        )

        return True

    def mint(self, to: str, amount: int, transaction_context: Dict[str, Any]) -> bool:
        """Mint new tokens (governance function)."""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.storage["total_supply"] += amount
        self.storage["balances"][to] = self.storage["balances"].get(to, 0) + amount

        self._emit_event("Mint", {"to": to, "amount": amount}, transaction_context)

        return True

    def burn(self, from_addr: str, amount: int, transaction_context: Dict[str, Any]) -> bool:
        """Burn tokens (governance function)."""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        balance = self.storage["balances"].get(from_addr, 0)
        if balance < amount:
            raise ValueError("Insufficient balance to burn")

        self.storage["balances"][from_addr] = balance - amount
        self.storage["total_supply"] -= amount

        self._emit_event("Burn", {"from": from_addr, "amount": amount}, transaction_context)

        return True


class ProposalContract(SmartContract):
    """Smart contract for managing governance proposals."""

    def __init__(self, address: str, deployer: str):
        super().__init__(address, deployer)
        self.storage["proposals"] = {}
        self.storage["proposal_counter"] = 0
        self.storage["voting_period"] = 7 * 24 * 3600  # 7 days in seconds
        self.storage["quorum_threshold"] = 0.1  # 10%
        self.storage["approval_threshold"] = 0.6  # 60%
        self.state = ContractState.ACTIVE

    def _setup_permissions(self):
        """Setup permissions for proposal contract functions."""
        self.permissions = [
            ContractPermission("create_proposal", PermissionLevel.STAKEHOLDER, [], []),
            ContractPermission("vote", PermissionLevel.STAKEHOLDER, [], []),
            ContractPermission("execute_proposal", PermissionLevel.GOVERNANCE, [], []),
            ContractPermission(
                "emergency_veto", PermissionLevel.ADMIN, ["emergency_responder"], []
            ),
        ]

    def create_proposal(
        self,
        title: str,
        description: str,
        action_data: Dict[str, Any],
        transaction_context: Dict[str, Any],
    ) -> int:
        """Create a new governance proposal."""
        proposal_id = self.storage["proposal_counter"] + 1
        self.storage["proposal_counter"] = proposal_id

        voting_end = datetime.now(tz=timezone.utc) + timedelta(seconds=self.storage["voting_period"])

        proposal = {
            "id": proposal_id,
            "title": title,
            "description": description,
            "proposer": transaction_context["caller"],
            "action_data": action_data,
            "votes_for": 0,
            "votes_against": 0,
            "votes_abstain": 0,
            "voters": {},
            "status": "voting",
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "voting_end": voting_end.isoformat(),
            "executed": False,
        }

        self.storage["proposals"][proposal_id] = proposal

        self._emit_event(
            "ProposalCreated",
            {"proposal_id": proposal_id, "proposer": transaction_context["caller"], "title": title},
            transaction_context,
        )

        return proposal_id

    def vote(
        self,
        proposal_id: int,
        vote_type: str,
        voting_power: int,
        transaction_context: Dict[str, Any],
    ) -> bool:
        """Vote on a proposal."""
        voter = transaction_context["caller"]
        proposal = self.storage["proposals"].get(proposal_id)

        if not proposal:
            raise ValueError("Proposal not found")

        if proposal["status"] != "voting":
            raise ValueError("Proposal not in voting phase")

        voting_end = datetime.fromisoformat(proposal["voting_end"])
        if datetime.now(tz=timezone.utc) > voting_end:
            raise ValueError("Voting period has ended")

        if voter in proposal["voters"]:
            raise ValueError("Already voted on this proposal")

        # Record vote
        proposal["voters"][voter] = {
            "vote_type": vote_type,
            "voting_power": voting_power,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        # Update vote counts
        if vote_type == "for":
            proposal["votes_for"] += voting_power
        elif vote_type == "against":
            proposal["votes_against"] += voting_power
        elif vote_type == "abstain":
            proposal["votes_abstain"] += voting_power
        else:
            raise ValueError("Invalid vote type")

        self._emit_event(
            "VoteCast",
            {
                "proposal_id": proposal_id,
                "voter": voter,
                "vote_type": vote_type,
                "voting_power": voting_power,
            },
            transaction_context,
        )

        return True

    def finalize_proposal(self, proposal_id: int, transaction_context: Dict[str, Any]) -> str:
        """Finalize a proposal after voting period."""
        proposal = self.storage["proposals"].get(proposal_id)

        if not proposal:
            raise ValueError("Proposal not found")

        if proposal["status"] != "voting":
            raise ValueError("Proposal not in voting phase")

        voting_end = datetime.fromisoformat(proposal["voting_end"])
        if datetime.now(tz=timezone.utc) <= voting_end:
            raise ValueError("Voting period not yet ended")

        # Calculate results
        total_votes = proposal["votes_for"] + proposal["votes_against"] + proposal["votes_abstain"]

        # Get total possible voting power (would need token contract integration)
        total_possible_power = transaction_context.get("total_voting_power", 1000000)

        participation_rate = total_votes / total_possible_power
        approval_rate = proposal["votes_for"] / total_votes if total_votes > 0 else 0

        # Determine outcome
        if participation_rate < self.storage["quorum_threshold"]:
            proposal["status"] = "failed_quorum"
            outcome = "failed"
        elif approval_rate >= self.storage["approval_threshold"]:
            proposal["status"] = "passed"
            outcome = "passed"
        else:
            proposal["status"] = "rejected"
            outcome = "rejected"

        proposal["participation_rate"] = participation_rate
        proposal["approval_rate"] = approval_rate
        proposal["finalized_at"] = datetime.now(tz=timezone.utc).isoformat()

        self._emit_event(
            "ProposalFinalized",
            {
                "proposal_id": proposal_id,
                "outcome": outcome,
                "participation_rate": participation_rate,
                "approval_rate": approval_rate,
            },
            transaction_context,
        )

        return outcome

    def execute_proposal(self, proposal_id: int, transaction_context: Dict[str, Any]) -> bool:
        """Execute a passed proposal."""
        proposal = self.storage["proposals"].get(proposal_id)

        if not proposal:
            raise ValueError("Proposal not found")

        if proposal["status"] != "passed":
            raise ValueError("Proposal not passed")

        if proposal["executed"]:
            raise ValueError("Proposal already executed")

        # Mark as executed
        proposal["executed"] = True
        proposal["executed_at"] = datetime.now(tz=timezone.utc).isoformat()

        self._emit_event(
            "ProposalExecuted",
            {"proposal_id": proposal_id, "action_data": proposal["action_data"]},
            transaction_context,
        )

        return True

    def emergency_veto(
        self, proposal_id: int, reason: str, transaction_context: Dict[str, Any]
    ) -> bool:
        """Emergency veto of a proposal."""
        proposal = self.storage["proposals"].get(proposal_id)

        if not proposal:
            raise ValueError("Proposal not found")

        proposal["status"] = "vetoed"
        proposal["veto_reason"] = reason
        proposal["vetoed_at"] = datetime.now(tz=timezone.utc).isoformat()
        proposal["vetoed_by"] = transaction_context["caller"]

        self._emit_event(
            "ProposalVetoed",
            {
                "proposal_id": proposal_id,
                "reason": reason,
                "vetoed_by": transaction_context["caller"],
            },
            transaction_context,
        )

        return True

    def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Get proposal details."""
        return self.storage["proposals"].get(proposal_id, {})


class EthicsEnforcementContract(SmartContract):
    """Smart contract for enforcing ethical constraints."""

    def __init__(self, address: str, deployer: str):
        super().__init__(address, deployer)
        self.storage["constraints"] = {}
        self.storage["violations"] = {}
        self.storage["enforcement_actions"] = {}
        self.storage["constraint_counter"] = 0
        self.state = ContractState.ACTIVE

    def _setup_permissions(self):
        """Setup permissions for ethics enforcement functions."""
        self.permissions = [
            ContractPermission("add_constraint", PermissionLevel.GOVERNANCE, ["ethics_admin"], []),
            ContractPermission("report_violation", PermissionLevel.STAKEHOLDER, [], []),
            ContractPermission("enforce_action", PermissionLevel.SYSTEM, ["enforcement_agent"], []),
            ContractPermission(
                "emergency_shutdown", PermissionLevel.ADMIN, ["emergency_responder"], []
            ),
        ]

    def add_constraint(
        self,
        name: str,
        description: str,
        constraint_logic: str,
        enforcement_action: str,
        transaction_context: Dict[str, Any],
    ) -> int:
        """Add a new ethical constraint."""
        constraint_id = self.storage["constraint_counter"] + 1
        self.storage["constraint_counter"] = constraint_id

        constraint = {
            "id": constraint_id,
            "name": name,
            "description": description,
            "constraint_logic": constraint_logic,
            "enforcement_action": enforcement_action,
            "active": True,
            "created_by": transaction_context["caller"],
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "violation_count": 0,
        }

        self.storage["constraints"][constraint_id] = constraint

        self._emit_event(
            "ConstraintAdded",
            {
                "constraint_id": constraint_id,
                "name": name,
                "created_by": transaction_context["caller"],
            },
            transaction_context,
        )

        return constraint_id

    def check_constraints(
        self, action_data: Dict[str, Any], transaction_context: Dict[str, Any]
    ) -> List[int]:
        """Check action against all active constraints."""
        violated_constraints = []

        for constraint_id, constraint in self.storage["constraints"].items():
            if not constraint["active"]:
                continue

            # Simplified constraint checking
            if self._evaluate_constraint(constraint["constraint_logic"], action_data):
                violated_constraints.append(constraint_id)

        return violated_constraints

    def report_violation(
        self, constraint_id: int, evidence: Dict[str, Any], transaction_context: Dict[str, Any]
    ) -> str:
        """Report a constraint violation."""
        constraint = self.storage["constraints"].get(constraint_id)

        if not constraint:
            raise ValueError("Constraint not found")

        violation_id = f"violation_{constraint_id}_{len(self.storage['violations']) + 1}"

        violation = {
            "id": violation_id,
            "constraint_id": constraint_id,
            "evidence": evidence,
            "reported_by": transaction_context["caller"],
            "reported_at": datetime.now(tz=timezone.utc).isoformat(),
            "severity": evidence.get("severity", "medium"),
            "status": "reported",
            "investigation_started": False,
        }

        self.storage["violations"][violation_id] = violation
        constraint["violation_count"] += 1

        self._emit_event(
            "ViolationReported",
            {
                "violation_id": violation_id,
                "constraint_id": constraint_id,
                "severity": violation["severity"],
                "reported_by": transaction_context["caller"],
            },
            transaction_context,
        )

        # Trigger immediate enforcement for high severity violations
        if violation["severity"] == "high":
            self._trigger_enforcement(constraint_id, violation_id, transaction_context)

        return violation_id

    def enforce_action(
        self, constraint_id: int, action_type: str, target: str, transaction_context: Dict[str, Any]
    ) -> bool:
        """Execute enforcement action for constraint violation."""
        constraint = self.storage["constraints"].get(constraint_id)

        if not constraint:
            raise ValueError("Constraint not found")

        action_id = f"action_{constraint_id}_{len(self.storage['enforcement_actions']) + 1}"

        action = {
            "id": action_id,
            "constraint_id": constraint_id,
            "action_type": action_type,
            "target": target,
            "executed_by": transaction_context["caller"],
            "executed_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": "executed",
        }

        self.storage["enforcement_actions"][action_id] = action

        self._emit_event(
            "EnforcementAction",
            {
                "action_id": action_id,
                "constraint_id": constraint_id,
                "action_type": action_type,
                "target": target,
            },
            transaction_context,
        )

        return True

    def _evaluate_constraint(self, constraint_logic: str, action_data: Dict[str, Any]) -> bool:
        """Evaluate if an action violates a constraint."""
        # Simplified constraint evaluation
        # In practice, this would use a more sophisticated logic engine

        if "harm_level > 0.5" in constraint_logic:
            return action_data.get("harm_level", 0) > 0.5

        if "privacy_violation" in constraint_logic:
            return action_data.get("accesses_personal_data", False) and not action_data.get(
                "has_consent", False
            )

        if "autonomy_violation" in constraint_logic:
            return action_data.get("overrides_human_decision", False)

        return False

    def _trigger_enforcement(
        self, constraint_id: int, violation_id: str, transaction_context: Dict[str, Any]
    ):
        """Trigger immediate enforcement for severe violations."""
        constraint = self.storage["constraints"][constraint_id]
        enforcement_action = constraint["enforcement_action"]

        # Execute enforcement action
        if enforcement_action == "immediate_shutdown":
            self._emit_event(
                "EmergencyShutdown",
                {
                    "constraint_id": constraint_id,
                    "violation_id": violation_id,
                    "reason": "High severity violation",
                },
                transaction_context,
            )

        elif enforcement_action == "restrict_capabilities":
            self._emit_event(
                "CapabilityRestriction",
                {"constraint_id": constraint_id, "violation_id": violation_id},
                transaction_context,
            )


class ContractRegistry:
    """Registry for managing deployed smart contracts."""

    def __init__(self):
        self.contracts: Dict[str, SmartContract] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.transaction_counter = 0
        self.block_height = 0

    def deploy_contract(
        self, contract_class: type, deployer: str, init_params: Dict[str, Any]
    ) -> str:
        """Deploy a new smart contract."""
        try:
            address = self._generate_address(contract_class.__name__)
            contract = contract_class(address, deployer, **init_params)
            self.contracts[address] = contract

            logger.info(f"Deployed contract {contract_class.__name__} at {address}")
            return address

        except Exception as e:
            logger.error(f"Contract deployment failed: {e}")
            raise

    def call_contract(
        self,
        contract_address: str,
        function_name: str,
        caller: str,
        parameters: Dict[str, Any],
        transaction_context: Dict[str, Any] = None,
    ) -> Transaction:
        """Call a contract function."""
        contract = self.contracts.get(contract_address)
        if not contract:
            raise ValueError(f"Contract not found: {contract_address}")

        transaction_id = self._generate_transaction_id()

        if transaction_context is None:
            transaction_context = {}

        transaction_context.update(
            {
                "caller": caller,
                "block_height": self.block_height,
                "transaction_hash": transaction_id,
            }
        )

        transaction = Transaction(
            id=transaction_id,
            from_address=caller,
            to_address=contract_address,
            function_name=function_name,
            parameters=parameters,
            gas_limit=1000000,
            gas_used=0,
            status=ExecutionStatus.PENDING,
            result=None,
            events=[],
            created_at=datetime.now(tz=timezone.utc),
            executed_at=None,
            block_height=None,
        )

        try:
            transaction.status = ExecutionStatus.EXECUTING
            success, result, events = contract.execute_function(
                function_name, caller, parameters, transaction_context
            )

            if success:
                transaction.status = ExecutionStatus.COMPLETED
                transaction.result = result
                transaction.events = events
                transaction.gas_used = 50000  # Simplified gas calculation
            else:
                transaction.status = ExecutionStatus.FAILED
                transaction.result = result

            transaction.executed_at = datetime.now(tz=timezone.utc)
            transaction.block_height = self.block_height

            self.transactions[transaction_id] = transaction

            logger.info(f"Transaction {transaction_id}: {transaction.status.value}")
            return transaction

        except Exception as e:
            transaction.status = ExecutionStatus.FAILED
            transaction.result = str(e)
            transaction.executed_at = datetime.now(tz=timezone.utc)
            self.transactions[transaction_id] = transaction

            logger.error(f"Transaction {transaction_id} failed: {e}")
            return transaction

    def get_contract(self, address: str) -> Optional[SmartContract]:
        """Get contract by address."""
        return self.contracts.get(address)

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self.transactions.get(transaction_id)

    def get_contract_events(
        self, contract_address: str, event_name: str = None
    ) -> List[ContractEvent]:
        """Get events from a contract."""
        contract = self.contracts.get(contract_address)
        if not contract:
            return []

        events = contract.events
        if event_name:
            events = [e for e in events if e.event_name == event_name]

        return events

    def _generate_address(self, contract_name: str) -> str:
        """Generate contract address."""
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        data = f"{contract_name}_{timestamp}_{len(self.contracts)}"
        return f"0x{hashlib.sha256(data.encode()).hexdigest()[:40]}"

    def _generate_transaction_id(self) -> str:
        """Generate transaction ID."""
        self.transaction_counter += 1
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        data = f"tx_{self.transaction_counter}_{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()


# Factory functions for easy contract deployment
def deploy_governance_contracts(registry: ContractRegistry, deployer: str) -> Dict[str, str]:
    """Deploy all governance contracts."""
    contracts = {}

    # Deploy token contract
    token_address = registry.deploy_contract(
        GovernanceTokenContract, deployer, {"initial_supply": 1000000}
    )
    contracts["token"] = token_address

    # Deploy proposal contract
    proposal_address = registry.deploy_contract(ProposalContract, deployer, {})
    contracts["proposal"] = proposal_address

    # Deploy ethics enforcement contract
    ethics_address = registry.deploy_contract(EthicsEnforcementContract, deployer, {})
    contracts["ethics"] = ethics_address

    logger.info(f"Deployed governance contract suite: {contracts}")
    return contracts
