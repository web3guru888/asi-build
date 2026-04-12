// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./AuditTrail.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AuditFactory
 * @dev Factory contract for creating and managing multiple audit trail contracts
 * @notice This contract allows organizations to create their own audit trail instances
 */
contract AuditFactory is Ownable {
    
    // Structure to store audit trail information
    struct AuditTrailInfo {
        address contractAddress;
        string name;
        string description;
        address creator;
        uint256 createdAt;
        bool active;
    }
    
    // Mapping of audit trail ID to info
    mapping(uint256 => AuditTrailInfo) public auditTrails;
    
    // Mapping of creator address to their audit trails
    mapping(address => uint256[]) public creatorAuditTrails;
    
    // Counter for audit trail instances
    uint256 private _auditTrailCounter;
    
    // Events
    event AuditTrailCreated(
        uint256 indexed auditTrailId,
        address indexed contractAddress,
        address indexed creator,
        string name
    );
    
    event AuditTrailDeactivated(
        uint256 indexed auditTrailId,
        address indexed contractAddress
    );
    
    event AuditTrailActivated(
        uint256 indexed auditTrailId,
        address indexed contractAddress
    );
    
    /**
     * @dev Constructor
     * @param initialOwner The address to be granted owner role
     */
    constructor(address initialOwner) {
        // OZ v4.9.6: Ownable sets msg.sender as owner; transfer if different
        if (initialOwner != msg.sender) {
            transferOwnership(initialOwner);
        }
    }
    
    /**
     * @dev Create a new audit trail contract
     * @param name Name for the audit trail
     * @param description Description of the audit trail purpose
     * @param admin Admin address for the new audit trail contract
     */
    function createAuditTrail(
        string memory name,
        string memory description,
        address admin
    ) external returns (uint256, address) {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(admin != address(0), "Admin address cannot be zero");
        
        _auditTrailCounter++;
        uint256 auditTrailId = _auditTrailCounter;
        
        // Deploy new AuditTrail contract
        AuditTrail auditTrail = new AuditTrail(admin);
        address auditTrailAddress = address(auditTrail);
        
        // Store audit trail info
        auditTrails[auditTrailId] = AuditTrailInfo({
            contractAddress: auditTrailAddress,
            name: name,
            description: description,
            creator: msg.sender,
            createdAt: block.timestamp,
            active: true
        });
        
        // Add to creator's list
        creatorAuditTrails[msg.sender].push(auditTrailId);
        
        emit AuditTrailCreated(auditTrailId, auditTrailAddress, msg.sender, name);
        
        return (auditTrailId, auditTrailAddress);
    }
    
    /**
     * @dev Get audit trail information
     * @param auditTrailId The ID of the audit trail
     */
    function getAuditTrailInfo(uint256 auditTrailId) external view returns (AuditTrailInfo memory) {
        require(auditTrailId > 0 && auditTrailId <= _auditTrailCounter, "Invalid audit trail ID");
        return auditTrails[auditTrailId];
    }
    
    /**
     * @dev Get all audit trails created by a specific address
     * @param creator The creator address
     */
    function getAuditTrailsByCreator(address creator) external view returns (uint256[] memory) {
        return creatorAuditTrails[creator];
    }
    
    /**
     * @dev Get total number of audit trails
     */
    function getTotalAuditTrails() external view returns (uint256) {
        return _auditTrailCounter;
    }
    
    /**
     * @dev Deactivate an audit trail (only owner or creator)
     * @param auditTrailId The ID of the audit trail to deactivate
     */
    function deactivateAuditTrail(uint256 auditTrailId) external {
        require(auditTrailId > 0 && auditTrailId <= _auditTrailCounter, "Invalid audit trail ID");
        AuditTrailInfo storage info = auditTrails[auditTrailId];
        require(
            msg.sender == owner() || msg.sender == info.creator,
            "Only owner or creator can deactivate"
        );
        require(info.active, "Audit trail already deactivated");
        
        info.active = false;
        
        emit AuditTrailDeactivated(auditTrailId, info.contractAddress);
    }
    
    /**
     * @dev Activate an audit trail (only owner or creator)
     * @param auditTrailId The ID of the audit trail to activate
     */
    function activateAuditTrail(uint256 auditTrailId) external {
        require(auditTrailId > 0 && auditTrailId <= _auditTrailCounter, "Invalid audit trail ID");
        AuditTrailInfo storage info = auditTrails[auditTrailId];
        require(
            msg.sender == owner() || msg.sender == info.creator,
            "Only owner or creator can activate"
        );
        require(!info.active, "Audit trail already active");
        
        info.active = true;
        
        emit AuditTrailActivated(auditTrailId, info.contractAddress);
    }
    
    /**
     * @dev Check if an audit trail is active
     * @param auditTrailId The ID of the audit trail
     */
    function isAuditTrailActive(uint256 auditTrailId) external view returns (bool) {
        require(auditTrailId > 0 && auditTrailId <= _auditTrailCounter, "Invalid audit trail ID");
        return auditTrails[auditTrailId].active;
    }
    
    /**
     * @dev Get all active audit trails (paginated)
     * @param offset Starting index
     * @param limit Maximum number of results
     */
    function getActiveAuditTrails(
        uint256 offset,
        uint256 limit
    ) external view returns (AuditTrailInfo[] memory) {
        require(limit > 0 && limit <= 100, "Limit must be between 1 and 100");
        
        uint256 activeCount = 0;
        
        // Count active audit trails
        for (uint256 i = 1; i <= _auditTrailCounter; i++) {
            if (auditTrails[i].active) {
                activeCount++;
            }
        }
        
        require(offset < activeCount, "Offset exceeds active count");
        
        uint256 resultCount = activeCount - offset;
        if (resultCount > limit) {
            resultCount = limit;
        }
        
        AuditTrailInfo[] memory result = new AuditTrailInfo[](resultCount);
        uint256 currentIndex = 0;
        uint256 skipped = 0;
        
        for (uint256 i = 1; i <= _auditTrailCounter && currentIndex < resultCount; i++) {
            if (auditTrails[i].active) {
                if (skipped >= offset) {
                    result[currentIndex] = auditTrails[i];
                    currentIndex++;
                } else {
                    skipped++;
                }
            }
        }
        
        return result;
    }
}