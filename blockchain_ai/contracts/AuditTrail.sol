// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title AuditTrail
 * @dev Smart contract for blockchain-based audit trail system
 * @notice This contract provides immutable audit logging with cryptographic verification
 */
contract AuditTrail is AccessControl, ReentrancyGuard {
    using Counters for Counters.Counter;
    
    // Role definitions
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");
    
    // Counter for audit entries
    Counters.Counter private _auditCounter;
    
    // Audit entry structure
    struct AuditEntry {
        uint256 id;
        address auditor;
        string dataHash; // IPFS hash of the actual data
        string signature; // Cryptographic signature
        string eventType;
        string description;
        uint256 timestamp;
        string metadata; // JSON metadata
        bool verified;
        address verifier;
        uint256 verificationTimestamp;
    }
    
    // Mapping of audit ID to audit entry
    mapping(uint256 => AuditEntry) public auditEntries;
    
    // Mapping of data hash to audit ID for quick lookup
    mapping(string => uint256) public hashToAuditId;
    
    // Events
    event AuditEntryCreated(
        uint256 indexed auditId,
        address indexed auditor,
        string dataHash,
        string eventType,
        uint256 timestamp
    );
    
    event AuditEntryVerified(
        uint256 indexed auditId,
        address indexed verifier,
        uint256 timestamp
    );
    
    event AuditEntryQueried(
        uint256 indexed auditId,
        address indexed querier,
        uint256 timestamp
    );
    
    /**
     * @dev Constructor
     * @param admin The address to be granted admin role
     */
    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(AUDITOR_ROLE, admin);
        _grantRole(VERIFIER_ROLE, admin);
    }
    
    /**
     * @dev Create a new audit entry
     * @param dataHash IPFS hash of the audit data
     * @param signature Cryptographic signature of the data
     * @param eventType Type of event being audited
     * @param description Human-readable description
     * @param metadata Additional metadata in JSON format
     */
    function createAuditEntry(
        string memory dataHash,
        string memory signature,
        string memory eventType,
        string memory description,
        string memory metadata
    ) external onlyRole(AUDITOR_ROLE) nonReentrant returns (uint256) {
        require(bytes(dataHash).length > 0, "Data hash cannot be empty");
        require(bytes(signature).length > 0, "Signature cannot be empty");
        require(hashToAuditId[dataHash] == 0, "Audit entry with this hash already exists");
        
        _auditCounter.increment();
        uint256 auditId = _auditCounter.current();
        
        auditEntries[auditId] = AuditEntry({
            id: auditId,
            auditor: msg.sender,
            dataHash: dataHash,
            signature: signature,
            eventType: eventType,
            description: description,
            timestamp: block.timestamp,
            metadata: metadata,
            verified: false,
            verifier: address(0),
            verificationTimestamp: 0
        });
        
        hashToAuditId[dataHash] = auditId;
        
        emit AuditEntryCreated(auditId, msg.sender, dataHash, eventType, block.timestamp);
        
        return auditId;
    }
    
    /**
     * @dev Verify an audit entry
     * @param auditId The ID of the audit entry to verify
     */
    function verifyAuditEntry(uint256 auditId) external onlyRole(VERIFIER_ROLE) nonReentrant {
        require(auditId > 0 && auditId <= _auditCounter.current(), "Invalid audit ID");
        require(!auditEntries[auditId].verified, "Audit entry already verified");
        
        auditEntries[auditId].verified = true;
        auditEntries[auditId].verifier = msg.sender;
        auditEntries[auditId].verificationTimestamp = block.timestamp;
        
        emit AuditEntryVerified(auditId, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Get audit entry by ID
     * @param auditId The ID of the audit entry
     */
    function getAuditEntry(uint256 auditId) external view returns (AuditEntry memory) {
        require(auditId > 0 && auditId <= _auditCounter.current(), "Invalid audit ID");
        
        return auditEntries[auditId];
    }
    
    /**
     * @dev Get audit entry by data hash
     * @param dataHash The IPFS hash of the audit data
     */
    function getAuditEntryByHash(string memory dataHash) external view returns (AuditEntry memory) {
        uint256 auditId = hashToAuditId[dataHash];
        require(auditId > 0, "Audit entry not found");
        
        return auditEntries[auditId];
    }
    
    /**
     * @dev Get total number of audit entries
     */
    function getTotalAuditEntries() external view returns (uint256) {
        return _auditCounter.current();
    }
    
    /**
     * @dev Emit query event for tracking access
     * @param auditId The ID of the audit entry being queried
     */
    function recordQuery(uint256 auditId) external {
        require(auditId > 0 && auditId <= _auditCounter.current(), "Invalid audit ID");
        
        emit AuditEntryQueried(auditId, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Check if an audit entry exists for a given hash
     * @param dataHash The IPFS hash to check
     */
    function auditEntryExists(string memory dataHash) external view returns (bool) {
        return hashToAuditId[dataHash] > 0;
    }
    
    /**
     * @dev Batch create multiple audit entries
     * @param dataHashes Array of IPFS hashes
     * @param signatures Array of cryptographic signatures
     * @param eventTypes Array of event types
     * @param descriptions Array of descriptions
     * @param metadatas Array of metadata
     */
    function batchCreateAuditEntries(
        string[] memory dataHashes,
        string[] memory signatures,
        string[] memory eventTypes,
        string[] memory descriptions,
        string[] memory metadatas
    ) external onlyRole(AUDITOR_ROLE) nonReentrant returns (uint256[] memory) {
        require(
            dataHashes.length == signatures.length &&
            signatures.length == eventTypes.length &&
            eventTypes.length == descriptions.length &&
            descriptions.length == metadatas.length,
            "Array lengths must match"
        );
        
        uint256[] memory auditIds = new uint256[](dataHashes.length);
        
        for (uint256 i = 0; i < dataHashes.length; i++) {
            require(bytes(dataHashes[i]).length > 0, "Data hash cannot be empty");
            require(hashToAuditId[dataHashes[i]] == 0, "Duplicate audit entry");
            
            _auditCounter.increment();
            uint256 auditId = _auditCounter.current();
            
            auditEntries[auditId] = AuditEntry({
                id: auditId,
                auditor: msg.sender,
                dataHash: dataHashes[i],
                signature: signatures[i],
                eventType: eventTypes[i],
                description: descriptions[i],
                timestamp: block.timestamp,
                metadata: metadatas[i],
                verified: false,
                verifier: address(0),
                verificationTimestamp: 0
            });
            
            hashToAuditId[dataHashes[i]] = auditId;
            auditIds[i] = auditId;
            
            emit AuditEntryCreated(auditId, msg.sender, dataHashes[i], eventTypes[i], block.timestamp);
        }
        
        return auditIds;
    }
}