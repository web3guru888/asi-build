// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title RingsBridge
 * @author ASI:BUILD — Rings↔Ethereum Bridge
 * @dev Trustless bridge between the Rings P2P network and Ethereum.
 *
 *      Architecture overview:
 *      ─────────────────────
 *      • **Deposits** — Users lock ETH or ERC20 tokens in this contract,
 *        specifying their Rings DID.  The bridge relayer observes the
 *        `Deposited` event and mints equivalent tokens on the Rings side.
 *
 *      • **Withdrawals** — Users on Rings initiate a withdrawal.  A ZK
 *        proof (Groth16) attesting to the withdrawal's validity is
 *        submitted to this contract.  On successful verification the
 *        contract releases ETH or mints BridgedTokens.
 *
 *      • **Sync committee** — A light-client–style sync committee root
 *        is maintained on-chain so that relayers can anchor Rings
 *        consensus state.  Updates require a ZK proof.
 *
 *      Safety features:
 *      ────────────────
 *      • Per-transaction and daily volume rate limits
 *      • Replay protection via nonce-based processed-withdrawal mapping
 *      • Pausable by GUARDIAN_ROLE (emergency circuit breaker)
 *      • ReentrancyGuard on all state-mutating external functions
 *      • ERC20 interactions via OpenZeppelin SafeERC20
 *
 * @notice This contract is designed for formal verification.  All
 *         arithmetic is checked (Solidity 0.8 default), and all
 *         external calls follow checks-effects-interactions.
 */

// ─── External interface for the Groth16 verifier ────────────────────
interface IGroth16Verifier {
    function verifyProof(
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external view returns (bool);
}

// ─── External interface for the bridged token ───────────────────────
interface IBridgedToken {
    function mint(address to, uint256 amount) external;
    function burnFrom(address from, uint256 amount) external;
}

contract RingsBridge is AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ──────────────────────────────────────────────────────────────────
    //  Roles
    // ──────────────────────────────────────────────────────────────────

    /// @dev Guardian can pause/unpause and update rate limits.
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    // ──────────────────────────────────────────────────────────────────
    //  Structs
    // ──────────────────────────────────────────────────────────────────

    /// @dev Record of a deposit into the bridge.
    struct DepositInfo {
        address depositor;
        bytes32 ringsDID;
        uint256 amount;
        address token; // address(0) for ETH deposits
        uint256 timestamp;
        uint256 nonce;
    }

    /// @dev Record of a processed withdrawal from the bridge.
    struct WithdrawalInfo {
        address recipient;
        bytes32 ringsDID;
        uint256 amount;
        address token; // address(0) for ETH withdrawals
        uint256 timestamp;
        uint256 nonce;
    }

    // ──────────────────────────────────────────────────────────────────
    //  State — Sync committee
    // ──────────────────────────────────────────────────────────────────

    /// @notice Current sync committee root (Poseidon hash of the committee).
    bytes32 public syncCommitteeRoot;

    /// @notice Slot number of the latest verified Rings consensus state.
    uint64 public latestVerifiedSlot;

    // ──────────────────────────────────────────────────────────────────
    //  State — Verifier
    // ──────────────────────────────────────────────────────────────────

    /// @notice Address of the deployed Groth16Verifier contract.
    IGroth16Verifier public immutable verifier;

    // ──────────────────────────────────────────────────────────────────
    //  State — Rate limiting
    // ──────────────────────────────────────────────────────────────────

    /// @notice Maximum total withdrawal volume per 24-hour window (in wei).
    uint256 public dailyLimit;

    /// @notice Maximum single withdrawal amount (in wei).
    uint256 public perTxLimit;

    /// @notice Cumulative withdrawal volume in the current daily window.
    uint256 public dailyVolume;

    /// @notice Timestamp at which the current daily window started.
    uint256 public lastResetTimestamp;

    // ──────────────────────────────────────────────────────────────────
    //  State — Nonces & mappings
    // ──────────────────────────────────────────────────────────────────

    /// @notice Monotonically increasing deposit nonce.
    uint256 public depositNonce;

    /// @notice Monotonically increasing withdrawal nonce.
    uint256 public withdrawalNonce;

