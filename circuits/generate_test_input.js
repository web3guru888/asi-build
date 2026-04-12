/**
 * Generate valid test inputs for the WithdrawalProof circuit.
 *
 * Computes Poseidon hashes to build a valid Merkle tree and
 * produces an input.json that the circuit will accept.
 */
const { poseidon2, poseidon3 } = require("poseidon-lite");

const LEVELS = 10;

// Test values
const secret = BigInt(42);
const balance = BigInt(1000);
const nonce = BigInt(1);
const amount = BigInt(100);

// Compute the account leaf: Poseidon(secret, balance, nonce)
const leaf = poseidon3([secret, balance, nonce]);
console.log("Leaf hash:", leaf.toString());

// Build a Merkle path with random siblings
// For testing, siblings are just constants (0, 1, 2, ...)
const pathElements = [];
const pathIndices = [];
let currentHash = leaf;

for (let i = 0; i < LEVELS; i++) {
    // Put the real hash on the left (pathIndex = 0)
    const sibling = BigInt(i + 100);
    pathElements.push(sibling.toString());
    pathIndices.push("0"); // our node is on the left

    // Hash: Poseidon(currentHash, sibling)
    currentHash = poseidon2([currentHash, sibling]);
}

const stateRoot = currentHash;
console.log("State root:", stateRoot.toString());

// Compute recipientHash = Poseidon(recipientAddress, 0)
// Use a dummy recipient address
const recipientAddress = BigInt("0x35C3770470F57560beBd1C6C74366b0297110Bc2");
const recipientHash = poseidon2([recipientAddress, BigInt(0)]);
console.log("Recipient hash:", recipientHash.toString());

// Build input
const input = {
    amount: amount.toString(),
    nonce: nonce.toString(),
    recipientHash: recipientHash.toString(),
    stateRoot: stateRoot.toString(),
    secret: secret.toString(),
    balance: balance.toString(),
    pathElements: pathElements,
    pathIndices: pathIndices,
};

const fs = require("fs");
fs.writeFileSync("build/input.json", JSON.stringify(input, null, 2));
console.log("\nWritten to build/input.json");
console.log(JSON.stringify(input, null, 2));
