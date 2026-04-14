// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/RingsBridge.sol";
import "../contracts/BridgedToken.sol";

// ─── Mock verifier that always returns true ────────────────────────────
contract MockVerifier is IGroth16Verifier {
    bool public shouldPass = true;

    function setResult(bool _result) external {
        shouldPass = _result;
    }

    function verifyProof(
        bytes calldata,
        bytes32[] calldata
    ) external view override returns (bool) {
        return shouldPass;
    }
}

// ─── Mock ERC20 for deposit tests ──────────────────────────────────────
contract MockERC20 is IERC20 {
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    uint256 private _totalSupply;

    function mint(address to, uint256 amount) external {
        _balances[to] += amount;
        _totalSupply += amount;
    }

    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 amount) external override returns (bool) {
        _balances[msg.sender] -= amount;
        _balances[to] += amount;
        return true;
    }

    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        _allowances[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        _allowances[from][msg.sender] -= amount;
        _balances[from] -= amount;
        _balances[to] += amount;
        return true;
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  RingsBridge Test Suite
// ═══════════════════════════════════════════════════════════════════════

contract RingsBridgeTest is Test {
    // ── Re-declare events so we can use `emit` in expectEmit ────────
    event Deposited(
        uint256 indexed nonce, address indexed depositor, bytes32 indexed ringsDID,
        uint256 amount, address token, uint256 timestamp
    );
    event Withdrawn(
        uint256 indexed nonce, address indexed recipient, bytes32 indexed ringsDID,
        uint256 amount, address token, uint256 timestamp
    );
    event SyncCommitteeUpdated(bytes32 indexed newRoot, uint64 indexed slot, address updater);
    event RateLimitUpdated(uint256 newDailyLimit, uint256 newPerTxLimit, address updater);
    event EmergencyPaused(address indexed guardian);

    RingsBridge public bridge;
    MockVerifier public verifier;
    BridgedToken public bToken;
    MockERC20 public mockToken;

    address public admin = address(0xA);
    address public guardian = address(0xB);
    address public user1 = address(0xC);
    address public user2 = address(0xD);

    uint256 public constant DAILY_LIMIT = 100 ether;
    uint256 public constant PER_TX_LIMIT = 10 ether;

    bytes32 public constant TEST_DID = keccak256("did:rings:test_user_1");
    bytes32 public constant TEST_DID_2 = keccak256("did:rings:test_user_2");

    // Dummy proof and public inputs for mock verifier
    bytes public dummyProof = abi.encode(
        [uint256(1), uint256(2)],
        [[uint256(3), uint256(4)], [uint256(5), uint256(6)]],
        [uint256(7), uint256(8)]
    );
    bytes32[] public dummyInputs;

    function setUp() public {
        // Deploy mock verifier
        verifier = new MockVerifier();

        // Deploy bridge
        vm.prank(admin);
        bridge = new RingsBridge(
            admin,
            guardian,
            DAILY_LIMIT,
            PER_TX_LIMIT,
            address(verifier)
        );

        // Deploy bridged token with bridge as minter
        vm.prank(admin);
        bToken = new BridgedToken("Bridged RINGS", "bRINGS", address(bridge));

        // Deploy mock ERC20
        mockToken = new MockERC20();

        // Fund test accounts
        vm.deal(user1, 200 ether);
        vm.deal(user2, 200 ether);
        vm.deal(address(bridge), 500 ether); // Fund bridge for withdrawals

        // Set up dummy public inputs — 5 elements matching circuit layout:
        // [amount, nonce, recipientHash, stateRoot, chainId]
        // publicInputs[4] must equal block.chainid for the chain ID check (#1242).
        dummyInputs.push(bytes32(uint256(1)));        // amount
        dummyInputs.push(bytes32(uint256(0)));        // nonce
        dummyInputs.push(bytes32(uint256(0)));        // recipientHash
        dummyInputs.push(bytes32(uint256(0)));        // stateRoot
        dummyInputs.push(bytes32(block.chainid));     // chainId (#1242 fix)
    }

    // ──────────────────────────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────────────────────────

    function test_ConstructorSetsAdmin() public view {
        assertTrue(bridge.hasRole(bridge.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_ConstructorSetsGuardian() public view {
        assertTrue(bridge.hasRole(bridge.GUARDIAN_ROLE(), guardian));
    }

    function test_ConstructorSetsLimits() public view {
        assertEq(bridge.dailyLimit(), DAILY_LIMIT);
        assertEq(bridge.perTxLimit(), PER_TX_LIMIT);
    }

    function test_ConstructorSetsVerifier() public view {
        assertEq(address(bridge.verifier()), address(verifier));
    }

    function test_ConstructorRevertsZeroAdmin() public {
        vm.expectRevert("RingsBridge: zero admin");
        new RingsBridge(address(0), guardian, DAILY_LIMIT, PER_TX_LIMIT, address(verifier));
    }

    function test_ConstructorRevertsZeroGuardian() public {
        vm.expectRevert("RingsBridge: zero guardian");
        new RingsBridge(admin, address(0), DAILY_LIMIT, PER_TX_LIMIT, address(verifier));
    }

    function test_ConstructorRevertsZeroVerifier() public {
        vm.expectRevert("RingsBridge: zero verifier");
        new RingsBridge(admin, guardian, DAILY_LIMIT, PER_TX_LIMIT, address(0));
    }

    function test_ConstructorRevertsZeroDailyLimit() public {
        vm.expectRevert("RingsBridge: zero daily limit");
        new RingsBridge(admin, guardian, 0, PER_TX_LIMIT, address(verifier));
    }

    function test_ConstructorRevertsZeroPerTxLimit() public {
        vm.expectRevert("RingsBridge: zero per-tx limit");
        new RingsBridge(admin, guardian, DAILY_LIMIT, 0, address(verifier));
    }

    function test_ConstructorRevertsPerTxExceedsDaily() public {
        vm.expectRevert("RingsBridge: per-tx limit exceeds daily");
        new RingsBridge(admin, guardian, 1 ether, 2 ether, address(verifier));
    }

    // ──────────────────────────────────────────────────────────────────
    //  ETH Deposits
    // ──────────────────────────────────────────────────────────────────

    function test_DepositETH() public {
        vm.prank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);

        assertEq(address(bridge).balance, 501 ether); // 500 initial + 1 deposited
        assertEq(bridge.depositNonce(), 1);
    }

    function test_DepositETH_RecordsInfo() public {
        vm.prank(user1);
        bridge.deposit{value: 2 ether}(TEST_DID);

        (
            address depositor,
            bytes32 ringsDID,
            uint256 amount,
            address token,
            uint256 timestamp,
            uint256 nonce
        ) = bridge.deposits(0);

        assertEq(depositor, user1);
        assertEq(ringsDID, TEST_DID);
        assertEq(amount, 2 ether);
        assertEq(token, address(0));
        assertEq(nonce, 0);
        assertGt(timestamp, 0);
    }

    function test_DepositETH_EmitsEvent() public {
        vm.expectEmit(true, true, true, true);
        emit Deposited(0, user1, TEST_DID, 1 ether, address(0), block.timestamp);

        vm.prank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);
    }

    function test_DepositETH_IncrementsNonce() public {
        vm.startPrank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);
        assertEq(bridge.depositNonce(), 1);

        bridge.deposit{value: 2 ether}(TEST_DID);
        assertEq(bridge.depositNonce(), 2);
        vm.stopPrank();
    }

    function test_DepositETH_RevertsZeroValue() public {
        vm.prank(user1);
        vm.expectRevert("RingsBridge: zero deposit");
        bridge.deposit{value: 0}(TEST_DID);
    }

    function test_DepositETH_RevertsZeroDID() public {
        vm.prank(user1);
        vm.expectRevert("RingsBridge: zero DID");
        bridge.deposit{value: 1 ether}(bytes32(0));
    }

    function test_DepositETH_RevertsWhenPaused() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.prank(user1);
        vm.expectRevert("Pausable: paused");
        bridge.deposit{value: 1 ether}(TEST_DID);
    }

    // ──────────────────────────────────────────────────────────────────
    //  ERC20 Deposits
    // ──────────────────────────────────────────────────────────────────

    function test_DepositToken() public {
        mockToken.mint(user1, 100 ether);
        vm.startPrank(user1);
        mockToken.approve(address(bridge), 10 ether);
        bridge.depositToken(address(mockToken), 10 ether, TEST_DID);
        vm.stopPrank();

        assertEq(mockToken.balanceOf(address(bridge)), 10 ether);
        assertEq(bridge.depositNonce(), 1);
    }

    function test_DepositToken_RecordsTokenAddress() public {
        mockToken.mint(user1, 100 ether);
        vm.startPrank(user1);
        mockToken.approve(address(bridge), 5 ether);
        bridge.depositToken(address(mockToken), 5 ether, TEST_DID);
        vm.stopPrank();

        (, , , address token, , ) = bridge.deposits(0);
        assertEq(token, address(mockToken));
    }

    function test_DepositToken_RevertsZeroAmount() public {
        vm.prank(user1);
        vm.expectRevert("RingsBridge: zero deposit");
        bridge.depositToken(address(mockToken), 0, TEST_DID);
    }

    function test_DepositToken_RevertsZeroTokenAddress() public {
        vm.prank(user1);
        vm.expectRevert("RingsBridge: zero token address");
        bridge.depositToken(address(0), 1 ether, TEST_DID);
    }

    function test_DepositToken_RevertsZeroDID() public {
        vm.prank(user1);
        vm.expectRevert("RingsBridge: zero DID");
        bridge.depositToken(address(mockToken), 1 ether, bytes32(0));
    }

    // ──────────────────────────────────────────────────────────────────
    //  ETH Withdrawals
    // ──────────────────────────────────────────────────────────────────

    function test_WithdrawETH() public {
        uint256 balBefore = user1.balance;

        bridge.withdraw(
            payable(user1),
            TEST_DID,
            5 ether,
            0, // nonce
            dummyProof,
            dummyInputs
        );

        assertEq(user1.balance, balBefore + 5 ether);
        assertEq(bridge.withdrawalNonce(), 1);
    }

    function test_WithdrawETH_RecordsInfo() public {
        bridge.withdraw(payable(user1), TEST_DID, 3 ether, 0, dummyProof, dummyInputs);

        (
            address recipient,
            bytes32 ringsDID,
            uint256 amount,
            address token,
            uint256 timestamp,
            uint256 nonce
        ) = bridge.withdrawals(0);

        assertEq(recipient, user1);
        assertEq(ringsDID, TEST_DID);
        assertEq(amount, 3 ether);
        assertEq(token, address(0));
        assertEq(nonce, 0);
        assertGt(timestamp, 0);
    }

    function test_WithdrawETH_EmitsEvent() public {
        vm.expectEmit(true, true, true, true);
        emit Withdrawn(0, user1, TEST_DID, 5 ether, address(0), block.timestamp);

        bridge.withdraw(payable(user1), TEST_DID, 5 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawETH_ReplayProtection() public {
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);

        // Same nonce should revert
        vm.expectRevert("RingsBridge: withdrawal already processed");
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawETH_DifferentNoncesSucceed() public {
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 1, dummyProof, dummyInputs);
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 2, dummyProof, dummyInputs);

        assertEq(bridge.withdrawalNonce(), 3);
        assertTrue(bridge.processedWithdrawals(0));
        assertTrue(bridge.processedWithdrawals(1));
        assertTrue(bridge.processedWithdrawals(2));
    }

    function test_WithdrawETH_InvalidProofReverts() public {
        verifier.setResult(false);

        vm.expectRevert("RingsBridge: invalid proof");
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawETH_RevertsZeroRecipient() public {
        vm.expectRevert("RingsBridge: zero recipient");
        bridge.withdraw(payable(address(0)), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawETH_RevertsZeroAmount() public {
        vm.expectRevert("RingsBridge: zero amount");
        bridge.withdraw(payable(user1), TEST_DID, 0, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawETH_RevertsZeroDID() public {
        vm.expectRevert("RingsBridge: zero DID");
        bridge.withdraw(payable(user1), bytes32(0), 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawETH_WhenPausedReverts() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.expectRevert("Pausable: paused");
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    /// @dev Fix for #1242 — cross-chain replay attack prevention.
    /// A proof generated for chain A (chainId in publicInputs[4] = A)
    /// must not be accepted on chain B (block.chainid = B).
    function test_WithdrawETH_RejectsWrongChainId() public {
        // Build public inputs with a wrong chain ID (block.chainid + 1)
        bytes32[] memory wrongChainInputs = new bytes32[](5);
        wrongChainInputs[0] = bytes32(uint256(1));        // amount
        wrongChainInputs[1] = bytes32(uint256(0));        // nonce
        wrongChainInputs[2] = bytes32(uint256(0));        // recipientHash
        wrongChainInputs[3] = bytes32(uint256(0));        // stateRoot
        wrongChainInputs[4] = bytes32(block.chainid + 1); // wrong chainId

        vm.expectRevert("RingsBridge: proof bound to wrong chain");
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, wrongChainInputs);
    }

    /// @dev Withdrawal must fail when publicInputs array is too short (< 5 elements).
    function test_WithdrawETH_RejectsMissingChainId() public {
        bytes32[] memory shortInputs = new bytes32[](4);
        shortInputs[0] = bytes32(uint256(1));
        shortInputs[1] = bytes32(uint256(0));
        shortInputs[2] = bytes32(uint256(0));
        shortInputs[3] = bytes32(uint256(0));

        vm.expectRevert("RingsBridge: missing chain ID input");
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, shortInputs);
    }

    /// @dev Same replay protection for token withdrawals.
    function test_WithdrawToken_RejectsWrongChainId() public {
        bytes32[] memory wrongChainInputs = new bytes32[](5);
        wrongChainInputs[0] = bytes32(uint256(1));
        wrongChainInputs[1] = bytes32(uint256(0));
        wrongChainInputs[2] = bytes32(uint256(0));
        wrongChainInputs[3] = bytes32(uint256(0));
        wrongChainInputs[4] = bytes32(block.chainid + 1); // wrong chainId

        vm.expectRevert("RingsBridge: proof bound to wrong chain");
        bridge.withdrawToken(address(bToken), user1, TEST_DID, 1 ether, 0, dummyProof, wrongChainInputs);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Token Withdrawals (BridgedToken mint)
    // ──────────────────────────────────────────────────────────────────

    function test_WithdrawToken() public {
        bridge.withdrawToken(
            address(bToken),
            user1,
            TEST_DID,
            5 ether,
            0,
            dummyProof,
            dummyInputs
        );

        assertEq(bToken.balanceOf(user1), 5 ether);
        assertEq(bridge.withdrawalNonce(), 1);
    }

    function test_WithdrawToken_RecordsTokenAddress() public {
        bridge.withdrawToken(address(bToken), user1, TEST_DID, 2 ether, 0, dummyProof, dummyInputs);

        (, , , address token, , ) = bridge.withdrawals(0);
        assertEq(token, address(bToken));
    }

    function test_WithdrawToken_ReplayProtection() public {
        bridge.withdrawToken(address(bToken), user1, TEST_DID, 1 ether, 0, dummyProof, dummyInputs);

        vm.expectRevert("RingsBridge: withdrawal already processed");
        bridge.withdrawToken(address(bToken), user1, TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawToken_RevertsZeroTokenAddress() public {
        vm.expectRevert("RingsBridge: zero token");
        bridge.withdrawToken(address(0), user1, TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawToken_RevertsZeroRecipient() public {
        vm.expectRevert("RingsBridge: zero recipient");
        bridge.withdrawToken(address(bToken), address(0), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_WithdrawToken_InvalidProofReverts() public {
        verifier.setResult(false);

        vm.expectRevert("RingsBridge: invalid proof");
        bridge.withdrawToken(address(bToken), user1, TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Rate Limiting
    // ──────────────────────────────────────────────────────────────────

    function test_PerTxLimitEnforced() public {
        vm.expectRevert("RingsBridge: exceeds per-tx limit");
        bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT + 1, 0, dummyProof, dummyInputs);
    }

    function test_PerTxLimitExactlyAtLimit() public {
        bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT, 0, dummyProof, dummyInputs);
        assertEq(bridge.dailyVolume(), PER_TX_LIMIT);
    }

    function test_DailyLimitEnforced() public {
        // Withdraw 10 times at PER_TX_LIMIT (10 ETH each = 100 ETH total = DAILY_LIMIT)
        for (uint256 i = 0; i < 10; i++) {
            bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT, i, dummyProof, dummyInputs);
        }

        // One more should fail (daily limit hit)
        vm.expectRevert("RingsBridge: exceeds daily limit");
        bridge.withdraw(payable(user1), TEST_DID, 1 wei, 10, dummyProof, dummyInputs);
    }

    function test_DailyLimitAccumulation() public {
        bridge.withdraw(payable(user1), TEST_DID, 3 ether, 0, dummyProof, dummyInputs);
        assertEq(bridge.dailyVolume(), 3 ether);

        bridge.withdraw(payable(user1), TEST_DID, 4 ether, 1, dummyProof, dummyInputs);
        assertEq(bridge.dailyVolume(), 7 ether);
    }

    function test_DailyLimitResetAfter24Hours() public {
        // Exhaust daily limit
        for (uint256 i = 0; i < 10; i++) {
            bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT, i, dummyProof, dummyInputs);
        }
        assertEq(bridge.dailyVolume(), DAILY_LIMIT);

        // Advance 24 hours + 1 second
        vm.warp(block.timestamp + 1 days + 1);

        // Should succeed after reset
        bridge.withdraw(payable(user1), TEST_DID, 5 ether, 10, dummyProof, dummyInputs);
        assertEq(bridge.dailyVolume(), 5 ether);
    }

    function test_GetRemainingDailyLimit_Full() public view {
        assertEq(bridge.getRemainingDailyLimit(), DAILY_LIMIT);
    }

    function test_GetRemainingDailyLimit_Partial() public {
        bridge.withdraw(payable(user1), TEST_DID, 3 ether, 0, dummyProof, dummyInputs);
        assertEq(bridge.getRemainingDailyLimit(), DAILY_LIMIT - 3 ether);
    }

    function test_GetRemainingDailyLimit_Exhausted() public {
        for (uint256 i = 0; i < 10; i++) {
            bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT, i, dummyProof, dummyInputs);
        }
        assertEq(bridge.getRemainingDailyLimit(), 0);
    }

    function test_GetRemainingDailyLimit_ResetAfterWindow() public {
        bridge.withdraw(payable(user1), TEST_DID, 5 ether, 0, dummyProof, dummyInputs);
        vm.warp(block.timestamp + 1 days + 1);
        // View function returns dailyLimit when a reset would occur
        assertEq(bridge.getRemainingDailyLimit(), DAILY_LIMIT);
    }

    function test_DailyLimitAlsoAppliesToTokenWithdrawals() public {
        // Mix ETH and token withdrawals — both count toward daily limit
        bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT, 0, dummyProof, dummyInputs);
        bridge.withdrawToken(address(bToken), user1, TEST_DID, PER_TX_LIMIT, 1, dummyProof, dummyInputs);

        assertEq(bridge.dailyVolume(), 2 * PER_TX_LIMIT);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Access Control — Pause / Unpause
    // ──────────────────────────────────────────────────────────────────

    function test_GuardianCanPause() public {
        vm.prank(guardian);
        bridge.emergencyPause();
        assertTrue(bridge.paused());
    }

    function test_EmergencyPauseEmitsEvent() public {
        vm.expectEmit(true, false, false, false);
        emit EmergencyPaused(guardian);

        vm.prank(guardian);
        bridge.emergencyPause();
    }

    function test_NonGuardianCannotPause() public {
        vm.prank(user1);
        vm.expectRevert();
        bridge.emergencyPause();
    }

    function test_AdminCanUnpause() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.prank(admin);
        bridge.unpause();
        assertFalse(bridge.paused());
    }

    function test_GuardianCannotUnpause() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.prank(guardian);
        vm.expectRevert();
        bridge.unpause();
    }

    function test_NonAdminCannotUnpause() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.prank(user1);
        vm.expectRevert();
        bridge.unpause();
    }

    function test_PauseBlocksDepositsAndWithdrawals() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.prank(user1);
        vm.expectRevert("Pausable: paused");
        bridge.deposit{value: 1 ether}(TEST_DID);

        vm.expectRevert("Pausable: paused");
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);

        vm.expectRevert("Pausable: paused");
        bridge.withdrawToken(address(bToken), user1, TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
    }

    function test_UnpauseRestoresOperations() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.prank(admin);
        bridge.unpause();

        // Should work after unpause
        vm.prank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);
        assertEq(bridge.depositNonce(), 1);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Access Control — Rate Limit Updates
    // ──────────────────────────────────────────────────────────────────

    function test_GuardianCanUpdateRateLimits() public {
        vm.prank(guardian);
        bridge.updateRateLimits(200 ether, 20 ether);

        assertEq(bridge.dailyLimit(), 200 ether);
        assertEq(bridge.perTxLimit(), 20 ether);
    }

    function test_UpdateRateLimitsEmitsEvent() public {
        vm.expectEmit(false, false, false, true);
        emit RateLimitUpdated(200 ether, 20 ether, guardian);

        vm.prank(guardian);
        bridge.updateRateLimits(200 ether, 20 ether);
    }

    function test_NonGuardianCannotUpdateRateLimits() public {
        vm.prank(user1);
        vm.expectRevert();
        bridge.updateRateLimits(200 ether, 20 ether);
    }

    function test_AdminCannotUpdateRateLimits() public {
        // Admin is not guardian by default
        vm.prank(admin);
        vm.expectRevert();
        bridge.updateRateLimits(200 ether, 20 ether);
    }

    function test_UpdateRateLimitsRevertsZeroDaily() public {
        vm.prank(guardian);
        vm.expectRevert("RingsBridge: zero daily limit");
        bridge.updateRateLimits(0, PER_TX_LIMIT);
    }

    function test_UpdateRateLimitsRevertsZeroPerTx() public {
        vm.prank(guardian);
        vm.expectRevert("RingsBridge: zero per-tx limit");
        bridge.updateRateLimits(DAILY_LIMIT, 0);
    }

    function test_UpdateRateLimitsRevertsPerTxExceedsDaily() public {
        vm.prank(guardian);
        vm.expectRevert("RingsBridge: per-tx limit exceeds daily");
        bridge.updateRateLimits(10 ether, 20 ether);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Sync Committee
    // ──────────────────────────────────────────────────────────────────

    function test_UpdateSyncCommittee() public {
        bytes32 newRoot = keccak256("new_sync_committee_root");

        bridge.updateSyncCommittee(newRoot, 100, dummyProof, dummyInputs);

        assertEq(bridge.syncCommitteeRoot(), newRoot);
        assertEq(bridge.latestVerifiedSlot(), 100);
    }

    function test_UpdateSyncCommitteeEmitsEvent() public {
        bytes32 newRoot = keccak256("new_sync_committee_root");

        vm.expectEmit(true, true, false, true);
        emit SyncCommitteeUpdated(newRoot, 100, address(this));

        bridge.updateSyncCommittee(newRoot, 100, dummyProof, dummyInputs);
    }

    function test_SyncCommitteeSlotMustAdvance() public {
        bytes32 root1 = keccak256("root1");
        bytes32 root2 = keccak256("root2");

        bridge.updateSyncCommittee(root1, 100, dummyProof, dummyInputs);

        // Same slot → revert
        vm.expectRevert("RingsBridge: slot not advancing");
        bridge.updateSyncCommittee(root2, 100, dummyProof, dummyInputs);

        // Lower slot → revert
        vm.expectRevert("RingsBridge: slot not advancing");
        bridge.updateSyncCommittee(root2, 50, dummyProof, dummyInputs);

        // Higher slot → success
        bridge.updateSyncCommittee(root2, 200, dummyProof, dummyInputs);
        assertEq(bridge.latestVerifiedSlot(), 200);
    }

    function test_SyncCommitteeRevertsZeroRoot() public {
        vm.expectRevert("RingsBridge: zero root");
        bridge.updateSyncCommittee(bytes32(0), 100, dummyProof, dummyInputs);
    }

    function test_SyncCommitteeInvalidProofReverts() public {
        verifier.setResult(false);

        vm.expectRevert("RingsBridge: invalid committee proof");
        bridge.updateSyncCommittee(keccak256("root"), 100, dummyProof, dummyInputs);
    }

    function test_SyncCommitteeWhenPausedReverts() public {
        vm.prank(guardian);
        bridge.emergencyPause();

        vm.expectRevert("Pausable: paused");
        bridge.updateSyncCommittee(keccak256("root"), 100, dummyProof, dummyInputs);
    }

    // ──────────────────────────────────────────────────────────────────
    //  View Functions
    // ──────────────────────────────────────────────────────────────────

    function test_IsDepositProcessed() public {
        assertFalse(bridge.isDepositProcessed(0));

        vm.prank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);

        assertTrue(bridge.isDepositProcessed(0));
        assertFalse(bridge.isDepositProcessed(1));
    }

    function test_GetDepositInfo() public {
        vm.prank(user1);
        bridge.deposit{value: 3 ether}(TEST_DID);

        RingsBridge.DepositInfo memory info = bridge.getDepositInfo(0);
        assertEq(info.depositor, user1);
        assertEq(info.ringsDID, TEST_DID);
        assertEq(info.amount, 3 ether);
        assertEq(info.token, address(0));
    }

    function test_GetWithdrawalInfo() public {
        bridge.withdraw(payable(user1), TEST_DID, 2 ether, 0, dummyProof, dummyInputs);

        RingsBridge.WithdrawalInfo memory info = bridge.getWithdrawalInfo(0);
        assertEq(info.recipient, user1);
        assertEq(info.ringsDID, TEST_DID);
        assertEq(info.amount, 2 ether);
        assertEq(info.token, address(0));
    }

    // ──────────────────────────────────────────────────────────────────
    //  Receive
    // ──────────────────────────────────────────────────────────────────

    function test_BridgeAcceptsPlainETH() public {
        uint256 balBefore = address(bridge).balance;
        vm.prank(user1);
        (bool success,) = address(bridge).call{value: 10 ether}("");
        assertTrue(success);
        assertEq(address(bridge).balance, balBefore + 10 ether);
    }

    // ──────────────────────────────────────────────────────────────────
    //  ERC-165
    // ──────────────────────────────────────────────────────────────────

    function test_SupportsInterface_AccessControl() public view {
        // IAccessControl interface ID
        assertTrue(bridge.supportsInterface(type(IAccessControl).interfaceId));
    }

    function test_SupportsInterface_ERC165() public view {
        // ERC165 itself
        assertTrue(bridge.supportsInterface(0x01ffc9a7));
    }

    // ──────────────────────────────────────────────────────────────────
    //  Fuzz Tests
    // ──────────────────────────────────────────────────────────────────

    function testFuzz_DepositAnyAmount(uint256 amount) public {
        amount = bound(amount, 1, 100 ether);
        vm.deal(user1, amount);

        vm.prank(user1);
        bridge.deposit{value: amount}(TEST_DID);

        assertEq(bridge.depositNonce(), 1);
    }

    function testFuzz_WithdrawWithinLimits(uint256 amount) public {
        amount = bound(amount, 1, PER_TX_LIMIT);

        bridge.withdraw(payable(user1), TEST_DID, amount, 0, dummyProof, dummyInputs);
        assertEq(bridge.dailyVolume(), amount);
    }

    function testFuzz_PerTxLimitRejection(uint256 amount) public {
        amount = bound(amount, PER_TX_LIMIT + 1, type(uint128).max);

        vm.expectRevert("RingsBridge: exceeds per-tx limit");
        bridge.withdraw(payable(user1), TEST_DID, amount, 0, dummyProof, dummyInputs);
    }

    // ──────────────────────────────────────────────────────────────────
    //  End-to-End Scenarios
    // ──────────────────────────────────────────────────────────────────

    function test_E2E_DepositThenWithdraw() public {
        // User deposits 5 ETH
        vm.prank(user1);
        bridge.deposit{value: 5 ether}(TEST_DID);

        uint256 bridgeBalAfterDeposit = address(bridge).balance;

        // User withdraws 5 ETH (proof verified by mock)
        uint256 userBalBefore = user2.balance;
        bridge.withdraw(payable(user2), TEST_DID, 5 ether, 0, dummyProof, dummyInputs);

        assertEq(user2.balance, userBalBefore + 5 ether);
        assertEq(address(bridge).balance, bridgeBalAfterDeposit - 5 ether);
        assertEq(bridge.depositNonce(), 1);
        assertEq(bridge.withdrawalNonce(), 1);
    }

    function test_E2E_MultipleUsersMultipleDepositsWithdrawals() public {
        // User1 deposits twice
        vm.startPrank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);
        bridge.deposit{value: 2 ether}(TEST_DID);
        vm.stopPrank();

        // User2 deposits
        vm.prank(user2);
        bridge.deposit{value: 3 ether}(TEST_DID_2);

        assertEq(bridge.depositNonce(), 3);

        // Withdrawals
        bridge.withdraw(payable(user1), TEST_DID, 1 ether, 0, dummyProof, dummyInputs);
        bridge.withdraw(payable(user2), TEST_DID_2, 2 ether, 1, dummyProof, dummyInputs);

        assertEq(bridge.withdrawalNonce(), 2);
        assertEq(bridge.dailyVolume(), 3 ether);
    }

    function test_E2E_PauseUnpauseResume() public {
        // Normal operation
        vm.prank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);

        // Guardian pauses
        vm.prank(guardian);
        bridge.emergencyPause();

        // Operations blocked
        vm.prank(user1);
        vm.expectRevert("Pausable: paused");
        bridge.deposit{value: 1 ether}(TEST_DID);

        // Admin unpauses
        vm.prank(admin);
        bridge.unpause();

        // Operations resume
        vm.prank(user1);
        bridge.deposit{value: 1 ether}(TEST_DID);
        assertEq(bridge.depositNonce(), 2);
    }

    function test_E2E_RateLimitResetCycle() public {
        // Day 1: exhaust limit
        for (uint256 i = 0; i < 10; i++) {
            bridge.withdraw(payable(user1), TEST_DID, PER_TX_LIMIT, i, dummyProof, dummyInputs);
        }
        assertEq(bridge.dailyVolume(), DAILY_LIMIT);

        // Still day 1: can't withdraw more
        vm.expectRevert("RingsBridge: exceeds daily limit");
        bridge.withdraw(payable(user1), TEST_DID, 1 wei, 10, dummyProof, dummyInputs);

        // Day 2
        vm.warp(block.timestamp + 1 days + 1);

        // Fresh limit
        bridge.withdraw(payable(user1), TEST_DID, 5 ether, 10, dummyProof, dummyInputs);
        assertEq(bridge.dailyVolume(), 5 ether);
    }
}
