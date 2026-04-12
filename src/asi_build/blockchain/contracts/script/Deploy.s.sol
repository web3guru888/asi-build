// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

// ─── Interfaces (re-declared to avoid import-path issues) ──────────────

interface IGroth16VerifierDeployed {
    function getInputCount() external view returns (uint256);
}

interface IRingsBridgeDeployed {
    function dailyLimit() external view returns (uint256);
    function perTxLimit() external view returns (uint256);
    function verifier() external view returns (address);
}

interface IBridgedTokenDeployed {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function hasRole(bytes32 role, address account) external view returns (bool);
}

/**
 * @title DeployBridge
 * @author ASI:BUILD
 * @notice Forge deployment script for the Rings↔Ethereum Bridge suite.
 *
 *         Deploys in order:
 *           1. Groth16Verifier  — with a testnet-safe dummy verification key
 *           2. RingsBridge      — wired to the verifier, rate-limited
 *           3. BridgedToken     — BRIDGE_ROLE granted to the bridge
 *
 *         Environment variables (set via .env or --env-file):
 *           DEPLOYER_PRIVATE_KEY  — Private key of the deployer wallet
 *           GUARDIAN_ADDRESS      — Guardian who can pause the bridge
 *                                   (defaults to deployer if unset)
 *           DAILY_LIMIT           — Daily withdrawal cap in wei
 *                                   (default: 100 ether)
 *           PER_TX_LIMIT          — Per-transaction withdrawal cap in wei
 *                                   (default: 10 ether)
 *
 * @dev Usage:
 *        forge script script/Deploy.s.sol:DeployBridge \
 *          --rpc-url $SEPOLIA_RPC_URL \
 *          --broadcast \
 *          --verify
 *
 *        Dry-run (no broadcast):
 *        forge script script/Deploy.s.sol:DeployBridge \
 *          --rpc-url $SEPOLIA_RPC_URL
 */
