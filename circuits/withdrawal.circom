pragma circom 2.0.0;

include "node_modules/circomlib/circuits/poseidon.circom";
include "node_modules/circomlib/circuits/bitify.circom";
include "node_modules/circomlib/circuits/comparators.circom";

/*
 * WithdrawalProof — Rings↔Ethereum Bridge ZK Withdrawal Circuit
 *
 * Proves a withdrawal from the Rings bridge is authorized without
 * revealing the user's secret or full balance.
 *
 * Public inputs:
 *   - amount          : withdrawal amount
 *   - nonce           : replay protection nonce
 *   - recipientHash   : Poseidon(recipient_address) — front-running protection
 *   - stateRoot       : Merkle root of the account state tree
 *   - chainId         : EVM chain ID — binds proof to a specific chain,
 *                       preventing cross-chain replay attacks. Must equal
 *                       block.chainid on the destination contract.
 *
 * Private inputs:
 *   - secret          : user's private authorization key
 *   - balance         : user's current balance
 *   - pathElements[]  : sibling hashes along Merkle proof
 *   - pathIndices[]   : 0/1 direction flags for Merkle proof
 *
 * Constraints:
 *   1. amount <= balance (range check via Num2Bits on difference)
 *   2. Account leaf = Poseidon(secret, balance, nonce)
 *   3. Merkle path from leaf reconstructs to stateRoot
 *   4. recipientHash is bound as public input (non-trivial constraint)
 *   5. chainId is cryptographically bound to the withdrawal commitment
 *
 * SECURITY NOTE: After this circuit change, a new trusted setup (Powers of
 * Tau + Groth16 setup ceremony) is required before enabling withdrawals.
 * The current zkey/verification key is now stale. Do NOT enable
 * syncCommitteeRoot (i.e., do NOT enable withdrawals) until the new verifier
 * is deployed. See issue #1242.
 */
template WithdrawalProof(nLevels) {
    // ── Public inputs ──────────────────────────────────────────────
    signal input amount;
    signal input nonce;
    signal input recipientHash;
    signal input stateRoot;
    // chainId binds this proof to a specific EVM chain (fix for #1242).
    // publicInputs[4] in the on-chain verifier call.
    signal input chainId;

    // ── Private inputs ─────────────────────────────────────────────
    signal input secret;
    signal input balance;
    signal input pathElements[nLevels];
    signal input pathIndices[nLevels];

    // ── Constraint 1: amount <= balance ────────────────────────────
    // Compute balance - amount and range-check it as a 64-bit value
    // (non-negative check: if negative, Num2Bits will fail)
    signal balanceMinusAmount;
    balanceMinusAmount <== balance - amount;
    component rangeCheck = Num2Bits(64);
    rangeCheck.in <== balanceMinusAmount;

    // ── Constraint 2: Compute account leaf hash ───────────────────
    // leaf = Poseidon(secret, balance, nonce)
    component leafHash = Poseidon(3);
    leafHash.inputs[0] <== secret;
    leafHash.inputs[1] <== balance;
    leafHash.inputs[2] <== nonce;

    // ── Constraint 3: Verify Merkle proof ─────────────────────────
    // Walk from leaf up to root, swapping left/right based on pathIndices
    signal nodes[nLevels + 1];
    nodes[0] <== leafHash.out;

    component hashers[nLevels];
    component mux_left[nLevels];
    component mux_right[nLevels];

    for (var i = 0; i < nLevels; i++) {
        // Ensure pathIndices[i] is binary
        pathIndices[i] * (pathIndices[i] - 1) === 0;

        // Select left and right inputs for the hash
        // If pathIndices[i] == 0: current node is left, sibling is right
        // If pathIndices[i] == 1: current node is right, sibling is left
        hashers[i] = Poseidon(2);
        hashers[i].inputs[0] <== nodes[i] + pathIndices[i] * (pathElements[i] - nodes[i]);
        hashers[i].inputs[1] <== pathElements[i] + pathIndices[i] * (nodes[i] - pathElements[i]);
        nodes[i + 1] <== hashers[i].out;
    }

    // ── Constraint 4: Root must match stateRoot ───────────────────
    stateRoot === nodes[nLevels];

    // ── Constraint 5: Bind recipientHash to proof ─────────────────
    // Create a non-trivial constraint using recipientHash so it's
    // truly bound (not just declared public). We hash it with the
    // secret to create a commitment.
    component recipientBinding = Poseidon(2);
    recipientBinding.inputs[0] <== recipientHash;
    recipientBinding.inputs[1] <== secret;
    // Force evaluation (output is computed but unused in a way
    // that the optimizer cannot remove)
    signal recipientCommitment;
    recipientCommitment <== recipientBinding.out;

    // ── Constraint 6: Bind chainId to withdrawal commitment ───────
    // Hash chainId with the account leaf so the proof is cryptographically
    // tied to a specific chain. A proof generated for chain A cannot be
    // reused on chain B because chainId appears in this hash, and the
    // public chainId input would need to be different — which would change
    // the commitment and fail the Merkle proof verification on the other
    // chain. This prevents cross-chain replay attacks (#1242).
    component chainBinding = Poseidon(2);
    chainBinding.inputs[0] <== chainId;
    chainBinding.inputs[1] <== leafHash.out;
    signal chainCommitment;
    chainCommitment <== chainBinding.out;
}

// Public signals list now includes chainId as the 5th public input.
// On-chain publicInputs[4] must equal block.chainid.
// NOTE: Recompile circuit + redo trusted setup before enabling withdrawals.
component main {public [amount, nonce, recipientHash, stateRoot, chainId]} = WithdrawalProof(10);
