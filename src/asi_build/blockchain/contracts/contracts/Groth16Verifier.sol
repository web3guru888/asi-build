// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Groth16Verifier
 * @author ASI:BUILD — Rings↔Ethereum Bridge
 * @dev On-chain Groth16 zero-knowledge proof verifier over the BN254
 *      (alt_bn128) curve, using Ethereum precompiles:
 *        • ecAdd      — address 0x06
 *        • ecMul      — address 0x07
 *        • ecPairing  — address 0x08
 *
 *      The verification key is set once at deployment and is immutable.
 *      Two entry points are provided:
 *        1. `verify(a, b, c, input)` — low-level, accepts decoded points.
 *        2. `verifyProof(proof, publicInputs)` — high-level, accepts
 *           ABI-encoded proof bytes and a public-inputs array.
 *
 *      This contract follows the standard pattern produced by snarkjs and
 *      circom tooling.
 *
 * @notice The BN254 curve order is:
 *         p = 21888242871839275222246405745257275088696311157297823662689037894645226208583
 *         (used for scalar-field checks)
 */
contract Groth16Verifier {
    // ──────────────────────────────────────────────────────────────────
    //  Curve structures
    // ──────────────────────────────────────────────────────────────────

    /// @dev Affine point on the G1 group of BN254.
    struct G1Point {
        uint256 X;
        uint256 Y;
    }

    /// @dev Affine point on the G2 group of BN254 (coordinates are
    ///      elements of F_{p^2}, stored as (imaginary, real) per EIP-197).
    struct G2Point {
        uint256[2] X; // [x_imag, x_real]
        uint256[2] Y; // [y_imag, y_real]
    }

    // ──────────────────────────────────────────────────────────────────
    //  Verification key
    // ──────────────────────────────────────────────────────────────────

    /// @dev Full Groth16 verification key.
    struct VerifyingKey {
        G1Point alpha1;
        G2Point beta2;
        G2Point gamma2;
        G2Point delta2;
        G1Point[] IC; // length = number_of_public_inputs + 1
    }

    /// @dev The immutable verification key, set in the constructor.
    VerifyingKey private _vk;

    /// @dev BN254 curve order (prime subgroup order).
    uint256 private constant PRIME_Q =
        21888242871839275222246405745257275088696311157297823662689037894645226208583;

    // ──────────────────────────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────────────────────────

    /**
     * @param alpha1  G1 component of the verification key.
     * @param beta2   G2 component of the verification key.
     * @param gamma2  G2 component of the verification key.
     * @param delta2  G2 component of the verification key.
     * @param ic      Array of G1 points (IC[0..n] where n = public inputs).
     *
     * @dev IC must have at least 2 elements (IC[0] + at least one input).
     */
    constructor(
        G1Point memory alpha1,
        G2Point memory beta2,
        G2Point memory gamma2,
        G2Point memory delta2,
        G1Point[] memory ic
    ) {
        require(ic.length >= 2, "Groth16: IC length must be >= 2");

        _vk.alpha1 = alpha1;
        _vk.beta2 = beta2;
        _vk.gamma2 = gamma2;
        _vk.delta2 = delta2;

        for (uint256 i = 0; i < ic.length; i++) {
            _vk.IC.push(ic[i]);
        }
    }

    // ──────────────────────────────────────────────────────────────────
    //  Public API
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Verify a Groth16 proof given decoded elliptic-curve points
     *         and public inputs.
     *
     * @param a     G1 proof element π_A as [x, y].
     * @param b     G2 proof element π_B as [[x_imag, x_real], [y_imag, y_real]].
     * @param c     G1 proof element π_C as [x, y].
     * @param input Public inputs array (length must equal IC.length - 1).
     *
     * @return True if the proof is valid, false otherwise.
     */
    function verify(
        uint256[2] memory a,
        uint256[2][2] memory b,
        uint256[2] memory c,
        uint256[] memory input
    ) public view returns (bool) {
        require(
            input.length + 1 == _vk.IC.length,
            "Groth16: input length mismatch"
        );

        // Compute the linear combination: vk_x = IC[0] + Σ input[i]·IC[i+1]
        G1Point memory vk_x = G1Point(0, 0);
        vk_x = _addition(vk_x, _vk.IC[0]);

        for (uint256 i = 0; i < input.length; i++) {
            require(input[i] < PRIME_Q, "Groth16: input exceeds field size");
            vk_x = _addition(vk_x, _scalar_mul(_vk.IC[i + 1], input[i]));
        }

        // Verify the pairing equation:
        //   e(-A, B) · e(α, β) · e(vk_x, γ) · e(C, δ) == 1
        //
        // Which is equivalent to checking that the product of pairings is
        // the identity element of GT.
        return
            _pairing4(
                _negate(G1Point(a[0], a[1])),
                G2Point(b[0], b[1]),
                _vk.alpha1,
                _vk.beta2,
                vk_x,
                _vk.gamma2,
                G1Point(c[0], c[1]),
                _vk.delta2
            );
    }

    /**
     * @notice High-level entry point: verify an ABI-encoded proof with
     *         public inputs provided as bytes32 array.
     *
     * @param proof        ABI-encoded (uint256[2] a, uint256[2][2] b, uint256[2] c).
     * @param publicInputs Array of public input values as bytes32.
     *
     * @return True if the proof is valid, false otherwise.
     *
     * @dev The proof bytes are decoded as:
     *        abi.encode(uint256[2], uint256[2][2], uint256[2])
     *      Each publicInput bytes32 is cast to uint256.
     */
    function verifyProof(
        bytes calldata proof,
        bytes32[] calldata publicInputs
    ) external view returns (bool) {
        // Decode the three proof elements from the packed bytes.
        (
            uint256[2] memory a,
            uint256[2][2] memory b,
            uint256[2] memory c
        ) = abi.decode(proof, (uint256[2], uint256[2][2], uint256[2]));

        // Convert bytes32 public inputs to uint256 array.
        uint256[] memory input = new uint256[](publicInputs.length);
        for (uint256 i = 0; i < publicInputs.length; i++) {
            input[i] = uint256(publicInputs[i]);
        }

        return verify(a, b, c, input);
    }

    /**
     * @notice Return the number of public inputs expected by this verifier.
     * @return The number of public inputs (IC.length - 1).
     */
    function getInputCount() external view returns (uint256) {
        return _vk.IC.length - 1;
    }

    // ──────────────────────────────────────────────────────────────────
    //  BN254 curve operations (internal)
    // ──────────────────────────────────────────────────────────────────

    /**
     * @dev Negate a G1 point: (x, y) → (x, p - y).
     *      The point at infinity (0, 0) is its own negation.
     */
    function _negate(G1Point memory p) internal pure returns (G1Point memory) {
        // The prime modulus of the base field.
        uint256 q = 21888242871839275222246405745257275088548364400416034343698204186575808495617;
        if (p.X == 0 && p.Y == 0) {
            return G1Point(0, 0);
        }
        return G1Point(p.X, q - (p.Y % q));
    }

    /**
     * @dev Add two G1 points using the ecAdd precompile (address 0x06).
     */
    function _addition(
        G1Point memory p1,
        G1Point memory p2
    ) internal view returns (G1Point memory r) {
        uint256[4] memory input_;
        input_[0] = p1.X;
        input_[1] = p1.Y;
        input_[2] = p2.X;
        input_[3] = p2.Y;

        bool success;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            success := staticcall(sub(gas(), 2000), 6, input_, 0x80, r, 0x40)
        }
        require(success, "Groth16: ecAdd failed");
    }

    /**
     * @dev Scalar multiplication of a G1 point using the ecMul precompile
     *      (address 0x07).
     */
    function _scalar_mul(
        G1Point memory p,
        uint256 s
    ) internal view returns (G1Point memory r) {
        uint256[3] memory input_;
        input_[0] = p.X;
        input_[1] = p.Y;
        input_[2] = s;

        bool success;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            success := staticcall(sub(gas(), 2000), 7, input_, 0x60, r, 0x40)
        }
        require(success, "Groth16: ecMul failed");
    }

    /**
     * @dev Verify a product of 4 pairings equals the identity element of GT.
     *
     *      Uses the ecPairing precompile (address 0x08) which accepts
     *      a sequence of (G1, G2) pairs and returns 1 iff
     *      ∏ e(G1_i, G2_i) == 1.
     *
     * @return True if the pairing check passes.
     */
    function _pairing4(
        G1Point memory a1,
        G2Point memory a2,
        G1Point memory b1,
        G2Point memory b2,
        G1Point memory c1,
        G2Point memory c2,
        G1Point memory d1,
        G2Point memory d2
    ) internal view returns (bool) {
        uint256[24] memory input_;

        // Pair 1: (-A, B)
        input_[0] = a1.X;
        input_[1] = a1.Y;
        input_[2] = a2.X[1]; // real part first per EIP-197
        input_[3] = a2.X[0]; // imaginary part
        input_[4] = a2.Y[1];
        input_[5] = a2.Y[0];

        // Pair 2: (α, β)
        input_[6] = b1.X;
        input_[7] = b1.Y;
        input_[8] = b2.X[1];
        input_[9] = b2.X[0];
        input_[10] = b2.Y[1];
        input_[11] = b2.Y[0];

        // Pair 3: (vk_x, γ)
        input_[12] = c1.X;
        input_[13] = c1.Y;
        input_[14] = c2.X[1];
        input_[15] = c2.X[0];
        input_[16] = c2.Y[1];
        input_[17] = c2.Y[0];

        // Pair 4: (C, δ)
        input_[18] = d1.X;
        input_[19] = d1.Y;
        input_[20] = d2.X[1];
        input_[21] = d2.X[0];
        input_[22] = d2.Y[1];
        input_[23] = d2.Y[0];

        uint256[1] memory out;
        bool success;

        // solhint-disable-next-line no-inline-assembly
        assembly {
            success := staticcall(
                sub(gas(), 2000),
                8,
                input_,
                0x300, // 24 * 32 = 768 bytes
                out,
                0x20
            )
        }
        require(success, "Groth16: pairing precompile failed");
        return out[0] != 0;
    }
}
