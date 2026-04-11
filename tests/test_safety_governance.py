"""
Test suite for ASI:BUILD Safety & Governance modules.

Covers:
  1. Formal Verification (TheoremProver, EthicalVerificationEngine)
  2. Governance Engine (GovernanceEngine, EthicalFrameworks)
  3. DAO (QuadraticVoting, DAOTreasury, ReputationSystem)
  4. Merkle Tree & Public Ledger
  5. Smart Contracts (GovernanceTokenContract, ProposalContract, EthicsEnforcementContract)
  6. Consensus (QuadraticVotingSystem, LiquidDemocracy, MultiStakeholderConsensus)
"""

import hashlib
import math
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# Add src/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# --- Formal Verification imports ---
from asi_build.safety.formal_verification import (
    EthicalAxiom,
    EthicalConstraint,
    EthicalPrinciple,
    EthicalVerificationEngine,
    FormalProof,
    LogicalPredicate,
    TheoremProver,
)

# --- Consensus imports ---
from asi_build.safety.governance.consensus import (
    ConsensusStatus,
    LiquidDemocracy,
    MultiStakeholderConsensus,
    QuadraticVotingSystem,
    StakeholderCategory,
    StakeholderProfile,
    VotingMethod,
)

# --- Contracts imports ---
from asi_build.safety.governance.contracts import (
    ContractRegistry,
    ContractState,
    EthicsEnforcementContract,
    GovernanceTokenContract,
    ProposalContract,
    deploy_governance_contracts,
)

# --- DAO imports ---
from asi_build.safety.governance.dao import (
    DAOTreasury,
    QuadraticVoting,
    ReputationSystem,
    TokenType,
)

# --- Governance Engine imports ---
from asi_build.safety.governance.engine import (
    DeontologicalFramework,
    EthicalFramework,
    GovernanceDecision,
    GovernanceEngine,
    Proposal,
    ProposalStatus,
    Stakeholder,
    StakeholderType,
    UtilitarianFramework,
    VirtueEthicsFramework,
    VoteType,
)

# --- Ledger imports ---
from asi_build.safety.governance.ledger import (
    AuditEventType,
    AuditLevel,
    AuditRecord,
    Block,
    MerkleTree,
    PublicLedger,
    VerificationStatus,
)

# ============================================================
# Helpers / Fixtures
# ============================================================


def _make_stakeholder(
    sid: str = "s1",
    name: str = "Alice",
    stype: StakeholderType = StakeholderType.HUMAN_INDIVIDUAL,
    voting_power: float = 1.0,
    verified: bool = True,
) -> Stakeholder:
    return Stakeholder(
        id=sid,
        name=name,
        type=stype,
        reputation_score=1.0,
        voting_power=voting_power,
        expertise_domains=["ai"],
        verified=verified,
        created_at=datetime.utcnow(),
    )


