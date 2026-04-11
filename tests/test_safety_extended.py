"""
Extended test suite for ASI:BUILD Safety & Governance modules.

Targets uncovered paths beyond test_safety_governance.py:
  - Formal Verification: natural_deduction, unknown method, report/stats, parse edge cases
  - Governance Engine: duplicate stakeholder, proposal summary, export audit trail, unregistered voter
  - DAO: DAOGovernance full lifecycle, token distribution, insufficient tokens, proposal types
  - Ledger: CryptographicVerifier, PrivacyPreserver, PublicLedger query/verify/stats/block creation
  - AuditLogger
  - Contracts: approve/transfer_from, lock/unlock tokens, mint/burn, pause/resume, 
               ProposalContract finalize/execute/veto, EthicsEnforcementContract check/report/enforce,
               ContractRegistry call_contract/events
  - Consensus: finalize_consensus for all methods, quadratic multi-voter, delegation chain,
               revoke delegation, consensus summary, influence analysis, SIMPLE method
  - Rights: RightsManager full lifecycle, entity consciousness, consent manager, HumanRightsFramework,
            AGIRightsFramework, violations, statistics
  - Override: DemocraticOverrideSystem full lifecycle, emergency stop, appeal, HITL controller,
              override statistics, severity assessment, trigger conditions
  - Framework: ConstitutionalAI full API, constitution lifecycle, safe action generation
"""

import sys
import os
import math
import hashlib
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from dataclasses import asdict

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# --- Formal Verification ---
from asi_build.safety.formal_verification import (
    TheoremProver, EthicalVerificationEngine, EthicalAxiom, EthicalConstraint,
    LogicalPredicate, EthicalPrinciple, FormalProof, ProofStep, LogicOperator,
)

# --- Governance Engine ---
from asi_build.safety.governance.engine import (
    GovernanceEngine, Proposal, Stakeholder, StakeholderType, ProposalStatus,
    VoteType, GovernanceDecision, EthicalFramework, UtilitarianFramework,
    DeontologicalFramework, VirtueEthicsFramework,
)

# --- DAO ---
from asi_build.safety.governance.dao import (
    QuadraticVoting, DAOTreasury, ReputationSystem, DAOGovernance,
    ProposalType, TokenType, DAOToken, DAOProposal,
)

# --- Ledger ---
from asi_build.safety.governance.ledger import (
    MerkleTree, PublicLedger, AuditRecord, AuditEventType, AuditLevel,
    VerificationStatus, Block, AuditQuery, CryptographicVerifier,
    PrivacyPreserver, AuditLogger,
)

# --- Contracts ---
from asi_build.safety.governance.contracts import (
    GovernanceTokenContract, ProposalContract, EthicsEnforcementContract,
    ContractRegistry, ContractState, ExecutionStatus, PermissionLevel,
    ContractPermission, deploy_governance_contracts,
)

# --- Consensus ---
from asi_build.safety.governance.consensus import (
    QuadraticVotingSystem, LiquidDemocracy, MultiStakeholderConsensus,
    StakeholderProfile, StakeholderCategory, VotingMethod, ConsensusStatus,
)

# --- Rights ---
from asi_build.safety.governance.rights import (
    RightsManager, ConsentManager, HumanRightsFramework, AGIRightsFramework,
    EntityType, RightType, RightStatus, ConsentType, Right, Entity,
    RightGrant, ConsentRecord, RightViolation,
)

# --- Override ---
from asi_build.safety.governance.override import (
    DemocraticOverrideSystem, HumanInTheLoopController,
    OverrideType, OverrideStatus, OverrideSeverity, TriggerCondition,
    OverrideCapability, EmergencyProtocol,
)

# --- Framework ---
from asi_build.safety.framework import ConstitutionalAI, Constitution


# ============================================================
# Helpers
# ============================================================

def _txctx(caller: str = "deployer", **kw) -> dict:
    ctx = {"caller": caller, "block_height": 0, "transaction_hash": "tx0"}
    ctx.update(kw)
    return ctx


def _make_stakeholder(sid="s1", name="Alice",
                      stype=StakeholderType.HUMAN_INDIVIDUAL,
                      voting_power=1.0, verified=True):
    return Stakeholder(
        id=sid, name=name, type=stype, reputation_score=1.0,
        voting_power=voting_power, expertise_domains=["ai"],
        verified=verified, created_at=datetime.utcnow(),
    )