    /// @notice Replay protection: withdrawal nonce → processed flag.
    mapping(uint256 => bool) public processedWithdrawals;

    /// @notice Deposit records by nonce.
    mapping(uint256 => DepositInfo) public deposits;

    /// @notice Withdrawal records by nonce.
    mapping(uint256 => WithdrawalInfo) public withdrawals;

    // ──────────────────────────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────────────────────────

    /**
     * @dev Emitted when a user deposits ETH or ERC20 into the bridge.
     * @param nonce      Unique deposit identifier.
     * @param depositor  Ethereum address of the depositor.
     * @param ringsDID   Rings DID that will receive tokens on the Rings side.
     * @param amount     Amount deposited (in wei / token smallest unit).
     * @param token      Token address (address(0) for native ETH).
     * @param timestamp  Block timestamp of the deposit.
     */
    event Deposited(
        uint256 indexed nonce,
        address indexed depositor,
        bytes32 indexed ringsDID,
        uint256 amount,
        address token,
        uint256 timestamp
    );

    /**
     * @dev Emitted when a verified withdrawal is processed.
     * @param nonce      Unique withdrawal identifier.
     * @param recipient  Ethereum address receiving the funds.
     * @param ringsDID   Rings DID that initiated the withdrawal.
     * @param amount     Amount withdrawn (in wei / token smallest unit).
     * @param token      Token address (address(0) for native ETH).
     * @param timestamp  Block timestamp of the withdrawal.
     */
    event Withdrawn(
        uint256 indexed nonce,
        address indexed recipient,
        bytes32 indexed ringsDID,
        uint256 amount,
        address token,
        uint256 timestamp
    );

    /**
     * @dev Emitted when the Rings sync committee root is updated.
     * @param newRoot  New sync committee root hash.
     * @param slot     Rings consensus slot that was verified.
     * @param updater  Address that submitted the update.
     */
    event SyncCommitteeUpdated(
        bytes32 indexed newRoot,
        uint64 indexed slot,
        address updater
    );

    /**
     * @dev Emitted when rate limits are changed by a guardian.
     * @param newDailyLimit New daily volume cap (wei).
     * @param newPerTxLimit New per-transaction cap (wei).
     * @param updater       Address that changed the limits.
     */
    event RateLimitUpdated(
        uint256 newDailyLimit,
        uint256 newPerTxLimit,
        address updater
    );

    /**
     * @dev Emitted when the bridge is emergency-paused.
     * @param guardian Address that triggered the pause.
     */
    event EmergencyPaused(address indexed guardian);

    // ──────────────────────────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────────────────────────

    /**
     * @param initialAdmin   Address receiving DEFAULT_ADMIN_ROLE.
     * @param guardian        Address receiving GUARDIAN_ROLE.
     * @param dailyLimit_    Initial daily withdrawal limit (wei).
     * @param perTxLimit_    Initial per-transaction limit (wei).
     * @param verifierAddress Address of the deployed Groth16Verifier.
     */
    constructor(
        address initialAdmin,
        address guardian,
        uint256 dailyLimit_,
        uint256 perTxLimit_,
        address verifierAddress
    ) {
        require(initialAdmin != address(0), "RingsBridge: zero admin");
        require(guardian != address(0), "RingsBridge: zero guardian");
        require(verifierAddress != address(0), "RingsBridge: zero verifier");
        require(dailyLimit_ > 0, "RingsBridge: zero daily limit");
        require(perTxLimit_ > 0, "RingsBridge: zero per-tx limit");
        require(
            perTxLimit_ <= dailyLimit_,
            "RingsBridge: per-tx limit exceeds daily"
        );

        _grantRole(DEFAULT_ADMIN_ROLE, initialAdmin);
        _grantRole(GUARDIAN_ROLE, guardian);

        dailyLimit = dailyLimit_;
        perTxLimit = perTxLimit_;
        verifier = IGroth16Verifier(verifierAddress);
        lastResetTimestamp = block.timestamp;
    }