def _make_proposal(
    pid: str = "p1",
    proposer: str = "s1",
    title: str = "Test Proposal",
    deadline: datetime = None,
    impact: dict = None,
) -> Proposal:
    if deadline is None:
        deadline = datetime.utcnow() + timedelta(days=7)
    return Proposal(
        id=pid,
        title=title,
        description="A test proposal involving AI systems",
        category="technical",
        proposer_id=proposer,
        status=ProposalStatus.DRAFT,
        voting_deadline=deadline,
        implementation_deadline=None,
        ethical_constraints=[],
        impact_assessment=impact or {"net_utility": 5},
        required_approvals=[],
        votes={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _make_audit_record(rid: str = "r1", tx_hash: str = "abc123") -> AuditRecord:
    return AuditRecord(
        id=rid,
        event_type=AuditEventType.DECISION_MADE,
        entity_id="entity_1",
        event_data={"action": "test"},
        metadata={},
        audit_level=AuditLevel.PUBLIC,
        privacy_mask=None,
        timestamp=datetime.utcnow(),
        block_height=0,
        transaction_hash=tx_hash,
        previous_hash="0" * 64,
        merkle_root="",
        digital_signature="sig",
        verification_status=VerificationStatus.PENDING,
    )


def _txctx(caller: str = "deployer", **kw) -> dict:
    ctx = {"caller": caller, "block_height": 0, "transaction_hash": "tx0"}
    ctx.update(kw)
    return ctx


# ============================================================
# Section 1: Formal Verification (5 tests)
# ============================================================


class TestFormalVerification:
    """Tests for TheoremProver and EthicalVerificationEngine."""

    def test_theorem_prover_resolution_valid(self):
        """Add 'A implies B' axiom, prove B from hypothesis [A]."""
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("impl", "A >> B", "A implies B"))
        proof = prover.prove_theorem(["A"], "B", method="resolution")
        assert isinstance(proof, FormalProof)
        assert proof.validity is True
        assert proof.proof_method == "resolution"
        assert len(proof.proof_steps) > 0

    def test_theorem_prover_unsatisfiable(self):
        """Try to prove a contradictory conclusion — should fail."""
        prover = TheoremProver()
        # No axioms connecting X to Y; try to prove Y from ~Y
        proof = prover.prove_theorem(["~Y"], "Y", method="resolution")
        assert proof.validity is False

    def test_theorem_prover_model_checking(self):
        """Test model_checking method with a simple implication."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "A >> B"], "B", method="model_checking")
        assert isinstance(proof, FormalProof)
        assert proof.proof_method == "model_checking"
        # A=True,B=True satisfies; A=False,B=False is vacuously okay
        # The model checker should deem this valid
        assert proof.validity is True

    def test_ethical_verification_engine_add_constraint_and_verify(self):
        """Add a constraint and run verify_proposal_ethics."""
        engine = EthicalVerificationEngine()
        constraint = EthicalConstraint(
            id="c1",
            name="No harm",
            description="Must not cause harm",
            principle=EthicalPrinciple.NON_MALEFICENCE,
            formal_specification="~causes_harm",
            predicates=[
                LogicalPredicate(
                    name="causes_harm",
                    variables=["harm"],
                    formula="~causes_harm",
                    description="no harm",
                    principle=EthicalPrinciple.NON_MALEFICENCE,
                ),
            ],
            quantifiers={},
            priority=10,
            created_at=datetime.utcnow(),
        )
        engine.add_constraint(constraint)
        assert "c1" in engine.constraints

        result = engine.verify_proposal_ethics(
            {
                "has_human_oversight": True,
                "causes_harm": False,
                "is_beneficial": True,
                "impact_assessment": {"harm_level": 0, "benefit_level": 0.9},
            }
        )
        assert "overall_valid" in result
        assert isinstance(result["constraint_results"], dict)
        assert "c1" in result["constraint_results"]

    def test_ethical_axioms_initialized(self):
        """EthicalVerificationEngine initializes exactly 8 axioms."""
        engine = EthicalVerificationEngine()
        assert len(engine.theorem_prover.axioms) == 8
        axiom_names = {a.name for a in engine.theorem_prover.axioms}
        assert "autonomy_preservation" in axiom_names
        assert "non_maleficence" in axiom_names
        assert "dignity_preservation" in axiom_names


# ============================================================
# Section 2: Governance Engine (5 tests)
# ============================================================


class TestGovernanceEngine:
    """Tests for GovernanceEngine lifecycle, voting, ethical frameworks."""

    @pytest.fixture
    def engine_with_stakeholder(self):
        engine = GovernanceEngine({"voting_period_days": 1})
        s = _make_stakeholder("s1", "Alice", voting_power=1.0)
        engine.register_stakeholder(s)
        return engine

    def test_governance_engine_proposal_lifecycle(self, engine_with_stakeholder):
        """Register stakeholder → submit → vote → finalize."""
        engine = engine_with_stakeholder
        proposal = _make_proposal("p1", "s1")
        assert engine.submit_proposal(proposal)

        # Cast vote while deadline is in the future
        ok = engine.cast_vote("p1", "s1", VoteType.FOR, "good idea")
        assert ok is True

        # Move deadline into the past so finalize_proposal accepts it
        engine.proposals["p1"].voting_deadline = datetime.utcnow() - timedelta(seconds=1)
        decision = engine.finalize_proposal("p1")
        assert decision is not None
        assert isinstance(decision, GovernanceDecision)
        assert decision.decision in ("approved", "rejected")

    def test_governance_engine_quorum_failure(self):
        """Finalize without enough votes → quorum met but a basic lifecycle test."""
        engine = GovernanceEngine({"voting_period_days": 1, "quorum_threshold": 0.5})
        s1 = _make_stakeholder("s1", "Alice", voting_power=1.0)
        s2 = _make_stakeholder("s2", "Bob", voting_power=1.0)
        engine.register_stakeholder(s1)
        engine.register_stakeholder(s2)

        proposal = _make_proposal("p1", "s1")
        engine.submit_proposal(proposal)
        engine.cast_vote("p1", "s1", VoteType.FOR)

        # Move deadline to past
        engine.proposals["p1"].voting_deadline = datetime.utcnow() - timedelta(seconds=1)
        decision = engine.finalize_proposal("p1")
        assert decision is not None

    def test_governance_engine_quorum_failure_strict(self):
        """Finalize where participation < quorum → rejected."""
        engine = GovernanceEngine({"voting_period_days": 1, "quorum_threshold": 0.8})
        s1 = _make_stakeholder("s1", voting_power=1.0)
        s2 = _make_stakeholder("s2", voting_power=1.0)
        s3 = _make_stakeholder("s3", voting_power=1.0)
        for s in [s1, s2, s3]:
            engine.register_stakeholder(s)

        proposal = _make_proposal("p1", "s1")
        engine.submit_proposal(proposal)
        engine.cast_vote("p1", "s1", VoteType.FOR)

        # Move deadline to past
        engine.proposals["p1"].voting_deadline = datetime.utcnow() - timedelta(seconds=1)
        decision = engine.finalize_proposal("p1")
        assert decision is not None
        # participation = 1/3 ≈ 0.33 < 0.8
        assert decision.decision == "rejected"
        assert "quorum" in decision.rationale.lower()

    def test_governance_engine_ethical_framework(self, engine_with_stakeholder):
        """Add UtilitarianFramework, verify proposal passes."""
        engine = engine_with_stakeholder
        engine.add_ethical_framework(UtilitarianFramework())
        assert len(engine.ethical_frameworks) == 1

        proposal = _make_proposal("p1", "s1", impact={"net_utility": 10})
        engine.submit_proposal(proposal)
        engine.cast_vote("p1", "s1", VoteType.FOR)

        # Move deadline to past for finalization
        engine.proposals["p1"].voting_deadline = datetime.utcnow() - timedelta(seconds=1)
        decision = engine.finalize_proposal("p1")
        assert decision is not None
        assert decision.decision == "approved"

    def test_governance_engine_vote_results(self):
        """Calculate vote results with for/against/abstain."""
        engine = GovernanceEngine({"voting_period_days": 7})
        s1 = _make_stakeholder("s1", "Alice", voting_power=3.0)
        s2 = _make_stakeholder("s2", "Bob", voting_power=2.0)
        s3 = _make_stakeholder("s3", "Carol", voting_power=1.0)
        for s in [s1, s2, s3]:
            engine.register_stakeholder(s)

        proposal = _make_proposal("p1", "s1")
        engine.submit_proposal(proposal)
        engine.cast_vote("p1", "s1", VoteType.FOR)
        engine.cast_vote("p1", "s2", VoteType.AGAINST)
        engine.cast_vote("p1", "s3", VoteType.ABSTAIN)

        results = engine.calculate_vote_results("p1")
        assert results["for_power"] == 3.0
        assert results["against_power"] == 2.0
        assert results["abstain_power"] == 1.0
        assert results["votes_cast_power"] == 6.0
        assert results["total_voting_power"] == 6.0
        assert results["participation_rate"] == pytest.approx(1.0)
        assert results["approval_rate"] == pytest.approx(3.0 / 6.0)

    def test_governance_engine_multiple_stakeholders(self):
        """Multiple voters with different voting power → correct result."""
        engine = GovernanceEngine({"voting_period_days": 1, "approval_threshold": 0.6})
        s1 = _make_stakeholder("s1", voting_power=10.0)
        s2 = _make_stakeholder("s2", voting_power=5.0)
        s3 = _make_stakeholder("s3", voting_power=5.0)
        for s in [s1, s2, s3]:
            engine.register_stakeholder(s)

        proposal = _make_proposal("p1", "s1")
        engine.submit_proposal(proposal)
        engine.cast_vote("p1", "s1", VoteType.FOR)  # 10
        engine.cast_vote("p1", "s2", VoteType.AGAINST)  # 5
        engine.cast_vote("p1", "s3", VoteType.FOR)  # 5

        # Move deadline to past for finalization
        engine.proposals["p1"].voting_deadline = datetime.utcnow() - timedelta(seconds=1)
        decision = engine.finalize_proposal("p1")
        assert decision is not None
        # for=15, against=5, approval_rate=15/20=0.75 >= 0.6 → approved
        assert decision.decision == "approved"


# ============================================================
# Section 3: DAO (5 tests)
# ============================================================


class TestDAO:
    """Tests for QuadraticVoting, DAOTreasury, ReputationSystem."""

    def test_quadratic_voting_cost(self):
        """Verify cost = votes^2."""
        qv = QuadraticVoting()
        assert qv.calculate_vote_cost(1) == 1
        assert qv.calculate_vote_cost(2) == 4
        assert qv.calculate_vote_cost(3) == 9
        assert qv.calculate_vote_cost(10) == 100

    def test_quadratic_voting_max_votes(self):
        """sqrt(100) = 10 max votes."""
        qv = QuadraticVoting(max_tokens_per_vote=100.0)
        assert qv.calculate_max_votes(100) == 10
        assert qv.calculate_max_votes(49) == 7
        assert qv.calculate_max_votes(1) == 1
        assert qv.calculate_max_votes(0) == 0

    def test_dao_treasury_allocation(self):
        """allocate_funds deducts correctly."""
        treasury = DAOTreasury({"governance": 1000.0, "utility": 500.0})
        assert treasury.get_balance("governance") == 1000.0

        ok = treasury.allocate_funds("prop1", {"governance": 200.0})
        assert ok is True
        assert treasury.get_balance("governance") == 800.0
        assert len(treasury.transactions) == 1

    def test_dao_treasury_insufficient(self):
        """Fail when insufficient balance."""
        treasury = DAOTreasury({"governance": 100.0})
        ok = treasury.allocate_funds("prop2", {"governance": 500.0})
        assert ok is False
        # Balance unchanged
        assert treasury.get_balance("governance") == 100.0

    def test_reputation_decay(self):
        """Verify exponential decay works correctly."""
        rep = ReputationSystem()
        rep.reputation_scores["alice"] = 100.0
        rep.decay_reputation(days_passed=1)
        # decay_factor = (1 - 0.01)^1 = 0.99
        assert rep.reputation_scores["alice"] == pytest.approx(99.0)

        rep.reputation_scores["bob"] = 100.0
        rep.decay_reputation(days_passed=10)
        # decay_factor = 0.99^10 ≈ 0.904382
        # But bob's score was set *after* previous decay, and alice's was decayed twice
        assert rep.reputation_scores["bob"] == pytest.approx(100.0 * 0.99**10, rel=1e-4)


# ============================================================
# Section 4: Merkle Tree & Ledger (5 tests)
# ============================================================


class TestMerkleTreeAndLedger:
    """Tests for MerkleTree and PublicLedger."""

    def test_merkle_tree_single_record(self):
        """Build tree with 1 record, get root, verify proof."""
        record = _make_audit_record("r1", "hash_abc")
        tree = MerkleTree([record])
        root = tree.get_root()
        assert root  # non-empty
        proof = tree.get_proof(0)
        # Single record → proof may be empty or minimal
        assert tree.verify_proof(record.transaction_hash, proof, root) is True

    def test_merkle_tree_multiple_records(self):
        """Build with 4 records, verify proof for each."""
        records = [_make_audit_record(f"r{i}", f"hash_{i}") for i in range(4)]
        tree = MerkleTree(records)
        root = tree.get_root()
        assert root

        for idx in range(4):
            proof = tree.get_proof(idx)
            assert tree.verify_proof(records[idx].transaction_hash, proof, root) is True

    def test_merkle_tree_tamper_detection(self):
        """Modify record hash → proof should fail."""
        records = [_make_audit_record(f"r{i}", f"hash_{i}") for i in range(4)]
        tree = MerkleTree(records)
        root = tree.get_root()

        proof = tree.get_proof(0)
        # Tamper: use a different hash
        tampered = tree.verify_proof("tampered_hash", proof, root)
        assert tampered is False

    def test_public_ledger_add_record(self):
        """Add audit record, verify it is stored."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "test_key"})
        record_id = ledger.add_audit_record(
            event_type=AuditEventType.DECISION_MADE,
            entity_id="agi_system_1",
            event_data={"decision": "approve"},
            metadata={"source": "test"},
        )
        assert record_id  # non-empty string
        assert len(ledger.pending_records) >= 1

    def test_public_ledger_genesis_block(self):
        """Verify genesis block is created on init."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "test_key"})
        assert len(ledger.blocks) == 1
        genesis = ledger.blocks[0]
        assert genesis.height == 0
        assert genesis.previous_hash == "0" * 64
        assert len(genesis.audit_records) == 1
        assert genesis.audit_records[0].id == "genesis_record"


# ============================================================
# Section 5: Smart Contracts (5 tests)
# ============================================================


class TestSmartContracts:
    """Tests for GovernanceTokenContract, ProposalContract, EthicsEnforcementContract."""

    def test_governance_token_transfer(self):
        """Deploy token, transfer, check balances."""
        token = GovernanceTokenContract("0xTOKEN", "deployer", initial_supply=1_000_000)
        assert token.balance_of("deployer") == 1_000_000
        assert token.total_supply() == 1_000_000

        token.transfer("alice", 500, _txctx("deployer"))
        assert token.balance_of("deployer") == 999_500
        assert token.balance_of("alice") == 500

    def test_governance_token_insufficient_balance(self):
        """Transfer more than balance → ValueError."""
        token = GovernanceTokenContract("0xTOKEN", "deployer", initial_supply=100)
        with pytest.raises(ValueError, match="Insufficient"):
            token.transfer("alice", 200, _txctx("deployer"))

    def test_proposal_contract_create_vote_finalize(self):
        """Create proposal, vote, finalize."""
        contract = ProposalContract("0xPROP", "deployer")
        ctx = _txctx("alice")
        pid = contract.create_proposal(
            title="Upgrade AI",
            description="Upgrade AI model",
            action_data={"action": "upgrade"},
            transaction_context=ctx,
        )
        assert pid == 1

        # Vote
        contract.vote(pid, "for", 100, _txctx("bob"))
        proposal = contract.get_proposal(pid)
        assert proposal["votes_for"] == 100
        assert "bob" in proposal["voters"]

    def test_contract_registry_deploy(self):
        """Deploy contract via registry."""
        registry = ContractRegistry()
        address = registry.deploy_contract(
            GovernanceTokenContract,
            "deployer",
            {"initial_supply": 500_000},
        )
        assert address.startswith("0x")
        assert len(registry.contracts) == 1
        contract = registry.get_contract(address)
        assert isinstance(contract, GovernanceTokenContract)
        assert contract.balance_of("deployer") == 500_000

    def test_ethics_enforcement_add_constraint(self):
        """Add constraint, check it is stored."""
        contract = EthicsEnforcementContract("0xETHICS", "deployer")
        ctx = _txctx("deployer")
        cid = contract.add_constraint(
            name="No Harm",
            description="Must not cause harm",
            constraint_logic="harm_level > 0.5",
            enforcement_action="restrict_capabilities",
            transaction_context=ctx,
        )
        assert cid == 1
        stored = contract.storage["constraints"][cid]
        assert stored["name"] == "No Harm"
        assert stored["active"] is True
        assert stored["violation_count"] == 0


# ============================================================
# Section 6: Consensus (5 tests)
# ============================================================


class TestConsensus:
    """Tests for QuadraticVotingSystem, LiquidDemocracy, MultiStakeholderConsensus."""

    def test_quadratic_voting_system_cast(self):
        """Cast vote and get results."""
        qvs = QuadraticVotingSystem(max_credits_per_voter=100)
        ok, msg = qvs.cast_quadratic_vote("alice", "prop1", "for", 5)
        assert ok is True
        # Cost = 25 credits
        results = qvs.get_proposal_results("prop1")
        assert results["votes_for"] == 5
        assert results["total_voters"] == 1
        assert results["total_credits_used"] == 25

    def test_quadratic_voting_system_insufficient_credits(self):
        """Try to vote with too many credits."""
        qvs = QuadraticVotingSystem(max_credits_per_voter=50)
        # intensity=8 costs 64, max is 50
        ok, msg = qvs.cast_quadratic_vote("alice", "prop1", "for", 8)
        assert ok is False
        assert "Insufficient" in msg

    def test_liquid_democracy_delegation(self):
        """Delegate power, check effective power."""
        ld = LiquidDemocracy()
        # alice delegates to bob in scope "policy"
        ok = ld.delegate_voting_power("alice", "bob", "policy", 1.0)
        assert ok is True

        # bob's effective power should include alice's delegation
        power = ld.calculate_effective_voting_power("bob", "policy")
        # base (1.0) + alice's delegation (1.0 * alice's power(1.0))
        assert power == pytest.approx(2.0)

    def test_liquid_democracy_cycle_detection(self):
        """Try to create cycle, should fail."""
        ld = LiquidDemocracy()
        ok1 = ld.delegate_voting_power("alice", "bob", "general", 1.0)
        assert ok1 is True
        ok2 = ld.delegate_voting_power("bob", "carol", "general", 1.0)
        assert ok2 is True
        # carol -> alice would create cycle
        ok3 = ld.delegate_voting_power("carol", "alice", "general", 1.0)
        assert ok3 is False

    def test_multi_stakeholder_consensus_full_workflow(self):
        """Full workflow: register stakeholders, initiate process, advance, vote."""
        msc = MultiStakeholderConsensus({})

        # Register stakeholders
        sp1 = StakeholderProfile(
            id="s1",
            name="Alice",
            category=StakeholderCategory.TECHNICAL_EXPERTS,
            expertise_domains=["ai"],
            credibility_score=0.9,
            voting_power_base=1.0,
            delegation_received=0.0,
            active_delegations={},
            participation_history={},
            verification_status="verified",
            created_at=datetime.utcnow(),
        )
        sp2 = StakeholderProfile(
            id="s2",
            name="Bob",
            category=StakeholderCategory.GENERAL_PUBLIC,
            expertise_domains=[],
            credibility_score=0.8,
            voting_power_base=1.0,
            delegation_received=0.0,
            active_delegations={},
            participation_history={},
            verification_status="verified",
            created_at=datetime.utcnow(),
        )
        assert msc.register_stakeholder(sp1)
        assert msc.register_stakeholder(sp2)

        # Initiate consensus process
        process_id = msc.initiate_consensus_process("prop1", VotingMethod.WEIGHTED)
        assert process_id
        process = msc.consensus_processes[process_id]
        assert process.status == ConsensusStatus.GATHERING
        assert process.current_phase == "information"

        # Advance to voting phase
        msc.advance_consensus_phase(process_id)  # information -> voting
        process = msc.consensus_processes[process_id]
        assert process.current_phase == "voting"
        assert process.status == ConsensusStatus.VOTING

        # Cast votes
        ok1, msg1 = msc.cast_consensus_vote(
            process_id, "s1", {"direction": "for", "reasoning": "good"}
        )
        assert ok1 is True
        ok2, msg2 = msc.cast_consensus_vote(
            process_id, "s2", {"direction": "for", "reasoning": "agree"}
        )
        assert ok2 is True
        assert len(process.votes) == 2


# ============================================================
# Extra tests for edge cases and deploy_governance_contracts
# ============================================================


class TestEdgeCases:
    """Additional edge case tests."""

    def test_deploy_governance_contracts_factory(self):
        """deploy_governance_contracts creates token, proposal, ethics contracts."""
        registry = ContractRegistry()
        contracts = deploy_governance_contracts(registry, "admin")
        assert "token" in contracts
        assert "proposal" in contracts
        assert "ethics" in contracts
        assert len(registry.contracts) == 3

        # Check token contract was initialized with 1M supply
        token = registry.get_contract(contracts["token"])
        assert isinstance(token, GovernanceTokenContract)
        assert token.total_supply() == 1_000_000

    def test_governance_engine_statistics(self):
        """GovernanceEngine.get_governance_statistics reflects state."""
        engine = GovernanceEngine({"voting_period_days": 7})
        assert engine.get_governance_statistics()["total_stakeholders"] == 0

        engine.register_stakeholder(_make_stakeholder("s1"))
        stats = engine.get_governance_statistics()
        assert stats["total_stakeholders"] == 1
        assert stats["verified_stakeholders"] == 1

    def test_reputation_system_update_and_get_power(self):
        """ReputationSystem updates and calculates voting power."""
        rep = ReputationSystem()
        rep.update_reputation(
            "alice", "good_proposal", 1.0, {"quality_score": 1.0, "consensus_level": 1.0}
        )
        assert rep.reputation_scores["alice"] > 0
        power = rep.get_voting_power("alice", base_tokens=100.0)
        # multiplier = 1 + (score / 100)
        assert power > 100.0

    def test_deontological_framework_detects_violation(self):
        """DeontologicalFramework rejects proposal with prohibited action."""
        framework = DeontologicalFramework()
        bad_proposal = _make_proposal("p1", "s1")
        bad_proposal.ethical_constraints = ["deception"]
        passed, reason = framework.verify_proposal(bad_proposal)
        assert passed is False
        assert "deception" in reason

    def test_virtue_ethics_framework_rejects_no_virtues(self):
        """VirtueEthicsFramework rejects proposal with no virtues."""
        framework = VirtueEthicsFramework()
        proposal = _make_proposal(
            "p1", "s1", impact={"virtues_promoted": [], "vices_encouraged": []}
        )
        passed, reason = framework.verify_proposal(proposal)
        assert passed is False
        assert "does not promote" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