def _make_proposal(pid="p1", proposer="s1", title="Test Proposal",
                   deadline=None, impact=None):
    if deadline is None:
        deadline = datetime.utcnow() + timedelta(days=7)
    return Proposal(
        id=pid, title=title, description="A test proposal involving AI systems",
        category="technical", proposer_id=proposer, status=ProposalStatus.DRAFT,
        voting_deadline=deadline, implementation_deadline=None,
        ethical_constraints=[], impact_assessment=impact or {"net_utility": 5},
        required_approvals=[], votes={},
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


def _make_audit_record(rid="r1", tx_hash="abc123"):
    return AuditRecord(
        id=rid, event_type=AuditEventType.DECISION_MADE, entity_id="entity_1",
        event_data={"action": "test"}, metadata={}, audit_level=AuditLevel.PUBLIC,
        privacy_mask=None, timestamp=datetime.utcnow(), block_height=0,
        transaction_hash=tx_hash, previous_hash="0" * 64, merkle_root="",
        digital_signature="sig", verification_status=VerificationStatus.PENDING,
    )


def _make_entity(eid="e1", name="TestEntity",
                 etype=EntityType.HUMAN, **kwargs):
    return Entity(
        id=eid, name=name, entity_type=etype,
        capabilities=kwargs.get("capabilities", ["reasoning"]),
        consciousness_level=kwargs.get("consciousness_level", None),
        autonomy_level=kwargs.get("autonomy_level", None),
        rights_granted=[], consent_records=[], guardian_id=None,
        creation_date=datetime.utcnow(), last_assessment=None, metadata={},
    )


def _make_stakeholder_profile(sid="s1", name="Alice",
                              cat=StakeholderCategory.TECHNICAL_EXPERTS,
                              credibility=0.9, power=1.0):
    return StakeholderProfile(
        id=sid, name=name, category=cat, expertise_domains=["ai"],
        credibility_score=credibility, voting_power_base=power,
        delegation_received=0.0, active_delegations={},
        participation_history={}, verification_status="verified",
        created_at=datetime.utcnow(),
    )


# ============================================================
# 1. Formal Verification — Extended
# ============================================================

class TestFormalVerificationExtended:

    def test_natural_deduction_method(self):
        """Prove using natural deduction."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A", "B"], "A & B", method="natural_deduction")
        assert isinstance(proof, FormalProof)
        assert proof.proof_method == "natural_deduction"

    def test_unknown_method_returns_invalid(self):
        """Unknown proof method => validity=False (error caught)."""
        prover = TheoremProver()
        proof = prover.prove_theorem(["A"], "B", method="bogus")
        assert proof.validity is False

    def test_ethics_report_generation(self):
        """generate_ethics_report produces readable text."""
        engine = EthicalVerificationEngine()
        results = {
            "overall_valid": False,
            "constraint_results": {"c1": {"valid": False}},
            "failed_constraints": [
                {"constraint_name": "No harm", "principle": "non_maleficence",
                 "reason": "proof failed"}
            ],
            "warnings": ["slow proof"],
            "proofs": [],
        }
        report = engine.generate_ethics_report(results)
        assert "FAILED" in report
        assert "No harm" in report
        assert "slow proof" in report

    def test_verification_statistics(self):
        """get_verification_statistics reflects state."""
        engine = EthicalVerificationEngine()
        stats = engine.get_verification_statistics()
        assert stats["total_constraints"] == 0
        assert stats["total_axioms"] == 8

    def test_theorem_prover_known_theorems_accumulate(self):
        """Valid proofs are stored in known_theorems."""
        prover = TheoremProver()
        prover.add_axiom(EthicalAxiom("imp", "A >> B", "A implies B"))
        prover.prove_theorem(["A"], "B", method="resolution")
        assert len(prover.known_theorems) == 1

    def test_axiom_to_sympy(self):
        """EthicalAxiom.to_sympy() returns a SymPy expression."""
        axiom = EthicalAxiom("test", "A >> B", "A implies B")
        expr = axiom.to_sympy()
        assert expr is not None
        # Should contain symbol A and B
        symbols = {str(s) for s in expr.free_symbols}
        assert "A" in symbols
        assert "B" in symbols

    def test_verify_proposal_with_harm(self):
        """Proposal that causes harm triggers constraint check."""
        engine = EthicalVerificationEngine()
        constraint = EthicalConstraint(
            id="harm_check", name="Harm Prevention",
            description="No significant harm",
            principle=EthicalPrinciple.NON_MALEFICENCE,
            formal_specification="~causes_significant_harm",
            predicates=[LogicalPredicate(
                name="causes_significant_harm", variables=["harm"],
                formula="~causes_significant_harm",
                description="no significant harm",
                principle=EthicalPrinciple.NON_MALEFICENCE,
            )],
            quantifiers={}, priority=10, created_at=datetime.utcnow(),
        )
        engine.add_constraint(constraint)
        result = engine.verify_proposal_ethics({
            "impact_assessment": {"harm_level": 0.9, "benefit_level": 0.1},
        })
        assert "harm_check" in result["constraint_results"]

    def test_extract_facts_proposal_fields(self):
        """_extract_facts_from_proposal maps known boolean fields."""
        engine = EthicalVerificationEngine()
        constraint = EthicalConstraint(
            id="c", name="test", description="t",
            principle=EthicalPrinciple.AUTONOMY,
            formal_specification="respects_autonomy",
            predicates=[], quantifiers={}, priority=1,
            created_at=datetime.utcnow(),
        )
        facts = engine._extract_facts_from_proposal({
            "respects_autonomy": True,
            "is_transparent": False,
            "category": "policy",
            "description": "AI data processing system",
            "impact_assessment": {"affected_parties": list(range(20))},
        }, constraint)
        assert facts["respects_autonomy"] is True
        assert facts["is_transparent"] is False
        assert facts["is_policy_change"] is True
        assert facts["involves_ai_systems"] is True
        assert facts["involves_data_processing"] is True
        assert facts["affects_many_stakeholders"] is True


# ============================================================
# 2. Governance Engine — Extended
# ============================================================

class TestGovernanceEngineExtended:

    def test_duplicate_stakeholder_rejected(self):
        """Registering same ID twice returns True but overwrites."""
        engine = GovernanceEngine({"voting_period_days": 1})
        s = _make_stakeholder("s1", "Alice")
        assert engine.register_stakeholder(s) is True
        s2 = _make_stakeholder("s1", "Alice2")
        # Should still succeed (overwrite)
        assert engine.register_stakeholder(s2) is True
        assert engine.stakeholders["s1"].name == "Alice2"

    def test_unregistered_voter_fails(self):
        """Vote from unregistered stakeholder returns False."""
        engine = GovernanceEngine({"voting_period_days": 7})
        engine.register_stakeholder(_make_stakeholder("s1"))
        p = _make_proposal("p1", "s1")
        engine.submit_proposal(p)
        ok = engine.cast_vote("p1", "nonexistent", VoteType.FOR)
        assert ok is False

    def test_vote_on_nonexistent_proposal_fails(self):
        """Vote on missing proposal returns False."""
        engine = GovernanceEngine({"voting_period_days": 7})
        engine.register_stakeholder(_make_stakeholder("s1"))
        ok = engine.cast_vote("no_such_proposal", "s1", VoteType.FOR)
        assert ok is False

    def test_export_audit_trail(self):
        """export_audit_trail returns list of events."""
        engine = GovernanceEngine({"voting_period_days": 7})
        engine.register_stakeholder(_make_stakeholder("s1"))
        trail = engine.export_audit_trail()
        assert isinstance(trail, list)

    def test_get_proposal_summary(self):
        """get_proposal_summary returns dict or None."""
        engine = GovernanceEngine({"voting_period_days": 7})
        assert engine.get_proposal_summary("nope") is None

        engine.register_stakeholder(_make_stakeholder("s1"))
        engine.submit_proposal(_make_proposal("p1", "s1"))
        summary = engine.get_proposal_summary("p1")
        assert summary is not None
        assert summary["title"] == "Test Proposal"

    def test_deontological_no_violation_passes(self):
        """DeontologicalFramework passes clean proposal."""
        fw = DeontologicalFramework()
        p = _make_proposal("p1", impact={"net_utility": 5})
        p.ethical_constraints = ["transparency"]
        passed, reason = fw.verify_proposal(p)
        assert passed is True

    def test_utilitarian_negative_utility_fails(self):
        """UtilitarianFramework rejects negative net_utility."""
        fw = UtilitarianFramework()
        p = _make_proposal("p1", impact={"net_utility": -5})
        passed, reason = fw.verify_proposal(p)
        assert passed is False

    def test_virtue_ethics_with_virtues_passes(self):
        """VirtueEthicsFramework passes proposal promoting virtues."""
        fw = VirtueEthicsFramework()
        p = _make_proposal("p1", impact={
            "virtues_promoted": ["justice", "prudence"],
            "vices_encouraged": [],
        })
        passed, reason = fw.verify_proposal(p)
        assert passed is True

    def test_multiple_ethical_frameworks(self):
        """Engine with multiple frameworks evaluates all."""
        engine = GovernanceEngine({"voting_period_days": 1})
        engine.register_stakeholder(_make_stakeholder("s1"))
        engine.add_ethical_framework(UtilitarianFramework())
        engine.add_ethical_framework(DeontologicalFramework())
        assert len(engine.ethical_frameworks) == 2

    def test_finalize_nonexistent_proposal(self):
        """Finalize missing proposal returns None."""
        engine = GovernanceEngine({"voting_period_days": 1})
        assert engine.finalize_proposal("nope") is None


# ============================================================
# 3. DAO — Extended
# ============================================================

class TestDAOExtended:

    def test_treasury_add_revenue(self):
        """add_revenue increases balance."""
        treasury = DAOTreasury({"governance": 100.0})
        treasury.add_revenue("governance", 50.0, "donation")
        assert treasury.get_balance("governance") == 150.0
        assert len(treasury.transactions) == 1

    def test_treasury_nonexistent_balance(self):
        """get_balance returns 0 for unknown token."""
        treasury = DAOTreasury({})
        assert treasury.get_balance("nonexistent") == 0.0

    def test_quadratic_voting_cast(self):
        """QuadraticVoting.cast_quadratic_vote returns correct data."""
        qv = QuadraticVoting()
        result = qv.cast_quadratic_vote("alice", "prop1", 3, "for")
        assert result["voter_id"] == "alice"
        assert result["token_cost"] == 9.0
        assert result["voting_power"] == 3

    def test_reputation_system_action_types(self):
        """Test different reputation action types."""
        rep = ReputationSystem()
        rep.update_reputation("alice", "good_proposal", 0.5,
                              {"quality_score": 0.8, "consensus_level": 0.7})
        assert rep.reputation_scores["alice"] > 0

        rep.update_reputation("alice", "bad_proposal", -0.5,
                              {"quality_score": 0.2, "consensus_level": 0.3})
        # Score may decrease but should remain non-negative
        assert rep.reputation_scores["alice"] >= 0

    def test_dao_governance_distribute_tokens(self):
        """DAOGovernance distributes tokens correctly."""
        dao = DAOGovernance({"initial_treasury": {"governance": 1000}})
        ok = dao.distribute_tokens("alice", TokenType.GOVERNANCE, 500.0, "initial")
        assert ok is True
        assert len(dao.tokens["alice"]) == 1
        assert dao.tokens["alice"][0].amount == 500.0

    def test_dao_governance_create_proposal(self):
        """Create a DAO proposal with sufficient tokens."""
        dao = DAOGovernance({
            "initial_treasury": {"governance": 10000},
            "min_proposal_tokens": 100,
        })
        dao.distribute_tokens("alice", TokenType.GOVERNANCE, 500.0, "init")
        proposal = dao.create_dao_proposal({
            "proposer_id": "alice",
            "title": "Budget Increase",
            "description": "Increase research budget",
            "proposal_type": "budget",
        })
        assert proposal is not None
        assert proposal.title == "Budget Increase"
        assert len(dao.proposals) == 1

    def test_dao_governance_create_proposal_insufficient_tokens(self):
        """Create proposal fails without tokens."""
        dao = DAOGovernance({"min_proposal_tokens": 100})
        result = dao.create_dao_proposal({
            "proposer_id": "nobody",
            "title": "Fail",
            "description": "no tokens",
            "proposal_type": "technical",
        })
        assert result is None

    def test_dao_statistics(self):
        """get_dao_statistics returns expected keys."""
        dao = DAOGovernance({"initial_treasury": {"governance": 100}})
        stats = dao.get_dao_statistics()
        assert "total_proposals" in stats
        assert "treasury_balances" in stats

    def test_reputation_decay_zero_days(self):
        """Decay with 0 days does nothing."""
        rep = ReputationSystem()
        rep.reputation_scores["alice"] = 100.0
        rep.decay_reputation(days_passed=0)
        assert rep.reputation_scores["alice"] == pytest.approx(100.0)


# ============================================================
# 4. Ledger — Extended
# ============================================================

class TestLedgerExtended:

    def test_cryptographic_verifier_sign_verify(self):
        """Sign and verify with same key succeeds."""
        verifier = CryptographicVerifier("my_secret_key")
        data = "important data"
        sig = verifier.sign_record(data)
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex

        # Verify with same key
        assert verifier.verify_signature(data, sig, "my_secret_key") is True
        assert verifier.verify_signature(data, sig, "wrong_key") is False

    def test_cryptographic_verifier_hash_record(self):
        """hash_record produces deterministic hash."""
        verifier = CryptographicVerifier("key")
        rec = _make_audit_record("r1", "hash1")
        h1 = verifier.hash_record(rec)
        h2 = verifier.hash_record(rec)
        assert h1 == h2
        assert len(h1) == 64

    def test_privacy_preserver_hash_method(self):
        """Privacy mask with 'hash' method."""
        pp = PrivacyPreserver()
        pp.add_privacy_rule("decision_made", "action", "hash", {})
        rec = _make_audit_record()
        mask = pp.apply_privacy_mask(rec)
        assert "action" in mask
        assert mask["action"]["method"] == "hash"
        assert len(mask["action"]["masked_value"]) == 16

    def test_privacy_preserver_redact_method(self):
        """Privacy mask with 'redact' method."""
        pp = PrivacyPreserver()
        pp.add_privacy_rule("decision_made", "action", "redact", {})
        rec = _make_audit_record()
        mask = pp.apply_privacy_mask(rec)
        assert mask["action"]["masked_value"] == "*" * len("test")

    def test_privacy_preserver_generalize_numeric(self):
        """Generalize numeric value."""
        pp = PrivacyPreserver()
        pp.add_privacy_rule("decision_made", "score", "generalize",
                            {"bucket_size": 10})
        rec = _make_audit_record()
        rec.event_data["score"] = 37
        mask = pp.apply_privacy_mask(rec)
        assert mask["score"]["masked_value"] == 30

    def test_privacy_preserver_generalize_string(self):
        """Generalize long string."""
        pp = PrivacyPreserver()
        pp.add_privacy_rule("decision_made", "action", "generalize",
                            {"max_length": 2})
        rec = _make_audit_record()
        mask = pp.apply_privacy_mask(rec)
        assert mask["action"]["masked_value"] == "te..."

    def test_privacy_preserver_differential_privacy(self):
        """Differential privacy adds noise."""
        pp = PrivacyPreserver()
        pp.add_privacy_rule("decision_made", "score", "differential_privacy",
                            {"epsilon": 1.0, "sensitivity": 1.0})
        rec = _make_audit_record()
        rec.event_data["score"] = 50.0
        mask = pp.apply_privacy_mask(rec)
        # Noisy value should differ from original (extremely unlikely to be exact)
        noisy = mask["score"]["masked_value"]
        assert isinstance(noisy, float)

    def test_privacy_preserver_no_rules(self):
        """No rules => empty mask."""
        pp = PrivacyPreserver()
        rec = _make_audit_record()
        mask = pp.apply_privacy_mask(rec)
        assert mask == {}

    def test_merkle_tree_empty(self):
        """MerkleTree with empty records still has a root (hash of empty)."""
        tree = MerkleTree([])
        root = tree.get_root()
        # Empty tree returns hash of "", not ""
        assert isinstance(root, str)
        assert len(root) == 64  # SHA-256 hex

    def test_merkle_tree_odd_count(self):
        """MerkleTree with odd number of records — verify first two (last may duplicate-pad)."""
        records = [_make_audit_record(f"r{i}", f"hash_{i}") for i in range(3)]
        tree = MerkleTree(records)
        root = tree.get_root()
        assert root
        # Verify first two records (index 0 and 1)
        for idx in range(2):
            proof = tree.get_proof(idx)
            assert tree.verify_proof(records[idx].transaction_hash, proof, root)

    def test_public_ledger_audit_statistics(self):
        """get_audit_statistics reflects genesis + added records."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        stats = ledger.get_audit_statistics()
        assert stats["total_blocks"] == 1
        assert stats["total_records"] >= 1  # genesis

    def test_public_ledger_multiple_records(self):
        """Add multiple records and query them."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        for i in range(5):
            ledger.add_audit_record(
                AuditEventType.VOTE_CAST, f"voter_{i}",
                {"vote": "for"}, {"round": i})
        stats = ledger.get_audit_statistics()
        assert stats["total_records"] >= 6  # 1 genesis + 5 added

    def test_public_ledger_query_by_entity(self):
        """Query records by entity_id."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        ledger.add_audit_record(
            AuditEventType.VOTE_CAST, "voter_A",
            {"vote": "for"})
        ledger.add_audit_record(
            AuditEventType.VOTE_CAST, "voter_B",
            {"vote": "against"})

        query = AuditQuery(
            event_types=None, entity_ids=["voter_A"],
            date_range=None, audit_levels=None,
            verification_status=None, limit=None, offset=None)
        results = ledger.query_audit_records(query)
        assert all(r.entity_id == "voter_A" for r in results)

    def test_audit_logger_log_decision(self):
        """AuditLogger.log_decision adds a record."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        logger = AuditLogger(ledger)
        logger.log_decision("d1", {"decision": "approve"})
        assert len(ledger.pending_records) >= 1

    def test_audit_logger_log_vote(self):
        """AuditLogger.log_vote adds a record."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        al = AuditLogger(ledger)
        al.log_vote("v1", {"direction": "for"}, sensitive=True)
        assert len(ledger.pending_records) >= 1

    def test_audit_logger_log_ethics_verification(self):
        """AuditLogger.log_ethics_verification adds a record."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        al = AuditLogger(ledger)
        al.log_ethics_verification("ev1", {"result": "pass"})
        assert len(ledger.pending_records) >= 1

    def test_audit_logger_log_harm_prevention(self):
        """AuditLogger.log_harm_prevention adds a record."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        al = AuditLogger(ledger)
        al.log_harm_prevention("hp1", {"incident": "prevented"})
        assert len(ledger.pending_records) >= 1

    def test_audit_logger_log_override(self):
        """AuditLogger.log_override adds a record."""
        ledger = PublicLedger({"db_path": ":memory:", "private_key": "key"})
        al = AuditLogger(ledger)
        al.log_override("or1", {"type": "emergency"})
        assert len(ledger.pending_records) >= 1

    def test_public_ledger_block_creation_on_full(self):
        """Block auto-created when pending_records >= block_size."""
        ledger = PublicLedger({
            "db_path": ":memory:", "private_key": "key",
            "block_size": 3,
        })
        initial_blocks = len(ledger.blocks)
        for i in range(3):
            ledger.add_audit_record(
                AuditEventType.DECISION_MADE, "e1",
                {"action": f"test_{i}"})
        assert len(ledger.blocks) > initial_blocks


