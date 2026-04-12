// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title BridgedToken
 * @author ASI:BUILD — Rings↔Ethereum Bridge
 * @dev ERC20 token minted/burned exclusively by the bridge contract.
 *
 *      When a user deposits native tokens on the Rings side, the bridge
 *      mints an equivalent amount of BridgedToken on Ethereum.  When the
 *      user withdraws back to Rings, the bridge burns the tokens.
 *
 *      Only addresses holding BRIDGE_ROLE may mint or burn.  The deployer
 *      receives DEFAULT_ADMIN_ROLE so additional bridges or migration
 *      contracts can be authorised later.
 *
 * @notice This token has no value of its own — it is a 1:1 receipt for
 *         assets locked on the Rings network.
 */
contract BridgedToken is ERC20, ERC20Burnable, AccessControl {
    // ──────────────────────────────────────────────────────────────────
    //  Constants
    // ──────────────────────────────────────────────────────────────────

    /// @dev Role that allows minting and burning tokens (assigned to bridge).
    bytes32 public constant BRIDGE_ROLE = keccak256("BRIDGE_ROLE");

    // ──────────────────────────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────────────────────────

    /**
     * @param name_         Human-readable token name  (e.g. "Bridged RINGS").
     * @param symbol_       Token ticker symbol         (e.g. "bRINGS").
     * @param bridgeAddress Address of the RingsBridge contract.
     *
     * @dev The deployer (`msg.sender`) is granted DEFAULT_ADMIN_ROLE so
     *      that governance can add/revoke bridge addresses later.
     *      `bridgeAddress` is immediately granted BRIDGE_ROLE.
     */
    constructor(
        string memory name_,
        string memory symbol_,
        address bridgeAddress
    ) ERC20(name_, symbol_) {
        require(bridgeAddress != address(0), "BridgedToken: zero bridge address");

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(BRIDGE_ROLE, bridgeAddress);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Bridge-only mint / burn
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Mint `amount` tokens to `to`.
     * @dev Called by the bridge when a withdrawal proof is verified.
     * @param to     Recipient address on Ethereum.
     * @param amount Number of tokens (in wei, 18 decimals).
     */
    function mint(address to, uint256 amount) external onlyRole(BRIDGE_ROLE) {
        require(to != address(0), "BridgedToken: mint to zero address");
        require(amount > 0, "BridgedToken: zero amount");
        _mint(to, amount);
    }

    /**
     * @notice Burn `amount` tokens from `from`.
     * @dev Called by the bridge when a user deposits tokens back to Rings.
     *      The bridge must hold sufficient allowance or be the `from` address.
     * @param from   Address whose tokens will be burned.
     * @param amount Number of tokens to burn.
     */
    function burnFrom(
        address from,
        uint256 amount
    ) public override onlyRole(BRIDGE_ROLE) {
        // ERC20Burnable.burnFrom already handles allowance checks, but
        // we override to enforce BRIDGE_ROLE gating.
        super.burnFrom(from, amount);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Metadata overrides
    // ──────────────────────────────────────────────────────────────────

    /**
     * @notice Returns the number of decimals used for display.
     * @return Always 18, matching ETH native precision.
     */
    function decimals() public pure override returns (uint8) {
        return 18;
    }

    // ──────────────────────────────────────────────────────────────────
    //  ERC-165 supportsInterface resolution
    // ──────────────────────────────────────────────────────────────────

    /**
     * @dev See {IERC165-supportsInterface}.
     *      Resolves the diamond-inheritance ambiguity between ERC20 and
     *      AccessControl (both inherit ERC165).
     */
    function supportsInterface(
        bytes4 interfaceId
    ) public view override(AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