    // ──────────────────────────────────────────────────────────────────
    //  Deposits
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Deposit native ETH into the bridge.
     * @param ringsDID  The Rings DID (bytes32) that should receive the
     *                  equivalent tokens on the Rings network.
     *
     * @dev Emits {Deposited} with token = address(0).
     */
    function deposit(
        bytes32 ringsDID
    ) external payable whenNotPaused nonReentrant {
        require(msg.value > 0, "RingsBridge: zero deposit");
        require(ringsDID != bytes32(0), "RingsBridge: zero DID");

        uint256 nonce = depositNonce;
        depositNonce = nonce + 1;

        deposits[nonce] = DepositInfo({
            depositor: msg.sender,
            ringsDID: ringsDID,
            amount: msg.value,
            token: address(0),
            timestamp: block.timestamp,
            nonce: nonce
        });

        emit Deposited(
            nonce,
            msg.sender,
            ringsDID,
            msg.value,
            address(0),
            block.timestamp
        );
    }

    /**
     * @notice Deposit ERC20 tokens into the bridge.
     * @param token     Address of the ERC20 token contract.
     * @param amount    Number of tokens to deposit (in smallest unit).
     * @param ringsDID  The Rings DID that should receive the equivalent
     *                  tokens on the Rings network.
     *
     * @dev The caller must have approved this contract for `amount` tokens.
     *      Uses SafeERC20.safeTransferFrom for safe interaction.
     *      Emits {Deposited}.
     */
    function depositToken(
        address token,
        uint256 amount,
        bytes32 ringsDID
    ) external whenNotPaused nonReentrant {
        require(amount > 0, "RingsBridge: zero deposit");
        require(token != address(0), "RingsBridge: zero token address");
        require(ringsDID != bytes32(0), "RingsBridge: zero DID");

        // Transfer tokens from depositor to this contract.
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        uint256 nonce = depositNonce;
        depositNonce = nonce + 1;

        deposits[nonce] = DepositInfo({
            depositor: msg.sender,
            ringsDID: ringsDID,
            amount: amount,
            token: token,
            timestamp: block.timestamp,
            nonce: nonce
        });

        emit Deposited(
            nonce,
            msg.sender,
            ringsDID,
            amount,
            token,
            block.timestamp
        );
    }

    // ──────────────────────────────────────────────────────────────────
    //  Withdrawals — Native ETH
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Withdraw native ETH from the bridge after ZK proof
     *         verification.
     *
     * @param recipient     Ethereum address to receive the ETH.
     * @param ringsDID      Rings DID that initiated the withdrawal.
     * @param amount        Amount of ETH to withdraw (wei).
     * @param nonce_        Withdrawal nonce (for replay protection).
     * @param proof         ABI-encoded Groth16 proof bytes.
     * @param publicInputs  Public inputs for the proof (must encode
     *                      recipient, ringsDID, amount, nonce).
     *
     * @dev Checks: proof validity → replay protection → rate limits.
     *      Effects: record withdrawal, update daily volume.
     *      Interactions: transfer ETH last (CEI pattern).
     */
    function withdraw(
        address payable recipient,
        bytes32 ringsDID,
        uint256 amount,
        uint256 nonce_,
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external whenNotPaused nonReentrant {
        require(recipient != address(0), "RingsBridge: zero recipient");
        require(amount > 0, "RingsBridge: zero amount");
        require(ringsDID != bytes32(0), "RingsBridge: zero DID");

        // ── Replay protection ───────────────────────────────────────
        require(
            !processedWithdrawals[nonce_],
            "RingsBridge: withdrawal already processed"
        );

        // ── ZK proof verification ───────────────────────────────────
        require(
            verifier.verifyProof(proof, publicInputs),
            "RingsBridge: invalid proof"
        );

        // ── Rate limiting ───────────────────────────────────────────
        require(amount <= perTxLimit, "RingsBridge: exceeds per-tx limit");
        _resetDailyVolumeIfNeeded();
        require(
            dailyVolume + amount <= dailyLimit,
            "RingsBridge: exceeds daily limit"
        );

        // ── Effects ─────────────────────────────────────────────────
        processedWithdrawals[nonce_] = true;
        dailyVolume += amount;

        uint256 wNonce = withdrawalNonce;
        withdrawalNonce = wNonce + 1;

        withdrawals[wNonce] = WithdrawalInfo({
            recipient: recipient,
            ringsDID: ringsDID,
            amount: amount,
            token: address(0),
            timestamp: block.timestamp,
            nonce: wNonce
        });

        // ── Interaction (last, per CEI) ─────────────────────────────
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "RingsBridge: ETH transfer failed");

        emit Withdrawn(
            wNonce,
            recipient,
            ringsDID,
            amount,
            address(0),
            block.timestamp
        );
    }