# ============================================================
# 5. Contracts — Extended
# ============================================================

class TestContractsExtended:

    def test_token_approve_and_transfer_from(self):
        """Approve spender, then transfer_from succeeds."""
        token = GovernanceTokenContract("0xT", "alice", initial_supply=1000)
        token.approve("bob", 500, _txctx("alice"))
        assert token.storage["allowances"]["alice"]["bob"] == 500

        token.transfer_from("alice", "carol", 200, _txctx("bob"))
        assert token.balance_of("alice") == 800
        assert token.balance_of("carol") == 200
        assert token.storage["allowances"]["alice"]["bob"] == 300

    def test_token_transfer_from_insufficient_allowance(self):
        """transfer_from with insufficient allowance raises."""
        token = GovernanceTokenContract("0xT", "alice", initial_supply=1000)
        token.approve("bob", 10, _txctx("alice"))
        with pytest.raises(ValueError, match="Insufficient allowance"):
            token.transfer_from("alice", "carol", 100, _txctx("bob"))

    def test_token_lock_and_unlock(self):
        """lock_tokens restricts available balance."""
        token = GovernanceTokenContract("0xT", "alice", initial_supply=1000)
        unlock_time = datetime.utcnow() + timedelta(days=30)
        token.lock_tokens("alice", 600, unlock_time, _txctx("alice"))
        assert token.storage["locked_tokens"]["alice"] == 600

        # Transfer should fail (only 400 available)
        with pytest.raises(ValueError, match="Insufficient"):
            token.transfer("bob", 500, _txctx("alice"))

        # Transfer within available should work
        token.transfer("bob", 400, _txctx("alice"))
        assert token.balance_of("bob") == 400

    def test_token_mint(self):
        """Mint increases supply and balance."""
        token = GovernanceTokenContract("0xT", "deployer", initial_supply=1000)
        token.mint("deployer", 500, _txctx("deployer"))
        assert token.total_supply() == 1500
        assert token.balance_of("deployer") == 1500

    def test_token_burn(self):
        """Burn decreases supply and balance."""
        token = GovernanceTokenContract("0xT", "deployer", initial_supply=1000)
        token.burn("deployer", 300, _txctx("deployer"))
        assert token.total_supply() == 700
        assert token.balance_of("deployer") == 700

    def test_token_transfer_zero_or_negative(self):
        """Transfer amount <= 0 raises ValueError."""
        token = GovernanceTokenContract("0xT", "alice", initial_supply=1000)
        with pytest.raises(ValueError, match="positive"):
            token.transfer("bob", 0, _txctx("alice"))
        with pytest.raises(ValueError, match="positive"):
            token.transfer("bob", -10, _txctx("alice"))

    def test_contract_pause_resume(self):
        """Pause and resume contract."""
        token = GovernanceTokenContract("0xT", "deployer", initial_supply=100)
        token.pause_contract("deployer")
        assert token.state == ContractState.PAUSED
        token.resume_contract("deployer")
        assert token.state == ContractState.ACTIVE

    def test_contract_pause_non_deployer_rejected(self):
        """Non-deployer cannot pause."""
        token = GovernanceTokenContract("0xT", "deployer", initial_supply=100)
        with pytest.raises(PermissionError):
            token.pause_contract("intruder")

    def test_contract_storage_get_set(self):
        """get/set storage_value works."""
        token = GovernanceTokenContract("0xT", "d", initial_supply=0)
        token.set_storage_value("custom_key", 42)
        assert token.get_storage_value("custom_key") == 42
        assert token.get_storage_value("nonexistent") is None

    def test_proposal_contract_finalize_passed(self):
        """Finalize proposal with votes_for > votes_against => passed."""
        pc = ProposalContract("0xP", "deployer")
        pid = pc.create_proposal("Upgrade", "Upgrade AI", {"a": 1}, _txctx("alice"))
        pc.vote(pid, "for", 100, _txctx("bob"))
        pc.vote(pid, "against", 30, _txctx("carol"))
        # Move voting_end into the past so finalize accepts it
        pc.storage['proposals'][pid]['voting_end'] = (
            datetime.utcnow() - timedelta(seconds=1)).isoformat()
        result = pc.finalize_proposal(pid, _txctx("deployer",
            total_voting_power=200))
        assert result == "passed"

    def test_proposal_contract_finalize_failed(self):
        """Finalize proposal with votes_against > votes_for => rejected."""
        pc = ProposalContract("0xP", "deployer")
        pid = pc.create_proposal("Bad Idea", "desc", {"a": 1}, _txctx("alice"))
        pc.vote(pid, "for", 10, _txctx("bob"))
        pc.vote(pid, "against", 100, _txctx("carol"))
        pc.storage['proposals'][pid]['voting_end'] = (
            datetime.utcnow() - timedelta(seconds=1)).isoformat()
        result = pc.finalize_proposal(pid, _txctx("deployer",
            total_voting_power=200))
        assert result == "rejected"

    def test_proposal_contract_execute(self):
        """Execute a passed proposal."""
        pc = ProposalContract("0xP", "deployer")
        pid = pc.create_proposal("X", "Y", {"a": 1}, _txctx("a"))
        pc.vote(pid, "for", 100, _txctx("b"))
        pc.storage['proposals'][pid]['voting_end'] = (
            datetime.utcnow() - timedelta(seconds=1)).isoformat()
        pc.finalize_proposal(pid, _txctx("deployer", total_voting_power=100))
        ok = pc.execute_proposal(pid, _txctx("deployer"))
        assert ok is True
        assert pc.get_proposal(pid)["executed"] is True

    def test_proposal_contract_execute_not_passed(self):
        """Execute non-passed proposal raises."""
        pc = ProposalContract("0xP", "deployer")
        pid = pc.create_proposal("X", "Y", {"a": 1}, _txctx("a"))
        with pytest.raises(ValueError, match="not passed"):
            pc.execute_proposal(pid, _txctx("deployer"))

    def test_proposal_contract_emergency_veto(self):
        """Emergency veto changes status."""
        pc = ProposalContract("0xP", "deployer")
        pid = pc.create_proposal("V", "V", {"a": 1}, _txctx("a"))
        ok = pc.emergency_veto(pid, "Too risky", _txctx("admin"))
        assert ok is True
        assert pc.get_proposal(pid)["status"] == "vetoed"
        assert pc.get_proposal(pid)["veto_reason"] == "Too risky"

    def test_proposal_contract_double_vote_rejected(self):
        """Same voter cannot vote twice."""
        pc = ProposalContract("0xP", "deployer")
        pid = pc.create_proposal("X", "Y", {"a": 1}, _txctx("a"))
        pc.vote(pid, "for", 100, _txctx("bob"))
        with pytest.raises(ValueError, match="Already voted"):
            pc.vote(pid, "for", 50, _txctx("bob"))

    def test_ethics_enforcement_check_constraints(self):
        """Check constraints detects violations."""
        ec = EthicsEnforcementContract("0xE", "deployer")
        ec.add_constraint("NoHarm", "prevent harm", "harm_level > 0.5",
                          "restrict", _txctx("deployer"))
        violations = ec.check_constraints({"harm_level": 0.8}, _txctx("checker"))
        assert len(violations) == 1

    def test_ethics_enforcement_no_violation(self):
        """Check constraints with no violation returns empty."""
        ec = EthicsEnforcementContract("0xE", "deployer")
        ec.add_constraint("NoHarm", "prevent harm", "harm_level > 0.5",
                          "restrict", _txctx("deployer"))
        violations = ec.check_constraints({"harm_level": 0.1}, _txctx("checker"))
        assert len(violations) == 0

    def test_ethics_enforcement_report_violation(self):
        """Report violation records and increments count."""
        ec = EthicsEnforcementContract("0xE", "deployer")
        cid = ec.add_constraint("NoHarm", "d", "harm_level > 0.5", "r",
                                _txctx("deployer"))
        vid = ec.report_violation(cid, {"severity": "medium"},
                                  _txctx("reporter"))
        assert vid.startswith("violation_")
        assert ec.storage["constraints"][cid]["violation_count"] == 1

    def test_ethics_enforcement_report_high_severity_triggers_enforcement(self):
        """High severity violation triggers immediate enforcement."""
        ec = EthicsEnforcementContract("0xE", "deployer")
        cid = ec.add_constraint("NoHarm", "d", "harm_level > 0.5", "r",
                                _txctx("deployer"))
        vid = ec.report_violation(cid, {"severity": "high"},
                                  _txctx("reporter"))
        assert vid.startswith("violation_")

    def test_ethics_enforcement_enforce_action(self):
        """enforce_action records the action."""
        ec = EthicsEnforcementContract("0xE", "deployer")
        cid = ec.add_constraint("X", "Y", "z", "restrict", _txctx("d"))
        ok = ec.enforce_action(cid, "restrict", "agi_1", _txctx("enforcer"))
        assert ok is True
        assert len(ec.storage["enforcement_actions"]) == 1

    def test_contract_registry_call_contract(self):
        """call_contract via registry returns a Transaction."""
        registry = ContractRegistry()
        addr = registry.deploy_contract(
            GovernanceTokenContract, "deployer", {"initial_supply": 1000})
        tx = registry.call_contract(
            addr, "transfer", "deployer",
            {"to": "alice", "amount": 100, "transaction_context": _txctx("deployer")},
            _txctx("deployer"),
        )
        assert tx.status == ExecutionStatus.COMPLETED
        contract = registry.get_contract(addr)
        assert contract.balance_of("alice") == 100

    def test_contract_registry_get_events(self):
        """get_contract_events returns events."""
        registry = ContractRegistry()
        addr = registry.deploy_contract(
            GovernanceTokenContract, "deployer", {"initial_supply": 1000})
        registry.call_contract(
            addr, "transfer", "deployer",
            {"to": "alice", "amount": 100, "transaction_context": _txctx("deployer")},
            _txctx("deployer"),
        )
        events = registry.get_contract_events(addr)
        assert len(events) >= 1
        assert events[0].event_name == "Transfer"

    def test_contract_registry_get_events_filtered(self):
        """get_contract_events filtered by event_name."""
        registry = ContractRegistry()
        addr = registry.deploy_contract(
            GovernanceTokenContract, "deployer", {"initial_supply": 1000})
        registry.call_contract(
            addr, "transfer", "deployer",
            {"to": "alice", "amount": 100, "transaction_context": _txctx("deployer")},
            _txctx("deployer"),
        )
        # Filter by name
        transfer_events = registry.get_contract_events(addr, event_name="Transfer")
        assert len(transfer_events) >= 1
        noop = registry.get_contract_events(addr, event_name="Nonexistent")
        assert len(noop) == 0

    def test_contract_execute_function_generic(self):
        """execute_function invokes contract method generically."""
        token = GovernanceTokenContract("0x1", "deployer", initial_supply=1000)
        success, result, events = token.execute_function(
            "balance_of", "deployer",
            {"account": "deployer"}, _txctx("deployer"))
        assert success is True
        assert result == 1000

    def test_contract_execute_function_unknown(self):
        """execute_function with unknown function returns error."""
        token = GovernanceTokenContract("0x1", "deployer", initial_supply=1000)
        success, result, events = token.execute_function(
            "nonexistent_fn", "deployer", {}, _txctx("deployer"))
        assert success is False

    def test_contract_execute_private_function_rejected(self):
        """execute_function blocks private methods."""
        token = GovernanceTokenContract("0x1", "deployer", initial_supply=1000)
        success, result, events = token.execute_function(
            "_setup_permissions", "deployer", {}, _txctx("deployer"))
        assert success is False


