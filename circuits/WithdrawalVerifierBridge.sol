// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title WithdrawalVerifierBridge
 * @author ASI:BUILD — Rings↔Ethereum Bridge
 * @dev Wraps the snarkjs-generated Groth16 verifier to conform to the
 *      IGroth16Verifier interface expected by RingsBridge.sol.
 *
 *      The inner verifier uses the standard snarkjs calling convention:
 *        verifyProof(uint[2] _pA, uint[2][2] _pB, uint[2] _pC, uint[4] _pubSignals)
 *
 *      This wrapper accepts:
 *        verifyProof(bytes proof, bytes32[] publicInputs)
 *
 *      Proof encoding (256 bytes):
 *        [0:32]   a[0]
 *        [32:64]  a[1]
 *        [64:96]  b[0][0]
 *        [96:128] b[0][1]
 *        [128:160] b[1][0]
 *        [160:192] b[1][1]
 *        [192:224] c[0]
 *        [224:256] c[1]
 *
 *      Public inputs are 4 x bytes32 (amount, nonce, recipientHash, stateRoot).
 */

// ─── Interface matching RingsBridge expectations ────────────────────
interface IGroth16Verifier {
    function verifyProof(
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external view returns (bool);
}

// ─── Inner verifier interface (snarkjs standard) ────────────────────
interface ISnarkJSVerifier {
    function verifyProof(
        uint[2] calldata _pA,
        uint[2][2] calldata _pB,
        uint[2] calldata _pC,
        uint[4] calldata _pubSignals
    ) external view returns (bool);
}

contract WithdrawalVerifierBridge is IGroth16Verifier {

    /// @dev The snarkjs-generated verifier with real VK baked in.
    ISnarkJSVerifier public immutable innerVerifier;

    constructor(address _innerVerifier) {
        require(_innerVerifier != address(0), "zero address");
        innerVerifier = ISnarkJSVerifier(_innerVerifier);
    }

    /**
     * @notice Verify a Groth16 proof using the bridge's standard interface.
     * @param proof ABI-encoded proof (256 bytes: a[2], b[2][2], c[2]).
     * @param publicInputs Array of 4 public inputs as bytes32.
     * @return True if the proof is valid.
     */
    function verifyProof(
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external view override returns (bool) {
        require(proof.length == 256, "invalid proof length");
        require(publicInputs.length == 4, "need 4 public inputs");

        // Decode proof components
        uint[2] memory a;
        uint[2][2] memory b;
        uint[2] memory c;

        a[0] = uint256(bytes32(proof[0:32]));
        a[1] = uint256(bytes32(proof[32:64]));
        b[0][0] = uint256(bytes32(proof[64:96]));
        b[0][1] = uint256(bytes32(proof[96:128]));
        b[1][0] = uint256(bytes32(proof[128:160]));
        b[1][1] = uint256(bytes32(proof[160:192]));
        c[0] = uint256(bytes32(proof[192:224]));
        c[1] = uint256(bytes32(proof[224:256]));

        // Decode public inputs
        uint[4] memory pubSignals;
        for (uint i = 0; i < 4; i++) {
            pubSignals[i] = uint256(publicInputs[i]);
        }

        return innerVerifier.verifyProof(a, b, c, pubSignals);
    }
}