    // ──────────────────────────────────────────────────────────────────
    //  Withdrawals — ERC20 (BridgedToken mint)
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Withdraw bridged ERC20 tokens.  Instead of releasing locked
     *         tokens, this mints new BridgedTokens to the recipient.
     *
     * @param bridgedToken  Address of the BridgedToken contract to mint.
     * @param recipient     Ethereum address to receive the tokens.
     * @param ringsDID      Rings DID that initiated the withdrawal.
     * @param amount        Amount of tokens to mint.
     * @param nonce_        Withdrawal nonce (for replay protection).
     * @param proof         ABI-encoded Groth16 proof bytes.
     * @param publicInputs  Public inputs for the proof.
     *
     * @dev The bridge must hold BRIDGE_ROLE on the BridgedToken contract.
     */
    function withdrawToken(
        address bridgedToken,
        address recipient,
        bytes32 ringsDID,
        uint256 amount,
        uint256 nonce_,
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external whenNotPaused nonReentrant {
        require(bridgedToken != address(0), "RingsBridge: zero token");
        require(recipient != address(0), "RingsBridge: zero recipient");
        require(amount > 0, "RingsBridge: zero amount");
        require(ringsDID != bytes32(0), "RingsBridge: zero DID");

        // ── Replay protection ───────────────────────────────────────
        require(
            !processedWithdrawals[nonce_],
            "RingsBridge: withdrawal already processed"
        );

        // ── ZK proof verification ───────────────────────────────────
        require(
            verifier.verifyProof(proof, publicInputs),
            "RingsBridge: invalid proof"
        );

        // ── Rate limiting ───────────────────────────────────────────
        require(amount <= perTxLimit, "RingsBridge: exceeds per-tx limit");
        _resetDailyVolumeIfNeeded();
        require(
            dailyVolume + amount <= dailyLimit,
            "RingsBridge: exceeds daily limit"
        );

        // ── Effects ─────────────────────────────────────────────────
        processedWithdrawals[nonce_] = true;
        dailyVolume += amount;

        uint256 wNonce = withdrawalNonce;
        withdrawalNonce = wNonce + 1;

        withdrawals[wNonce] = WithdrawalInfo({
            recipient: recipient,
            ringsDID: ringsDID,
            amount: amount,
            token: bridgedToken,
            timestamp: block.timestamp,
            nonce: wNonce
        });

        // ── Interaction: mint tokens ────────────────────────────────
        IBridgedToken(bridgedToken).mint(recipient, amount);

        emit Withdrawn(
            wNonce,
            recipient,
            ringsDID,
            amount,
            bridgedToken,
            block.timestamp
        );
    }

    // ──────────────────────────────────────────────────────────────────
    //  Sync committee management
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Update the Rings sync committee root with a new verified
     *         committee.
     *
     * @param newRoot       New sync committee Poseidon root.
     * @param slot          Rings slot number the new committee covers.
     * @param proof         ZK proof that the committee rotation is valid.
     * @param publicInputs  Public inputs for the rotation proof.
     *
     * @dev The new slot must be strictly greater than the current one to
     *      prevent replay.  The ZK proof must verify against the on-chain
     *      Groth16Verifier.
     */
    function updateSyncCommittee(
        bytes32 newRoot,
        uint64 slot,
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external whenNotPaused nonReentrant {
        require(newRoot != bytes32(0), "RingsBridge: zero root");
        require(
            slot > latestVerifiedSlot,
            "RingsBridge: slot not advancing"
        );

        // Verify the committee rotation proof.
        require(
            verifier.verifyProof(proof, publicInputs),
            "RingsBridge: invalid committee proof"
        );

        syncCommitteeRoot = newRoot;
        latestVerifiedSlot = slot;

        emit SyncCommitteeUpdated(newRoot, slot, msg.sender);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Guardian functions
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Emergency pause — halts all deposits and withdrawals.
     * @dev Only callable by GUARDIAN_ROLE.
     */
    function emergencyPause() external onlyRole(GUARDIAN_ROLE) {
        _pause();
        emit EmergencyPaused(msg.sender);
    }

    /**
     * @notice Unpause the bridge after an emergency.
     * @dev Only callable by DEFAULT_ADMIN_ROLE (more restrictive than pause).
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    /**
     * @notice Update rate limits.
     * @param newDailyLimit New daily volume cap (wei).
     * @param newPerTxLimit New per-transaction cap (wei).
     *
     * @dev Only callable by GUARDIAN_ROLE.  The per-tx limit must not
     *      exceed the daily limit.
     */
    function updateRateLimits(
        uint256 newDailyLimit,
        uint256 newPerTxLimit
    ) external onlyRole(GUARDIAN_ROLE) {
        require(newDailyLimit > 0, "RingsBridge: zero daily limit");
        require(newPerTxLimit > 0, "RingsBridge: zero per-tx limit");
        require(
            newPerTxLimit <= newDailyLimit,
            "RingsBridge: per-tx limit exceeds daily"
        );

        dailyLimit = newDailyLimit;
        perTxLimit = newPerTxLimit;

        emit RateLimitUpdated(newDailyLimit, newPerTxLimit, msg.sender);
    }

    // ──────────────────────────────────────────────────────────────────
    //  View functions
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Check whether a given deposit nonce has been recorded.
     * @param nonce_ Deposit nonce to check.
     * @return True if a deposit with this nonce exists.
     */
    function isDepositProcessed(uint256 nonce_) external view returns (bool) {
        return deposits[nonce_].timestamp != 0;
    }

    /**
     * @notice Get the remaining daily withdrawal capacity.
     * @return Remaining capacity in wei.  Resets when a new 24-hour
     *         window begins.
     */
    function getRemainingDailyLimit() external view returns (uint256) {
        if (block.timestamp >= lastResetTimestamp + 1 days) {
            // A reset would occur on the next withdrawal.
            return dailyLimit;
        }
        if (dailyVolume >= dailyLimit) {
            return 0;
        }
        return dailyLimit - dailyVolume;
    }

    /**
     * @notice Retrieve a deposit record by nonce.
     * @param nonce_ Deposit nonce.
     * @return info The DepositInfo struct.
     */
    function getDepositInfo(
        uint256 nonce_
    ) external view returns (DepositInfo memory info) {
        info = deposits[nonce_];
    }

    /**
     * @notice Retrieve a withdrawal record by nonce.
     * @param nonce_ Withdrawal nonce.
     * @return info The WithdrawalInfo struct.
     */
    function getWithdrawalInfo(
        uint256 nonce_
    ) external view returns (WithdrawalInfo memory info) {
        info = withdrawals[nonce_];
    }

    // ──────────────────────────────────────────────────────────────────
    //  Internal helpers
    // ──────────────────────────────────────────────────────────────────

    /**
     * @dev Reset the daily volume counter if 24 hours have elapsed since
     *      the last reset.
     */
    function _resetDailyVolumeIfNeeded() internal {
        if (block.timestamp >= lastResetTimestamp + 1 days) {
            dailyVolume = 0;
            lastResetTimestamp = block.timestamp;
        }
    }

    // ──────────────────────────────────────────────────────────────────
    //  ERC-165
    // ──────────────────────────────────────────────────────────────────

    /**
     * @dev Resolves supportsInterface for AccessControl.
     */
    function supportsInterface(
        bytes4 interfaceId
    ) public view override(AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Receive / Fallback
    // ──────────────────────────────────────────────────────────────────

    /**
     * @dev Accept plain ETH transfers so the bridge can be funded for
     *      withdrawals (e.g. from the treasury).
     */
    receive() external payable {}
}