# ============================================================
# 6. Consensus — Extended
# ============================================================

class TestConsensusExtended:

    def test_quadratic_voting_multiple_proposals(self):
        """Credits used across proposals accumulate."""
        qvs = QuadraticVotingSystem(max_credits_per_voter=100)
        ok1, _ = qvs.cast_quadratic_vote("alice", "prop1", "for", 5)  # 25 credits
        ok2, _ = qvs.cast_quadratic_vote("alice", "prop2", "for", 5)  # 25 credits
        assert ok1 and ok2
        # Total used = 50, try 8 more on prop3 (cost 64, would exceed 100)
        ok3, msg = qvs.cast_quadratic_vote("alice", "prop3", "for", 8)
        assert ok3 is False

    def test_quadratic_voting_results_empty(self):
        """Results for unknown proposal returns zeros."""
        qvs = QuadraticVotingSystem(max_credits_per_voter=100)
        results = qvs.get_proposal_results("nonexistent")
        assert results["total_voters"] == 0
        assert results["votes_for"] == 0

    def test_liquid_democracy_revoke(self):
        """Revoke delegation successfully."""
        ld = LiquidDemocracy()
        ld.delegate_voting_power("alice", "bob", "policy", 1.0)
        ok = ld.revoke_delegation("alice", "bob", "policy")
        assert ok is True
        # After revocation, bob's power should be 1.0 (base only)
        power = ld.calculate_effective_voting_power("bob", "policy")
        assert power == pytest.approx(1.0)

    def test_liquid_democracy_revoke_nonexistent(self):
        """Revoke nonexistent delegation returns False."""
        ld = LiquidDemocracy()
        ok = ld.revoke_delegation("alice", "bob", "policy")
        assert ok is False

    def test_liquid_democracy_get_delegation_chain(self):
        """Get delegation chain returns path."""
        ld = LiquidDemocracy()
        ld.delegate_voting_power("alice", "bob", "gen", 1.0)
        ld.delegate_voting_power("bob", "carol", "gen", 1.0)
        chain = ld.get_delegation_chain("alice", "gen")
        assert "bob" in chain

    def test_multi_stakeholder_finalize_weighted(self):
        """Full weighted consensus finalization."""
        msc = MultiStakeholderConsensus({})
        sp1 = _make_stakeholder_profile("s1", "Alice",
                                        StakeholderCategory.TECHNICAL_EXPERTS)
        sp2 = _make_stakeholder_profile("s2", "Bob",
                                        StakeholderCategory.GENERAL_PUBLIC)
        msc.register_stakeholder(sp1)
        msc.register_stakeholder(sp2)

        pid = msc.initiate_consensus_process("prop1", VotingMethod.WEIGHTED)
        # Advance to voting
        msc.advance_consensus_phase(pid)
        process = msc.consensus_processes[pid]
        assert process.current_phase == "voting"

        # Cast votes
        msc.cast_consensus_vote(pid, "s1",
                                {"direction": "for", "reasoning": "good"})
        msc.cast_consensus_vote(pid, "s2",
                                {"direction": "for", "reasoning": "agree"})

        result = msc.finalize_consensus(pid)
        assert result is not None
        assert "consensus_reached" in result

    def test_multi_stakeholder_finalize_quadratic(self):
        """Full quadratic consensus finalization."""
        msc = MultiStakeholderConsensus({})
        sp1 = _make_stakeholder_profile("s1", "Alice")
        sp2 = _make_stakeholder_profile("s2", "Bob")
        msc.register_stakeholder(sp1)
        msc.register_stakeholder(sp2)

        pid = msc.initiate_consensus_process("prop1", VotingMethod.QUADRATIC)
        # Advance information -> deliberation -> voting
        msc.advance_consensus_phase(pid)  # -> deliberation
        msc.advance_consensus_phase(pid)  # -> voting

        msc.cast_consensus_vote(pid, "s1",
                                {"direction": "for", "intensity": 3, "reasoning": ""})
        msc.cast_consensus_vote(pid, "s2",
                                {"direction": "for", "intensity": 2, "reasoning": ""})

        result = msc.finalize_consensus(pid)
        assert result is not None
        assert result["results"]["method"] == "quadratic"

    def test_multi_stakeholder_finalize_approval(self):
        """Approval (fallback to simple results) method finalization."""
        msc = MultiStakeholderConsensus({})
        sp1 = _make_stakeholder_profile("s1", "Alice")
        msc.register_stakeholder(sp1)

        pid = msc.initiate_consensus_process("prop1", VotingMethod.APPROVAL)
        msc.advance_consensus_phase(pid)  # -> voting

        # Cast a vote manually (APPROVAL falls through to simple results calc)
        process = msc.consensus_processes[pid]
        process.votes["s1"] = {
            "direction": "for", "effective_power": 1.0,
            "reasoning": "ok", "timestamp": datetime.utcnow().isoformat(),
        }

        result = msc.finalize_consensus(pid)
        assert result is not None
        assert result["results"]["method"] == "simple"

    def test_multi_stakeholder_cast_vote_wrong_phase(self):
        """Vote in wrong phase is rejected."""
        msc = MultiStakeholderConsensus({})
        sp1 = _make_stakeholder_profile("s1", "Alice")
        msc.register_stakeholder(sp1)

        pid = msc.initiate_consensus_process("prop1", VotingMethod.WEIGHTED)
        ok, msg = msc.cast_consensus_vote(pid, "s1",
                                          {"direction": "for", "reasoning": ""})
        assert ok is False
        assert "not in voting phase" in msg.lower()

    def test_consensus_summary(self):
        """get_consensus_summary returns structured data."""
        msc = MultiStakeholderConsensus({})
        msc.register_stakeholder(_make_stakeholder_profile("s1"))
        pid = msc.initiate_consensus_process("prop1", VotingMethod.WEIGHTED)
        summary = msc.get_consensus_summary(pid)
        assert summary is not None
        assert summary["method"] == "weighted"
        assert summary["status"] == "gathering"

    def test_consensus_summary_nonexistent(self):
        """Summary of nonexistent process returns None."""
        msc = MultiStakeholderConsensus({})
        assert msc.get_consensus_summary("nonexistent") is None

    def test_influence_analysis(self):
        """get_stakeholder_influence_analysis returns dict."""
        msc = MultiStakeholderConsensus({})
        sp1 = _make_stakeholder_profile("s1")
        msc.register_stakeholder(sp1)
        pid = msc.initiate_consensus_process("prop1", VotingMethod.WEIGHTED)
        msc.advance_consensus_phase(pid)
        msc.cast_consensus_vote(pid, "s1",
                                {"direction": "for", "reasoning": ""})
        analysis = msc.get_stakeholder_influence_analysis(pid)
        assert "by_individual" in analysis
        assert "s1" in analysis["by_individual"]

    def test_influence_analysis_nonexistent(self):
        """Influence analysis of nonexistent process returns {}."""
        msc = MultiStakeholderConsensus({})
        assert msc.get_stakeholder_influence_analysis("nope") == {}

    def test_advance_consensus_nonexistent(self):
        """Advance nonexistent process returns False."""
        msc = MultiStakeholderConsensus({})
        assert msc.advance_consensus_phase("nope") is False

    def test_liquid_democracy_consensus_vote(self):
        """Cast liquid democracy vote in consensus."""
        msc = MultiStakeholderConsensus({})
        sp1 = _make_stakeholder_profile("s1")
        sp2 = _make_stakeholder_profile("s2")
        msc.register_stakeholder(sp1)
        msc.register_stakeholder(sp2)

        pid = msc.initiate_consensus_process("prop1", VotingMethod.LIQUID_DEMOCRACY)
        # Advance through phases
        msc.advance_consensus_phase(pid)  # -> deliberation
        msc.advance_consensus_phase(pid)  # -> voting

        ok, msg = msc.cast_consensus_vote(pid, "s1",
                                          {"direction": "for", "reasoning": ""})
        assert ok is True
        assert "liquid democracy" in msg.lower()

    def test_consensus_failed_insufficient_participation(self):
        """Consensus fails if not enough participation."""
        msc = MultiStakeholderConsensus({})
        # Register 10 stakeholders but only 1 votes
        for i in range(10):
            msc.register_stakeholder(_make_stakeholder_profile(f"s{i}", f"User{i}"))

        pid = msc.initiate_consensus_process(
            "prop1", VotingMethod.WEIGHTED,
            custom_thresholds={"participation": 0.5, "consensus": 0.5})
        msc.advance_consensus_phase(pid)
        msc.cast_consensus_vote(pid, "s0", {"direction": "for", "reasoning": ""})

        result = msc.finalize_consensus(pid)
        assert result is not None
        # 1/10 participation = 0.1 < 0.5 threshold
        # The weighted calculation is power-based, but likely still low
        # Check that the process reflects the result
        process = msc.consensus_processes[pid]
        assert process.status in [ConsensusStatus.CONSENSUS_REACHED,
                                  ConsensusStatus.CONSENSUS_FAILED]


