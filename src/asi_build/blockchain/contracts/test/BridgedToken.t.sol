// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/BridgedToken.sol";

contract BridgedTokenTest is Test {
    BridgedToken public token;

    address public deployer = address(0xA);
    address public bridgeAddr = address(0xB);
    address public user1 = address(0xC);
    address public user2 = address(0xD);
    address public rando = address(0xE);

    function setUp() public {
        vm.prank(deployer);
        token = new BridgedToken("Bridged RINGS", "bRINGS", bridgeAddr);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────────────────────────

    function test_Name() public view {
        assertEq(token.name(), "Bridged RINGS");
    }

    function test_Symbol() public view {
        assertEq(token.symbol(), "bRINGS");
    }

    function test_Decimals() public view {
        assertEq(token.decimals(), 18);
    }

    function test_DeployerHasAdminRole() public view {
        assertTrue(token.hasRole(token.DEFAULT_ADMIN_ROLE(), deployer));
    }

    function test_BridgeHasBridgeRole() public view {
        assertTrue(token.hasRole(token.BRIDGE_ROLE(), bridgeAddr));
    }

    function test_ConstructorRevertsZeroBridge() public {
        vm.expectRevert("BridgedToken: zero bridge address");
        new BridgedToken("Test", "TST", address(0));
    }

    // ──────────────────────────────────────────────────────────────────
    //  Minting
    // ──────────────────────────────────────────────────────────────────

    function test_MintByBridge() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 100 ether);

        assertEq(token.balanceOf(user1), 100 ether);
        assertEq(token.totalSupply(), 100 ether);
    }

    function test_MintByNonBridgeReverts() public {
        vm.prank(rando);
        vm.expectRevert();
        token.mint(user1, 100 ether);
    }

    function test_MintByDeployerReverts() public {
        // Deployer has admin role but NOT bridge role
        vm.prank(deployer);
        vm.expectRevert();
        token.mint(user1, 100 ether);
    }

    function test_MintToZeroAddressReverts() public {
        vm.prank(bridgeAddr);
        vm.expectRevert("BridgedToken: mint to zero address");
        token.mint(address(0), 100 ether);
    }

    function test_MintZeroAmountReverts() public {
        vm.prank(bridgeAddr);
        vm.expectRevert("BridgedToken: zero amount");
        token.mint(user1, 0);
    }

    function test_MintMultipleTimes() public {
        vm.startPrank(bridgeAddr);
        token.mint(user1, 10 ether);
        token.mint(user1, 20 ether);
        token.mint(user2, 5 ether);
        vm.stopPrank();

        assertEq(token.balanceOf(user1), 30 ether);
        assertEq(token.balanceOf(user2), 5 ether);
        assertEq(token.totalSupply(), 35 ether);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Burning
    // ──────────────────────────────────────────────────────────────────

    function test_BurnFromByBridge() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 100 ether);

        // User approves bridge to burn
        vm.prank(user1);
        token.approve(bridgeAddr, 50 ether);

        vm.prank(bridgeAddr);
        token.burnFrom(user1, 50 ether);

        assertEq(token.balanceOf(user1), 50 ether);
        assertEq(token.totalSupply(), 50 ether);
    }

    function test_BurnFromByNonBridgeReverts() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 100 ether);

        vm.prank(user1);
        token.approve(rando, 50 ether);

        vm.prank(rando);
        vm.expectRevert();
        token.burnFrom(user1, 50 ether);
    }

    function test_BurnFromWithoutAllowanceReverts() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 100 ether);

        // No approval
        vm.prank(bridgeAddr);
        vm.expectRevert("ERC20: insufficient allowance");
        token.burnFrom(user1, 50 ether);
    }

    function test_BurnFromExceedingBalanceReverts() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 10 ether);

        vm.prank(user1);
        token.approve(bridgeAddr, 20 ether);

        vm.prank(bridgeAddr);
        vm.expectRevert("ERC20: burn amount exceeds balance");
        token.burnFrom(user1, 20 ether);
    }

    // ──────────────────────────────────────────────────────────────────
    //  ERC20 Standard Functionality
    // ──────────────────────────────────────────────────────────────────

    function test_Transfer() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 50 ether);

        vm.prank(user1);
        token.transfer(user2, 20 ether);

        assertEq(token.balanceOf(user1), 30 ether);
        assertEq(token.balanceOf(user2), 20 ether);
    }

    function test_Approve() public {
        vm.prank(user1);
        token.approve(user2, 10 ether);

        assertEq(token.allowance(user1, user2), 10 ether);
    }

    function test_TransferFrom() public {
        vm.prank(bridgeAddr);
        token.mint(user1, 50 ether);

        vm.prank(user1);
        token.approve(user2, 20 ether);

        vm.prank(user2);
        token.transferFrom(user1, user2, 15 ether);

        assertEq(token.balanceOf(user1), 35 ether);
        assertEq(token.balanceOf(user2), 15 ether);
        assertEq(token.allowance(user1, user2), 5 ether);
    }

    // ──────────────────────────────────────────────────────────────────
    //  Access Control — Admin can grant/revoke bridge role
    // ──────────────────────────────────────────────────────────────────

    function test_AdminCanGrantBridgeRole() public {
        address newBridge = address(0xF);
        bytes32 bridgeRole = token.BRIDGE_ROLE();

        vm.prank(deployer);
        token.grantRole(bridgeRole, newBridge);

        assertTrue(token.hasRole(bridgeRole, newBridge));

        // New bridge can mint
        vm.prank(newBridge);
        token.mint(user1, 1 ether);
        assertEq(token.balanceOf(user1), 1 ether);
    }

    function test_AdminCanRevokeBridgeRole() public {
        bytes32 bridgeRole = token.BRIDGE_ROLE();

        vm.prank(deployer);
        token.revokeRole(bridgeRole, bridgeAddr);

        vm.prank(bridgeAddr);
        vm.expectRevert();
        token.mint(user1, 1 ether);
    }

    function test_NonAdminCannotGrantRole() public {
        bytes32 bridgeRole = token.BRIDGE_ROLE();

        vm.prank(rando);
        vm.expectRevert();
        token.grantRole(bridgeRole, rando);
    }

    // ──────────────────────────────────────────────────────────────────
    //  ERC-165
    // ──────────────────────────────────────────────────────────────────

    function test_SupportsAccessControlInterface() public view {
        assertTrue(token.supportsInterface(type(IAccessControl).interfaceId));
    }

    function test_SupportsERC165() public view {
        assertTrue(token.supportsInterface(0x01ffc9a7));
    }

    // ──────────────────────────────────────────────────────────────────
    //  Fuzz
    // ──────────────────────────────────────────────────────────────────

    function testFuzz_MintAndBurn(uint256 amount) public {
        amount = bound(amount, 1, type(uint128).max);

        vm.prank(bridgeAddr);
        token.mint(user1, amount);
        assertEq(token.balanceOf(user1), amount);

        vm.prank(user1);
        token.approve(bridgeAddr, amount);

        vm.prank(bridgeAddr);
        token.burnFrom(user1, amount);
        assertEq(token.balanceOf(user1), 0);
        assertEq(token.totalSupply(), 0);
    }
}