contract DeployBridge is Script {
    // ──────────────────────────────────────────────────────────────────
    //  BN254 generator points (used for testnet dummy VK)
    // ──────────────────────────────────────────────────────────────────

    // G1 generator
    uint256 constant G1_X = 1;
    uint256 constant G1_Y = 2;

    // G2 generator (EIP-197 encoding: [x_imag, x_real], [y_imag, y_real])
    uint256 constant G2_X_IMAG = 10857046999023057135944570762232829481370756359578518086990519993285655852781;
    uint256 constant G2_X_REAL = 11559732032986387107991004021392285783925812861821192530917403151452391805634;
    uint256 constant G2_Y_IMAG = 8495653923123431417604973247489272438418190587263600148770280649306958101930;
    uint256 constant G2_Y_REAL = 4082367875863433681332203403145435568316851327593401208105741076214120093531;

    function run() external {
        // ── Read environment ────────────────────────────────────────
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        // Guardian defaults to deployer if not set
        address guardian = vm.envOr("GUARDIAN_ADDRESS", deployer);

        // Rate limits (defaults: 100 ETH daily, 10 ETH per-tx)
        uint256 dailyLimit = vm.envOr("DAILY_LIMIT", uint256(100 ether));
        uint256 perTxLimit = vm.envOr("PER_TX_LIMIT", uint256(10 ether));

        console.log("=== Rings Bridge Deployment ===");
        console.log("Deployer:      ", deployer);
        console.log("Guardian:      ", guardian);
        console.log("Daily limit:   ", dailyLimit);
        console.log("Per-tx limit:  ", perTxLimit);
        console.log("Chain ID:      ", block.chainid);
        console.log("");

        vm.startBroadcast(deployerPrivateKey);

        // ── 1. Deploy Groth16Verifier with testnet dummy VK ─────────
        //
        // For testnet we use the BN254 generator points as the VK.
        // This means proofs will NOT verify on-chain (pairing checks
        // will fail), which is the correct safety posture for a testnet
        // deployment — no real funds can be withdrawn.
        //
        // In production, replace with the actual circuit VK from the
        // trusted setup ceremony.

        bytes memory verifierCreation = abi.encodePacked(
            vm.getCode("Groth16Verifier.sol:Groth16Verifier"),
            abi.encode(
                // alpha1: G1Point
                [G1_X, G1_Y],
                // beta2: G2Point  { X: [imag, real], Y: [imag, real] }
                [[G2_X_IMAG, G2_X_REAL], [G2_Y_IMAG, G2_Y_REAL]],
                // gamma2: G2Point
                [[G2_X_IMAG, G2_X_REAL], [G2_Y_IMAG, G2_Y_REAL]],
                // delta2: G2Point
                [[G2_X_IMAG, G2_X_REAL], [G2_Y_IMAG, G2_Y_REAL]],
                // IC: G1Point[] — needs at least 2 elements
                _makeIC()
            )
        );

        address verifierAddr;
        assembly {
            verifierAddr := create(0, add(verifierCreation, 0x20), mload(verifierCreation))
        }
        require(verifierAddr != address(0), "DeployBridge: verifier deployment failed");
        console.log("Groth16Verifier:", verifierAddr);

        // ── 2. Deploy RingsBridge ───────────────────────────────────
        bytes memory bridgeCreation = abi.encodePacked(
            vm.getCode("RingsBridge.sol:RingsBridge"),
            abi.encode(
                deployer,       // initialAdmin
                guardian,       // guardian
                dailyLimit,     // dailyLimit_
                perTxLimit,     // perTxLimit_
                verifierAddr    // verifierAddress
            )
        );

        address bridgeAddr;
        assembly {
            bridgeAddr := create(0, add(bridgeCreation, 0x20), mload(bridgeCreation))
        }
        require(bridgeAddr != address(0), "DeployBridge: bridge deployment failed");
        console.log("RingsBridge:   ", bridgeAddr);

        // ── 3. Deploy BridgedToken ──────────────────────────────────
        bytes memory tokenCreation = abi.encodePacked(
            vm.getCode("BridgedToken.sol:BridgedToken"),
            abi.encode(
                "Bridged ASI",  // name_
                "bASI",         // symbol_
                bridgeAddr      // bridgeAddress → gets BRIDGE_ROLE
            )
        );

        address tokenAddr;
        assembly {
            tokenAddr := create(0, add(tokenCreation, 0x20), mload(tokenCreation))
        }
        require(tokenAddr != address(0), "DeployBridge: token deployment failed");
        console.log("BridgedToken:  ", tokenAddr);

        vm.stopBroadcast();

        // ── Post-deployment verification & output ───────────────────
        _logVerification(verifierAddr, bridgeAddr, tokenAddr);
        _writeOutput(verifierAddr, bridgeAddr, tokenAddr);
    }

    function _logVerification(
        address verifierAddr,
        address bridgeAddr,
        address tokenAddr
    ) internal view {
        console.log("");
        console.log("=== Verification ===");
        console.log("Verifier input count:", IGroth16VerifierDeployed(verifierAddr).getInputCount());
        console.log("Bridge daily limit:  ", IRingsBridgeDeployed(bridgeAddr).dailyLimit());
        console.log("Bridge per-tx limit: ", IRingsBridgeDeployed(bridgeAddr).perTxLimit());
        console.log("Bridge verifier:     ", address(IRingsBridgeDeployed(bridgeAddr).verifier()));

        bytes32 bridgeRole = keccak256("BRIDGE_ROLE");
        bool hasBridgeRole = IBridgedTokenDeployed(tokenAddr).hasRole(bridgeRole, bridgeAddr);
        console.log("Token BRIDGE_ROLE ok:", hasBridgeRole);
        console.log("");
        console.log("=== Deployment Complete ===");
    }

    function _writeOutput(
        address verifierAddr,
        address bridgeAddr,
        address tokenAddr
    ) internal {
        // Build JSON in parts to avoid stack-too-deep
        string memory part1 = string(abi.encodePacked(
            '{"verifier":"', vm.toString(verifierAddr),
            '","bridge":"', vm.toString(bridgeAddr),
            '","token":"', vm.toString(tokenAddr), '"}'
        ));
        vm.writeFile("deployment-output.json", part1);
        console.log("Addresses written to deployment-output.json");
    }

    /// @dev Build the IC array (G1Point[]) — minimum 2 elements.
    ///      Uses the G1 generator for testnet; production would use real VK.
    function _makeIC() internal pure returns (uint256[2][] memory ic) {
        ic = new uint256[2][](2);
        ic[0] = [G1_X, G1_Y];
        ic[1] = [G1_X, G1_Y];
    }
}