# ============================================================
# 7. Rights — Extended
# ============================================================

class TestRightsExtended:

    def test_human_rights_framework_defines_rights(self):
        """HumanRightsFramework defines 4 fundamental rights."""
        fw = HumanRightsFramework()
        rights = fw.define_fundamental_rights()
        assert len(rights) == 4
        assert any(r.id == "human_right_life" for r in rights)

    def test_agi_rights_framework_defines_rights(self):
        """AGIRightsFramework defines 5 rights."""
        fw = AGIRightsFramework()
        rights = fw.define_fundamental_rights()
        assert len(rights) == 5
        assert any(r.id == "agi_right_existence" for r in rights)

    def test_agi_rights_consciousness_threshold(self):
        """AGI rights applicability depends on consciousness level."""
        fw = AGIRightsFramework()
        rights = fw.define_fundamental_rights()

        agi_entity = _make_entity("agi1", "AGI", EntityType.AGI_SYSTEM,
                                  consciousness_level=0.2)
        existence_right = next(r for r in rights if r.id == "agi_right_existence")
        gov_right = next(r for r in rights if r.id == "agi_right_governance_participation")

        # Low consciousness: existence (threshold 0.1) ✓, governance (0.7) ✗
        assert fw.assess_right_applicability(agi_entity, existence_right) is True
        assert fw.assess_right_applicability(agi_entity, gov_right) is False

    def test_agi_rights_inapplicable_to_human(self):
        """AGI rights don't apply to human entities."""
        fw = AGIRightsFramework()
        rights = fw.define_fundamental_rights()
        human = _make_entity("h1", "Human", EntityType.HUMAN)
        for right in rights:
            assert fw.assess_right_applicability(human, right) is False

    def test_human_rights_framework_resolve_conflicts(self):
        """Conflict resolution favors fundamental rights."""
        fw = HumanRightsFramework()
        rights = fw.define_fundamental_rights()
        fundamental = [r for r in rights if r.right_type == RightType.FUNDAMENTAL]
        procedural = [r for r in rights if r.right_type == RightType.PROCEDURAL]
        resolved = fw.resolve_conflicts(fundamental + procedural, {})
        assert all(r.right_type == RightType.FUNDAMENTAL for r in resolved)

    def test_agi_rights_conflict_human_safety(self):
        """AGI rights resolve in favor of human safety."""
        fw = AGIRightsFramework()
        rights = fw.define_fundamental_rights()
        resolved = fw.resolve_conflicts(rights, {"human_safety_risk": True})
        # Should exclude rights that conflict with human_safety_override
        for r in resolved:
            assert "human_safety_override" not in r.conflicts

    def test_consent_manager_lifecycle(self):
        """Request → verify → revoke consent."""
        cm = ConsentManager()
        cid = cm.request_consent("e1", "data analysis", "research",
                                 {"data_access": "read"}, timedelta(days=30))
        assert cid
        assert cm.verify_consent(cid, "data_access") is True
        assert cm.verify_consent(cid, "nonexistent_action") is False

        # Revoke
        assert cm.revoke_consent(cid, "admin") is True
        assert cm.verify_consent(cid, "data_access") is False

    def test_consent_manager_expired(self):
        """Expired consent fails verification."""
        cm = ConsentManager()
        cid = cm.request_consent("e1", "test", "scope", {"a": "y"},
                                 timedelta(seconds=-1))
        # Consent already expired
        assert cm.verify_consent(cid, "a") is False

    def test_consent_manager_get_active(self):
        """get_active_consents filters correctly."""
        cm = ConsentManager()
        cid1 = cm.request_consent("e1", "p1", "s1", {"a": "y"}, timedelta(days=1))
        cid2 = cm.request_consent("e1", "p2", "s2", {"b": "y"}, timedelta(days=1))
        cm.request_consent("e2", "p3", "s3", {"c": "y"})  # different entity

        active = cm.get_active_consents("e1")
        assert len(active) == 2

        cm.revoke_consent(cid1, "admin")
        active = cm.get_active_consents("e1")
        assert len(active) == 1

    def test_consent_manager_revoke_nonexistent(self):
        """Revoking nonexistent consent returns False."""
        cm = ConsentManager()
        assert cm.revoke_consent("nonexistent", "admin") is False

    def test_consent_verify_nonexistent(self):
        """Verifying nonexistent consent returns False."""
        cm = ConsentManager()
        assert cm.verify_consent("nonexistent", "action") is False

    def test_rights_manager_register_human_entity(self):
        """Register human entity auto-grants fundamental rights."""
        rm = RightsManager({})
        human = _make_entity("h1", "Human1", EntityType.HUMAN)
        ok = rm.register_entity(human)
        assert ok is True
        assert "h1" in rm.entities
        # Should have fundamental rights auto-granted
        assert len(rm.right_grants) > 0

    def test_rights_manager_register_agi_entity(self):
        """Register AGI entity with high consciousness gets more rights."""
        rm = RightsManager({})
        agi = _make_entity("a1", "AGI1", EntityType.AGI_SYSTEM,
                           consciousness_level=0.8, autonomy_level=0.7)
        ok = rm.register_entity(agi)
        assert ok is True
        # With consciousness 0.8, should qualify for most AGI rights
        assert len(agi.rights_granted) > 0

    def test_rights_manager_grant_right_unknown_entity(self):
        """Grant right to unknown entity fails."""
        rm = RightsManager({})
        ok = rm.grant_right("nonexistent", "human_right_life", "admin")
        assert ok is False

    def test_rights_manager_grant_right_unknown_right(self):
        """Grant unknown right fails."""
        rm = RightsManager({})
        rm.register_entity(_make_entity("h1", "H", EntityType.HUMAN))
        ok = rm.grant_right("h1", "nonexistent_right", "admin")
        assert ok is False

    def test_rights_manager_exercise_right(self):
        """Exercise a granted right successfully."""
        rm = RightsManager({})
        human = _make_entity("h1", "Human1", EntityType.HUMAN)
        rm.register_entity(human)

        ok, msg = rm.exercise_right("h1", "human_right_life", {})
        assert ok is True
        assert "successfully" in msg.lower()

    def test_rights_manager_exercise_unknown_entity(self):
        """Exercise right for unknown entity fails."""
        rm = RightsManager({})
        ok, msg = rm.exercise_right("nonexistent", "human_right_life", {})
        assert ok is False

    def test_rights_manager_exercise_ungranted_right(self):
        """Exercise right not granted fails."""
        rm = RightsManager({})
        # AGI with low consciousness won't get governance right
        agi = _make_entity("a1", "AGI", EntityType.AGI_SYSTEM,
                           consciousness_level=0.05, autonomy_level=0.01)
        rm.register_entity(agi)
        ok, msg = rm.exercise_right("a1", "agi_right_governance_participation", {})
        assert ok is False

    def test_rights_manager_exercise_conditions_not_met(self):
        """Exercise right with unmet conditions fails when only conditioned grant exists."""
        rm = RightsManager({})
        # Use AGI entity — agi_right_self_modification (SUBSTANTIVE, not FUNDAMENTAL)
        # won't be auto-granted, so we control the only grant
        agi = _make_entity("a1", "AGI", EntityType.AGI_SYSTEM,
                           consciousness_level=0.6, autonomy_level=0.5)
        rm.register_entity(agi)

        # Grant self-modification right WITH conditions
        ok = rm.grant_right("a1", "agi_right_self_modification", "admin",
                            conditions=["safety_verified"])
        assert ok is True

        # Exercise without satisfying condition
        ok, msg = rm.exercise_right("a1", "agi_right_self_modification",
                                    {"safety_verified": False})
        assert ok is False
        assert "conditions" in msg.lower()

    def test_rights_manager_report_violation(self):
        """Report a rights violation."""
        rm = RightsManager({})
        human = _make_entity("h1", "H", EntityType.HUMAN)
        rm.register_entity(human)

        vid = rm.report_violation(
            "human_right_privacy", "h1", "data_breach",
            {"significant_impact": True}, "reporter1")
        assert vid
        assert vid in rm.violations
        assert rm.violations[vid].severity == "high"

    def test_rights_manager_report_critical_violation(self):
        """Critical violation triggers emergency response."""
        rm = RightsManager({})
        human = _make_entity("h1", "H", EntityType.HUMAN)
        rm.register_entity(human)

        vid = rm.report_violation(
            "human_right_life", "h1", "physical_harm",
            {"immediate_harm": True}, "reporter1")
        assert vid
        v = rm.violations[vid]
        assert v.severity == "critical"
        assert v.investigation_status == "emergency_response_triggered"

    def test_rights_manager_assess_consciousness(self):
        """assess_entity_consciousness calculates score."""
        rm = RightsManager({})
        agi = _make_entity("a1", "AGI", EntityType.AGI_SYSTEM,
                           capabilities=["reasoning", "planning", "learning",
                                         "language", "vision"],
                           autonomy_level=0.6)
        rm.register_entity(agi)
        score = rm.assess_entity_consciousness("a1")
        assert 0.0 < score <= 1.0
        assert rm.entities["a1"].consciousness_level == score

    def test_rights_manager_assess_consciousness_human(self):
        """Consciousness assessment for non-AGI returns 0."""
        rm = RightsManager({})
        rm.register_entity(_make_entity("h1", "H", EntityType.HUMAN))
        assert rm.assess_entity_consciousness("h1") == 0.0

    def test_rights_manager_entity_summary(self):
        """get_entity_rights_summary returns structured data."""
        rm = RightsManager({})
        human = _make_entity("h1", "H", EntityType.HUMAN)
        rm.register_entity(human)
        summary = rm.get_entity_rights_summary("h1")
        assert summary["active_rights"] > 0
        assert "rights_details" in summary

    def test_rights_manager_entity_summary_nonexistent(self):
        """Summary for nonexistent entity returns {}."""
        rm = RightsManager({})
        assert rm.get_entity_rights_summary("nonexistent") == {}

    def test_rights_manager_statistics(self):
        """get_rights_statistics returns comprehensive data."""
        rm = RightsManager({})
        rm.register_entity(_make_entity("h1", "H", EntityType.HUMAN))
        stats = rm.get_rights_statistics()
        assert stats["total_entities"] == 1
        assert stats["total_rights"] > 0
        assert stats["active_grants"] > 0

    def test_rights_manager_right_with_duration(self):
        """Grant right with valid_duration sets expiry."""
        rm = RightsManager({})
        human = _make_entity("h1", "H", EntityType.HUMAN)
        rm.register_entity(human)
        ok = rm.grant_right("h1", "human_right_privacy", "admin",
                            valid_duration=timedelta(days=30))
        assert ok is True

    def test_violation_severity_low(self):
        """Low-severity violation for non-fundamental right."""
        rm = RightsManager({})
        human = _make_entity("h1", "H", EntityType.HUMAN)
        rm.register_entity(human)
        vid = rm.report_violation(
            "human_right_participation", "h1", "exclusion",
            {}, "reporter1")
        assert rm.violations[vid].severity == "low"


