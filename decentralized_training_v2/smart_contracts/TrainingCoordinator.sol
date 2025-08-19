// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title TrainingCoordinator
 * @dev Smart contract for coordinating decentralized AGI training
 * Manages training rounds, checkpoints, and AGIX token rewards
 */
contract TrainingCoordinator is Ownable, ReentrancyGuard {
    using SafeMath for uint256;

    // AGIX token contract
    IERC20 public agixToken;
    
    // Training round structure
    struct TrainingRound {
        uint256 roundId;
        string globalModelHash;
        uint256 startTime;
        uint256 deadline;
        uint256 minParticipants;
        uint256 maxParticipants;
        uint256 rewardPool;
        bool isActive;
        bool isCompleted;
        address[] participants;
        mapping(address => bool) hasSubmitted;
        mapping(address => uint256) contributions;
    }
    
    // Model checkpoint structure
    struct ModelCheckpoint {
        string checkpointId;
        string modelHash;
        string ipfsHash;
        address creator;
        uint256 timestamp;
        uint256 roundNumber;
        uint256 sizeBytes;
        bool isVerified;
    }
    
    // Node information
    struct NodeInfo {
        address nodeAddress;
        uint256 stakeAmount;
        uint256 reputationScore;
        uint256 totalContributions;
        uint256 lastActiveRound;
        bool isActive;
        bool isSlashed;
    }
    
    // Events
    event TrainingRoundStarted(uint256 indexed roundId, uint256 rewardPool, uint256 deadline);
    event TrainingRoundCompleted(uint256 indexed roundId, uint256 totalRewards);
    event ModelUpdateSubmitted(uint256 indexed roundId, address indexed participant);
    event CheckpointRecorded(string indexed checkpointId, address indexed creator);
    event RewardDistributed(address indexed participant, uint256 amount);
    event NodeRegistered(address indexed nodeAddress, uint256 stakeAmount);
    event NodeSlashed(address indexed nodeAddress, uint256 slashAmount);
    event StakeWithdrawn(address indexed nodeAddress, uint256 amount);
    
    // State variables
    mapping(uint256 => TrainingRound) public trainingRounds;
    mapping(string => ModelCheckpoint) public checkpoints;
    mapping(address => NodeInfo) public nodes;
    mapping(address => uint256) public pendingRewards;
    
    uint256 public currentRoundId;
    uint256 public totalStaked;
    uint256 public minStakeAmount = 1000 * 10**18; // 1000 AGIX minimum
    uint256 public slashPercentage = 10; // 10% slashing for malicious behavior
    uint256 public reputationDecayRate = 5; // 5% decay per round
    
    // Configuration
    uint256 public constant REPUTATION_SCALE = 1000000;
    uint256 public constant MAX_PARTICIPANTS_PER_ROUND = 100;
    uint256 public constant ROUND_DURATION = 1 hours;
    
    constructor(address _agixToken) {
        agixToken = IERC20(_agixToken);
        currentRoundId = 0;
    }
    
    /**
     * @dev Register a new training node
     */
    function registerNode(uint256 stakeAmount) external nonReentrant {
        require(stakeAmount >= minStakeAmount, "Insufficient stake amount");
        require(!nodes[msg.sender].isActive, "Node already registered");
        
        // Transfer stake to contract
        require(agixToken.transferFrom(msg.sender, address(this), stakeAmount), "Stake transfer failed");
        
        nodes[msg.sender] = NodeInfo({
            nodeAddress: msg.sender,
            stakeAmount: stakeAmount,
            reputationScore: REPUTATION_SCALE / 2, // Start with neutral reputation
            totalContributions: 0,
            lastActiveRound: 0,
            isActive: true,
            isSlashed: false
        });
        
        totalStaked = totalStaked.add(stakeAmount);
        
        emit NodeRegistered(msg.sender, stakeAmount);
    }
    
    /**
     * @dev Increase stake for existing node
     */
    function increaseStake(uint256 additionalStake) external nonReentrant {
        require(nodes[msg.sender].isActive, "Node not registered");
        require(additionalStake > 0, "Invalid stake amount");
        
        require(agixToken.transferFrom(msg.sender, address(this), additionalStake), "Stake transfer failed");
        
        nodes[msg.sender].stakeAmount = nodes[msg.sender].stakeAmount.add(additionalStake);
        totalStaked = totalStaked.add(additionalStake);
    }
    
    /**
     * @dev Withdraw stake (only if not participating in active round)
     */
    function withdrawStake(uint256 amount) external nonReentrant {
        NodeInfo storage node = nodes[msg.sender];
        require(node.isActive, "Node not registered");
        require(amount <= node.stakeAmount, "Insufficient stake");
        require(node.lastActiveRound < currentRoundId, "Cannot withdraw during active round");
        
        node.stakeAmount = node.stakeAmount.sub(amount);
        totalStaked = totalStaked.sub(amount);
        
        if (node.stakeAmount < minStakeAmount) {
            node.isActive = false;
        }
        
        require(agixToken.transfer(msg.sender, amount), "Stake withdrawal failed");
        
        emit StakeWithdrawn(msg.sender, amount);
    }
    
    /**
     * @dev Start a new training round
     */
    function startTrainingRound(
        string memory globalModelHash,
        uint256 minParticipants,
        uint256 maxParticipants,
        uint256 rewardPool
    ) external onlyOwner {
        require(maxParticipants <= MAX_PARTICIPANTS_PER_ROUND, "Too many participants");
        require(minParticipants <= maxParticipants, "Invalid participant limits");
        
        // Complete previous round if active
        if (currentRoundId > 0 && trainingRounds[currentRoundId].isActive) {
            _completeTrainingRound(currentRoundId);
        }
        
        currentRoundId = currentRoundId.add(1);
        
        TrainingRound storage round = trainingRounds[currentRoundId];
        round.roundId = currentRoundId;
        round.globalModelHash = globalModelHash;
        round.startTime = block.timestamp;
        round.deadline = block.timestamp.add(ROUND_DURATION);
        round.minParticipants = minParticipants;
        round.maxParticipants = maxParticipants;
        round.rewardPool = rewardPool;
        round.isActive = true;
        round.isCompleted = false;
        
        emit TrainingRoundStarted(currentRoundId, rewardPool, round.deadline);
    }
    
    /**
     * @dev Submit model update for current training round
     */
    function submitModelUpdate(
        uint256 roundId,
        string memory modelDiffHash,
        uint256 dataSize,
        string memory computeProof
    ) external {
        require(roundId == currentRoundId, "Invalid round ID");
        
        TrainingRound storage round = trainingRounds[roundId];
        require(round.isActive, "Round not active");
        require(block.timestamp <= round.deadline, "Round deadline passed");
        require(!round.hasSubmitted[msg.sender], "Already submitted");
        require(round.participants.length < round.maxParticipants, "Round full");
        
        NodeInfo storage node = nodes[msg.sender];
        require(node.isActive && !node.isSlashed, "Node not eligible");
        
        // Add participant
        round.participants.push(msg.sender);
        round.hasSubmitted[msg.sender] = true;
        round.contributions[msg.sender] = dataSize;
        
        // Update node info
        node.lastActiveRound = roundId;
        node.totalContributions = node.totalContributions.add(dataSize);
        
        emit ModelUpdateSubmitted(roundId, msg.sender);
        
        // Auto-complete round if max participants reached
        if (round.participants.length >= round.maxParticipants) {
            _completeTrainingRound(roundId);
        }
    }
    
    /**
     * @dev Complete training round and distribute rewards
     */
    function completeTrainingRound(uint256 roundId) external onlyOwner {
        _completeTrainingRound(roundId);
    }
    
    /**
     * @dev Internal function to complete training round
     */
    function _completeTrainingRound(uint256 roundId) internal {
        TrainingRound storage round = trainingRounds[roundId];
        require(round.isActive, "Round not active");
        require(
            block.timestamp > round.deadline || round.participants.length >= round.maxParticipants,
            "Round not ready to complete"
        );
        
        round.isActive = false;
        round.isCompleted = true;
        
        // Distribute rewards if minimum participants met
        if (round.participants.length >= round.minParticipants) {
            _distributeRewards(roundId);
        }
        
        // Update reputation scores
        _updateReputationScores(roundId);
        
        emit TrainingRoundCompleted(roundId, round.rewardPool);
    }
    
    /**
     * @dev Distribute rewards to participants
     */
    function _distributeRewards(uint256 roundId) internal {
        TrainingRound storage round = trainingRounds[roundId];
        
        uint256 totalContribution = 0;
        uint256 totalReputation = 0;
        
        // Calculate totals
        for (uint256 i = 0; i < round.participants.length; i++) {
            address participant = round.participants[i];
            totalContribution = totalContribution.add(round.contributions[participant]);
            totalReputation = totalReputation.add(nodes[participant].reputationScore);
        }
        
        // Distribute rewards based on contribution and reputation
        for (uint256 i = 0; i < round.participants.length; i++) {
            address participant = round.participants[i];
            
            uint256 contributionWeight = round.contributions[participant].mul(REPUTATION_SCALE).div(totalContribution);
            uint256 reputationWeight = nodes[participant].reputationScore.mul(REPUTATION_SCALE).div(totalReputation);
            
            // Combined weight (50% contribution, 50% reputation)
            uint256 combinedWeight = contributionWeight.add(reputationWeight).div(2);
            
            uint256 reward = round.rewardPool.mul(combinedWeight).div(REPUTATION_SCALE);
            
            pendingRewards[participant] = pendingRewards[participant].add(reward);
            
            emit RewardDistributed(participant, reward);
        }
    }
    
    /**
     * @dev Update reputation scores after training round
     */
    function _updateReputationScores(uint256 roundId) internal {
        TrainingRound storage round = trainingRounds[roundId];
        
        // Boost reputation for participants
        for (uint256 i = 0; i < round.participants.length; i++) {
            address participant = round.participants[i];
            NodeInfo storage node = nodes[participant];
            
            // Increase reputation by 5%
            uint256 reputationBoost = node.reputationScore.mul(5).div(100);
            node.reputationScore = node.reputationScore.add(reputationBoost);
            
            // Cap at maximum
            if (node.reputationScore > REPUTATION_SCALE) {
                node.reputationScore = REPUTATION_SCALE;
            }
        }
        
        // Decay reputation for non-participants
        for (uint256 i = 0; i < round.participants.length; i++) {
            address nodeAddress = round.participants[i];
            if (nodes[nodeAddress].isActive && nodes[nodeAddress].lastActiveRound < roundId) {
                NodeInfo storage node = nodes[nodeAddress];
                uint256 decay = node.reputationScore.mul(reputationDecayRate).div(100);
                node.reputationScore = node.reputationScore.sub(decay);
            }
        }
    }
    
    /**
     * @dev Claim pending rewards
     */
    function claimRewards() external nonReentrant {
        uint256 reward = pendingRewards[msg.sender];
        require(reward > 0, "No pending rewards");
        
        pendingRewards[msg.sender] = 0;
        
        require(agixToken.transfer(msg.sender, reward), "Reward transfer failed");
    }
    
    /**
     * @dev Record model checkpoint
     */
    function recordCheckpoint(
        string memory checkpointId,
        string memory modelHash,
        string memory ipfsHash,
        uint256 roundNumber,
        uint256 sizeBytes
    ) external {
        require(nodes[msg.sender].isActive, "Node not registered");
        require(bytes(checkpoints[checkpointId].checkpointId).length == 0, "Checkpoint already exists");
        
        checkpoints[checkpointId] = ModelCheckpoint({
            checkpointId: checkpointId,
            modelHash: modelHash,
            ipfsHash: ipfsHash,
            creator: msg.sender,
            timestamp: block.timestamp,
            roundNumber: roundNumber,
            sizeBytes: sizeBytes,
            isVerified: false
        });
        
        emit CheckpointRecorded(checkpointId, msg.sender);
    }
    
    /**
     * @dev Get checkpoint information
     */
    function getCheckpoint(string memory checkpointId) external view returns (
        string memory,
        string memory,
        string memory,
        address,
        uint256,
        uint256,
        uint256
    ) {
        ModelCheckpoint memory checkpoint = checkpoints[checkpointId];
        return (
            checkpoint.checkpointId,
            checkpoint.modelHash,
            checkpoint.ipfsHash,
            checkpoint.creator,
            checkpoint.timestamp,
            checkpoint.roundNumber,
            checkpoint.sizeBytes
        );
    }
    
    /**
     * @dev Slash malicious node
     */
    function slashNode(address nodeAddress, string memory reason) external onlyOwner {
        NodeInfo storage node = nodes[nodeAddress];
        require(node.isActive, "Node not active");
        require(!node.isSlashed, "Node already slashed");
        
        uint256 slashAmount = node.stakeAmount.mul(slashPercentage).div(100);
        
        node.stakeAmount = node.stakeAmount.sub(slashAmount);
        node.isSlashed = true;
        node.reputationScore = 0;
        
        totalStaked = totalStaked.sub(slashAmount);
        
        // Slashed amount goes to treasury
        // In practice, this could be redistributed to honest nodes
        
        emit NodeSlashed(nodeAddress, slashAmount);
    }
    
    /**
     * @dev Get training round information
     */
    function getTrainingRound(uint256 roundId) external view returns (
        uint256,
        string memory,
        uint256,
        uint256,
        uint256,
        uint256,
        uint256,
        bool,
        bool,
        uint256
    ) {
        TrainingRound storage round = trainingRounds[roundId];
        return (
            round.roundId,
            round.globalModelHash,
            round.startTime,
            round.deadline,
            round.minParticipants,
            round.maxParticipants,
            round.rewardPool,
            round.isActive,
            round.isCompleted,
            round.participants.length
        );
    }
    
    /**
     * @dev Get node information
     */
    function getNodeInfo(address nodeAddress) external view returns (
        uint256,
        uint256,
        uint256,
        uint256,
        bool,
        bool
    ) {
        NodeInfo storage node = nodes[nodeAddress];
        return (
            node.stakeAmount,
            node.reputationScore,
            node.totalContributions,
            node.lastActiveRound,
            node.isActive,
            node.isSlashed
        );
    }
    
    /**
     * @dev Emergency functions
     */
    function emergencyPause() external onlyOwner {
        // Implement emergency pause functionality
    }
    
    function updateMinStakeAmount(uint256 newMinStake) external onlyOwner {
        minStakeAmount = newMinStake;
    }
    
    function updateSlashPercentage(uint256 newPercentage) external onlyOwner {
        require(newPercentage <= 50, "Slash percentage too high");
        slashPercentage = newPercentage;
    }
}