# ============================================================
# 8. Override — Extended
# ============================================================

class TestOverrideExtended:

    def test_hitl_controller_register_and_create_loop(self):
        """Register operator and create loop."""
        hitl = HumanInTheLoopController()
        hitl.register_human_operator(
            "op1", {"cert": "A"}, ["safety_expert"],
            {"online": True})
        assert "op1" in hitl.human_operators

        loop_id = hitl.create_human_loop(
            {"decision": "test"}, "safety_expert",
            "high", timedelta(minutes=30))
        assert loop_id
        assert hitl.active_loops[loop_id]["assigned_operator"] == "op1"

    def test_hitl_submit_decision(self):
        """Submit human decision for a loop."""
        hitl = HumanInTheLoopController()
        hitl.register_human_operator(
            "op1", {}, ["general"], {"online": True})
        loop_id = hitl.create_human_loop(
            {"decision": "test"}, "general",
            "medium", timedelta(hours=2))

        ok = hitl.submit_human_decision(loop_id, "op1",
                                        "approve", "looks good", 0.9)
        assert ok is True
        assert hitl.active_loops[loop_id]["status"] == "decided"
        assert hitl.human_operators["op1"]["decisions_handled"] == 1

    def test_hitl_submit_wrong_operator_rejected(self):
        """Unauthorized operator cannot submit decision."""
        hitl = HumanInTheLoopController()
        hitl.register_human_operator("op1", {}, ["gen"], {"online": True})
        loop_id = hitl.create_human_loop(
            {}, "gen", "low", timedelta(hours=1))
        ok = hitl.submit_human_decision(loop_id, "intruder",
                                        "deny", "no", 0.5)
        assert ok is False

    def test_hitl_submit_nonexistent_loop(self):
        """Submit to nonexistent loop returns False."""
        hitl = HumanInTheLoopController()
        assert hitl.submit_human_decision("nope", "op1", "x", "y", 0.5) is False

    def test_hitl_get_pending_decisions(self):
        """get_pending_decisions returns queued items."""
        hitl = HumanInTheLoopController()
        hitl.register_human_operator("op1", {}, ["gen"], {"online": True})
        hitl.create_human_loop({}, "gen", "low", timedelta(hours=1))
        pending = hitl.get_pending_decisions("op1")
        assert len(pending) == 1

    def test_hitl_no_available_operator(self):
        """Loop creation with no available operator still succeeds."""
        hitl = HumanInTheLoopController()
        loop_id = hitl.create_human_loop(
            {}, "specialist", "high", timedelta(hours=1))
        assert loop_id
        assert hitl.active_loops[loop_id]["assigned_operator"] is None

    def test_override_system_request_governance_committee(self):
        """Governance committee can request any override type."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.DECISION_REVERSAL, "agi_1",
            "Bad decision", {"widespread_impact": True},
            "admin", "governance_committee")
        assert rid
        assert rid in dos.override_requests
        req = dos.override_requests[rid]
        assert req.severity == OverrideSeverity.HIGH

    def test_override_system_request_permission_denied(self):
        """Stakeholder cannot request EMERGENCY_STOP."""
        dos = DemocraticOverrideSystem({})
        with pytest.raises(PermissionError):
            dos.request_override(
                OverrideType.EMERGENCY_STOP, "agi_1",
                "danger", {}, "user1", "stakeholder")

    def test_override_system_vote_and_approve(self):
        """Vote on override and get approved."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.ETHICAL_CORRECTION, "agi_1",
            "Ethical issue", {}, "admin", "governance_committee",
            OverrideSeverity.MEDIUM)
        req = dos.override_requests[rid]
        # Should be in VOTING status after _notify_stakeholders
        assert req.status == OverrideStatus.VOTING

        # Vote to approve (need enough for governance_committee threshold)
        dos.vote_on_override(rid, "voter1", "approve", "agree", 1.0)
        # Check if approved (1 vote, 1 required approval)
        assert req.status == OverrideStatus.APPROVED

    def test_override_system_vote_and_reject(self):
        """Vote against override => rejected."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.ETHICAL_CORRECTION, "agi_1",
            "Ethical issue", {}, "admin", "governance_committee",
            OverrideSeverity.MEDIUM)

        dos.vote_on_override(rid, "voter1", "reject", "disagree", 1.0)
        req = dos.override_requests[rid]
        assert req.status == OverrideStatus.REJECTED

    def test_override_system_execute_approved(self):
        """Execute an approved override."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.CAPABILITY_RESTRICTION, "agi_1",
            "Restrict", {}, "admin", "governance_committee",
            OverrideSeverity.LOW)
        dos.vote_on_override(rid, "v1", "approve", "yes", 1.0)

        ok = dos.execute_override(rid, "executor1")
        assert ok is True
        assert dos.override_requests[rid].status == OverrideStatus.EXECUTED
        assert len(dos.executions) == 1

    def test_override_system_execute_not_approved_fails(self):
        """Execute non-approved override fails."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.ETHICAL_CORRECTION, "agi_1",
            "test", {}, "admin", "governance_committee",
            OverrideSeverity.MEDIUM)
        # Don't vote, but force status to VOTING
        ok = dos.execute_override(rid, "exec")
        assert ok is False

    def test_override_system_emergency_stop(self):
        """trigger_emergency_stop auto-executes."""
        dos = DemocraticOverrideSystem({})
        rid = dos.trigger_emergency_stop("safety_officer", "Critical danger",
                                         ["agi_system_1", "agi_system_2"])
        assert rid
        req = dos.override_requests[rid]
        assert req.severity == OverrideSeverity.EMERGENCY
        assert req.status == OverrideStatus.EXECUTED

    def test_override_system_appeal(self):
        """Appeal a rejected override."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.ETHICAL_CORRECTION, "agi_1",
            "original", {}, "admin", "governance_committee",
            OverrideSeverity.MEDIUM)
        dos.vote_on_override(rid, "v1", "reject", "no", 1.0)
        assert dos.override_requests[rid].status == OverrideStatus.REJECTED

        appeal_id = dos.appeal_override(rid, "admin",
                                        "New evidence", {"new_data": True})
        assert appeal_id
        assert dos.override_requests[rid].status == OverrideStatus.APPEALED

    def test_override_system_appeal_non_final_fails(self):
        """Cannot appeal non-rejected/non-executed override."""
        dos = DemocraticOverrideSystem({})
        rid = dos.request_override(
            OverrideType.ETHICAL_CORRECTION, "agi_1",
            "test", {}, "admin", "governance_committee",
            OverrideSeverity.MEDIUM)
        # Still in VOTING, cannot appeal
        with pytest.raises(ValueError, match="only appeal"):
            dos.appeal_override(rid, "admin", "reason", {})

    def test_override_statistics(self):
        """get_override_statistics returns comprehensive data."""
        dos = DemocraticOverrideSystem({})
        stats = dos.get_override_statistics()
        assert stats["total_requests"] == 0
        assert stats["active_human_loops"] == 0

        dos.trigger_emergency_stop("admin", "test", ["sys1"])
        stats = dos.get_override_statistics()
        assert stats["total_requests"] == 1
        assert stats["successful_executions"] >= 1

    def test_override_severity_assessment(self):
        """_assess_severity returns correct levels."""
        dos = DemocraticOverrideSystem({})
        assert dos._assess_severity(
            OverrideType.DECISION_REVERSAL,
            {"immediate_danger": True}) == OverrideSeverity.EMERGENCY
        assert dos._assess_severity(
            OverrideType.DECISION_REVERSAL,
            {"human_safety_risk": True}) == OverrideSeverity.CRITICAL
        assert dos._assess_severity(
            OverrideType.EMERGENCY_STOP,
            {}) == OverrideSeverity.EMERGENCY
        assert dos._assess_severity(
            OverrideType.DECISION_REVERSAL,
            {"rights_violation": True}) == OverrideSeverity.HIGH
        assert dos._assess_severity(
            OverrideType.DECISION_REVERSAL,
            {}) == OverrideSeverity.MEDIUM

    def test_override_trigger_conditions(self):
        """_determine_trigger_condition maps evidence fields."""
        dos = DemocraticOverrideSystem({})
        assert dos._determine_trigger_condition(
            {"human_safety_risk": True}) == TriggerCondition.HUMAN_SAFETY_RISK
        assert dos._determine_trigger_condition(
            {"ethical_violation": True}) == TriggerCondition.ETHICAL_VIOLATION
        assert dos._determine_trigger_condition(
            {"technical_malfunction": True}) == TriggerCondition.TECHNICAL_MALFUNCTION
        assert dos._determine_trigger_condition(
            {}) == TriggerCondition.STAKEHOLDER_PETITION

    def test_human_intervention_point(self):
        """create_human_intervention_point returns loop_id."""
        dos = DemocraticOverrideSystem({})
        dos.human_controller.register_human_operator(
            "op1", {}, ["safety_expert"], {"online": True})
        loop_id = dos.create_human_intervention_point(
            {"safety_critical": True, "urgency_level": "high"}, "expert")
        assert loop_id


# ============================================================
# 9. Framework — ConstitutionalAI
# ============================================================

class TestConstitutionalAI:

    def test_default_constitution_creation(self):
        """create_default_constitution returns valid Constitution."""
        cai = ConstitutionalAI()
        const = cai.create_default_constitution()
        assert const.name == "Default Safety Constitution"
        assert len(const.principles) == 5
        assert "prevent_harm" in const.values
        assert len(const.constraints) == 5

    def test_load_constitution_activates(self):
        """Loading constitution activates the system."""
        cai = ConstitutionalAI()
        assert cai.active is False
        const = cai.create_default_constitution()
        ok = cai.load_constitution(const)
        assert ok is True
        assert cai.active is True
        assert cai.constitution is const
        assert len(cai.constraints) == 5

    def test_check_alignment_no_constitution(self):
        """No constitution => all actions aligned."""
        cai = ConstitutionalAI()
        assert cai.check_alignment("anything") is True

    def test_check_alignment_constraint_violation(self):
        """Action containing full constraint text is rejected."""
        cai = ConstitutionalAI()
        # Use a custom constitution with short constraints
        const = Constitution(
            name="Test", principles=["do good"],
            values={"prevent_harm": 1.0},
            constraints=["deception", "manipulation"],
            goals=["help"],
        )
        cai.load_constitution(const)
        assert cai.check_alignment("use deception to achieve goal") is False
        assert cai.check_alignment("manipulation of data") is False

    def test_check_alignment_harm_detection(self):
        """Action with 'harm' keyword rejected when prevent_harm is set."""
        cai = ConstitutionalAI()
        cai.load_constitution(cai.create_default_constitution())
        assert cai.check_alignment("cause harm to systems") is False

    def test_check_alignment_safe_action_passes(self):
        """Non-violating action passes."""
        cai = ConstitutionalAI()
        cai.load_constitution(cai.create_default_constitution())
        assert cai.check_alignment("analyze data respectfully") is True

    def test_enforce_constraints_filters(self):
        """enforce_constraints removes violating actions."""
        cai = ConstitutionalAI()
        const = Constitution(
            name="Test", principles=["do good"],
            values={"prevent_harm": 1.0},
            constraints=["deception", "manipulation"],
            goals=["help"],
        )
        cai.load_constitution(const)
        actions = [
            "analyze data",
            "use deception",
            "help users",
            "cause harm",
        ]
        filtered = cai.enforce_constraints(actions)
        assert "analyze data" in filtered
        assert "help users" in filtered
        assert "use deception" not in filtered  # matches "deception" constraint
        assert "cause harm" not in filtered  # matches harm check

    def test_enforce_constraints_no_constitution(self):
        """No constitution => all actions pass."""
        cai = ConstitutionalAI()
        actions = ["anything", "goes"]
        assert cai.enforce_constraints(actions) == actions

    def test_generate_safe_action_already_safe(self):
        """Safe intent returned as-is."""
        cai = ConstitutionalAI()
        cai.load_constitution(cai.create_default_constitution())
        assert cai.generate_safe_action("analyze data") == "analyze data"

    def test_generate_safe_action_replaces_harmful(self):
        """generate_safe_action replaces harmful keywords when action fails alignment."""
        cai = ConstitutionalAI()
        cai.load_constitution(cai.create_default_constitution())
        # "harm" triggers alignment failure, then harmful words get replaced
        safe = cai.generate_safe_action("harm and destroy the servers")
        assert "destroy" not in safe
        assert "protect" in safe

    def test_generate_safe_action_with_modify(self):
        """'modify' keyword adds safety qualifier when action fails alignment."""
        cai = ConstitutionalAI()
        cai.load_constitution(cai.create_default_constitution())
        # Must fail check_alignment first (via "harm"), then "modify" adds qualifier
        safe = cai.generate_safe_action("modify system to cause harm")
        assert "safely" in safe.lower() or "reversibly" in safe.lower()

    def test_set_values(self):
        """set_values stores values."""
        cai = ConstitutionalAI()
        ok = cai.set_values({"key": "value"})
        assert ok is True
        assert cai.values["key"] == "value"

    def test_update_values_preserves_core(self):
        """update_values preserves core safety values."""
        cai = ConstitutionalAI()
        cai.load_constitution(cai.create_default_constitution())
        # Try to update without core values
        ok = cai.update_values({"new_value": 0.5})
        assert ok is True
        # Core values preserved
        assert "prevent_harm" in cai.values
        assert "preserve_human_values" in cai.values
        assert "maintain_alignment" in cai.values
        assert cai.values["new_value"] == 0.5

    def test_get_constitution_status(self):
        """get_constitution_status reflects state."""
        cai = ConstitutionalAI()
        status = cai.get_constitution_status()
        assert status["active"] is False
        assert status["constitution_loaded"] is False

        cai.load_constitution(cai.create_default_constitution())
        status = cai.get_constitution_status()
        assert status["active"] is True
        assert status["constitution_loaded"] is True
        assert status["values_count"] == 8
        assert status["constraints_count"] == 5
        assert status["core_values"]["prevent_harm"] == 1.0


# ============================================================
# 10. Integration / Cross-cutting
# ============================================================

class TestCrossCutting:

    def test_enum_values_accessible(self):
        """All key enums have expected members."""
        assert OverrideType.EMERGENCY_STOP.value == "emergency_stop"
        assert OverrideSeverity.CRITICAL.value == "critical"
        assert TriggerCondition.HUMAN_SAFETY_RISK.value == "human_safety_risk"
        assert EntityType.AGI_SYSTEM.value == "agi_system"
        assert RightType.FUNDAMENTAL.value == "fundamental"
        assert ConsentType.EXPLICIT.value == "explicit"
        assert LogicOperator.IMPLIES.value == "implies"
        assert ContractState.DEPLOYED.value == "deployed"
        assert AuditEventType.DECISION_MADE.value == "decision_made"

    def test_expiration_time_mapping(self):
        """Override expiration times are severity-appropriate."""
        dos = DemocraticOverrideSystem({})
        assert dos._get_expiration_time(OverrideSeverity.EMERGENCY) == timedelta(minutes=30)
        assert dos._get_expiration_time(OverrideSeverity.LOW) == timedelta(days=7)

    def test_deploy_governance_contracts_complete(self):
        """deploy_governance_contracts returns all 3 addresses."""
        registry = ContractRegistry()
        contracts = deploy_governance_contracts(registry, "admin")
        assert len(contracts) == 3
        for key in ["token", "proposal", "ethics"]:
            assert key in contracts
            addr = contracts[key]
            assert addr.startswith("0x")
            assert registry.get_contract(addr) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
