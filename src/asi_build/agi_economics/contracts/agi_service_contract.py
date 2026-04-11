"""
AGI Service Contract Templates
=============================

Smart contract templates for AGI services with payment, escrow,
and reputation integration.
"""

import json
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ContractState(Enum):
    """States of service contract"""

    CREATED = "created"
    FUNDED = "funded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


@dataclass
class ServiceContractTemplate:
    """Template for AGI service smart contracts"""

    # Contract metadata
    contract_address: str
    contract_version: str = "1.0.0"

    # Service details
    service_id: str = ""
    service_type: str = ""
    service_description: str = ""

    # Parties
    client_address: str = ""
    provider_address: str = ""

    # Financial terms
    payment_amount: Decimal = Decimal("0")
    token_address: str = ""  # AGIX token contract
    escrow_percentage: Decimal = Decimal("0.1")  # 10% escrow

    # Service terms
    delivery_deadline: int = 0
    quality_requirements: Dict[str, Any] = None

    # Contract state
    state: ContractState = ContractState.CREATED
    created_at: int = 0

    def __post_init__(self):
        if self.quality_requirements is None:
            self.quality_requirements = {}
        if self.created_at == 0:
            self.created_at = int(time.time())


class AGIServiceContract:
    """
    Smart contract template generator for AGI services with:
    - Automated payments
    - Escrow functionality
    - Reputation integration
    - Dispute resolution
    - Quality assurance
    """

    @staticmethod
    def generate_solidity_contract(template: ServiceContractTemplate) -> str:
        """Generate Solidity smart contract code"""

        contract_code = f"""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./interfaces/IERC20.sol";

/**
 * @title AGI Service Contract
 * @dev Smart contract for AGI service agreements with escrow and reputation
 * @notice Generated contract for service: {template.service_type}
 */
contract AGIServiceContract_{template.service_id} is ReentrancyGuard, Pausable, Ownable {{
    
    // Contract version
    string public constant VERSION = "{template.contract_version}";
    
    // Service details
    string public serviceId = "{template.service_id}";
    string public serviceType = "{template.service_type}";
    string public serviceDescription = "{template.service_description}";
    
    // Parties
    address public client;
    address public provider;
    address public arbiter;
    
    // Payment details
    IERC20 public paymentToken;
    uint256 public paymentAmount;
    uint256 public escrowAmount;
    uint256 public providerStake;
    
    // Service terms
    uint256 public deliveryDeadline;
    mapping(string => uint256) public qualityRequirements;
    
    // Contract state
    enum State {{ Created, Funded, InProgress, Completed, Disputed, Cancelled }}
    State public contractState;
    
    // Timestamps
    uint256 public createdAt;
    uint256 public fundedAt;
    uint256 public completedAt;
    
    // Reputation tracking
    address public reputationContract;
    
    // Events
    event ContractCreated(string serviceId, address client, address provider);
    event ContractFunded(uint256 amount, uint256 escrowAmount);
    event ServiceStarted(uint256 startTime);
    event ServiceCompleted(uint256 completionTime, uint256 qualityScore);
    event PaymentReleased(address to, uint256 amount);
    event DisputeRaised(address by, string reason);
    event DisputeResolved(address winner, uint256 providerAmount, uint256 clientRefund);
    event ContractCancelled(string reason);
    
    // Modifiers
    modifier onlyClient() {{
        require(msg.sender == client, "Only client can call this function");
        _;
    }}
    
    modifier onlyProvider() {{
        require(msg.sender == provider, "Only provider can call this function");
        _;
    }}
    
    modifier onlyParties() {{
        require(msg.sender == client || msg.sender == provider, "Only contract parties can call this");
        _;
    }}
    
    modifier onlyArbiter() {{
        require(msg.sender == arbiter, "Only arbiter can call this function");
        _;
    }}
    
    modifier inState(State _state) {{
        require(contractState == _state, "Invalid contract state");
        _;
    }}
    
    modifier beforeDeadline() {{
        require(block.timestamp <= deliveryDeadline, "Deadline has passed");
        _;
    }}
    
    /**
     * @dev Constructor
     * @param _client Client address
     * @param _provider Service provider address
     * @param _paymentToken AGIX token contract address
     * @param _paymentAmount Total payment amount
     * @param _deliveryDeadline Unix timestamp for delivery deadline
     * @param _arbiter Dispute resolution arbiter address
     * @param _reputationContract Address of reputation contract
     */
    constructor(
        address _client,
        address _provider,
        address _paymentToken,
        uint256 _paymentAmount,
        uint256 _deliveryDeadline,
        address _arbiter,
        address _reputationContract
    ) {{
        require(_client != address(0), "Invalid client address");
        require(_provider != address(0), "Invalid provider address");
        require(_paymentToken != address(0), "Invalid token address");
        require(_paymentAmount > 0, "Payment amount must be positive");
        require(_deliveryDeadline > block.timestamp, "Deadline must be in future");
        
        client = _client;
        provider = _provider;
        paymentToken = IERC20(_paymentToken);
        paymentAmount = _paymentAmount;
        deliveryDeadline = _deliveryDeadline;
        arbiter = _arbiter;
        reputationContract = _reputationContract;
        
        // Calculate escrow (10% of payment)
        escrowAmount = (_paymentAmount * {int(template.escrow_percentage * 100)}) / 100;
        
        contractState = State.Created;
        createdAt = block.timestamp;
        
        emit ContractCreated(serviceId, _client, _provider);
    }}
    
    /**
     * @dev Fund the contract with payment and escrow
     */
    function fundContract() external onlyClient inState(State.Created) nonReentrant {{
        uint256 totalAmount = paymentAmount + escrowAmount;
        
        require(
            paymentToken.transferFrom(client, address(this), totalAmount),
            "Payment transfer failed"
        );
        
        contractState = State.Funded;
        fundedAt = block.timestamp;
        
        emit ContractFunded(paymentAmount, escrowAmount);
    }}
    
    /**
     * @dev Provider stakes tokens to start service
     */
    function stakeAndStartService(uint256 _stakeAmount) external onlyProvider inState(State.Funded) beforeDeadline nonReentrant {{
        require(_stakeAmount >= escrowAmount, "Stake amount too low");
        
        require(
            paymentToken.transferFrom(provider, address(this), _stakeAmount),
            "Stake transfer failed"
        );
        
        providerStake = _stakeAmount;
        contractState = State.InProgress;
        
        emit ServiceStarted(block.timestamp);
    }}
    
    /**
     * @dev Complete service delivery
     * @param _qualityScore Quality score from 0-100
     * @param _deliveryHash Hash of delivered service/data
     */
    function completeService(uint256 _qualityScore, bytes32 _deliveryHash) 
        external 
        onlyProvider 
        inState(State.InProgress) 
        beforeDeadline 
        nonReentrant 
    {{
        require(_qualityScore <= 100, "Invalid quality score");
        require(_deliveryHash != bytes32(0), "Invalid delivery hash");
        
        contractState = State.Completed;
        completedAt = block.timestamp;
        
        // Calculate payments based on quality
        uint256 qualityBonus = 0;
        if (_qualityScore >= 90) {{
            qualityBonus = (paymentAmount * 10) / 100; // 10% bonus for excellent quality
        }}
        
        uint256 providerPayment = paymentAmount + qualityBonus;
        uint256 providerTotal = providerPayment + providerStake;
        
        // Release payment to provider
        require(paymentToken.transfer(provider, providerTotal), "Provider payment failed");
        
        // Return excess escrow to client
        uint256 remainingBalance = paymentToken.balanceOf(address(this));
        if (remainingBalance > 0) {{
            require(paymentToken.transfer(client, remainingBalance), "Client refund failed");
        }}
        
        // Update reputation (external call)
        _updateReputation(provider, true, _qualityScore);
        _updateReputation(client, true, 85); // Default good client score
        
        emit ServiceCompleted(block.timestamp, _qualityScore);
        emit PaymentReleased(provider, providerTotal);
    }}
    
    /**
     * @dev Raise a dispute
     * @param _reason Reason for dispute
     */
    function raiseDispute(string memory _reason) external onlyParties nonReentrant {{
        require(
            contractState == State.InProgress || contractState == State.Completed,
            "Cannot dispute in current state"
        );
        
        contractState = State.Disputed;
        
        emit DisputeRaised(msg.sender, _reason);
    }}
    
    /**
     * @dev Resolve dispute (only arbiter)
     * @param _providerWins True if provider wins dispute
     * @param _providerAmount Amount to send to provider
     * @param _clientRefund Amount to refund to client
     */
    function resolveDispute(
        bool _providerWins,
        uint256 _providerAmount,
        uint256 _clientRefund
    ) external onlyArbiter inState(State.Disputed) nonReentrant {{
        
        contractState = State.Completed;
        
        // Send payments
        if (_providerAmount > 0) {{
            require(paymentToken.transfer(provider, _providerAmount), "Provider payment failed");
        }}
        
        if (_clientRefund > 0) {{
            require(paymentToken.transfer(client, _clientRefund), "Client refund failed");
        }}
        
        // Update reputations based on dispute outcome
        _updateReputation(provider, _providerWins, _providerWins ? 75 : 25);
        _updateReputation(client, !_providerWins, !_providerWins ? 75 : 25);
        
        emit DisputeResolved(_providerWins ? provider : client, _providerAmount, _clientRefund);
    }}
    
    /**
     * @dev Cancel contract (before funding or by mutual agreement)
     */
    function cancelContract(string memory _reason) external onlyParties nonReentrant {{
        require(
            contractState == State.Created || 
            (contractState == State.Funded && msg.sender == client) ||
            (contractState == State.InProgress && block.timestamp > deliveryDeadline),
            "Cannot cancel in current state"
        );
        
        contractState = State.Cancelled;
        
        // Refund any funds
        uint256 balance = paymentToken.balanceOf(address(this));
        if (balance > 0) {{
            if (contractState == State.Funded) {{
                require(paymentToken.transfer(client, balance), "Refund failed");
            }} else if (contractState == State.InProgress) {{
                // Split refund between parties based on time elapsed
                uint256 timeElapsed = block.timestamp - fundedAt;
                uint256 totalTime = deliveryDeadline - fundedAt;
                uint256 providerRefund = (balance * timeElapsed) / totalTime;
                uint256 clientRefund = balance - providerRefund;
                
                if (providerRefund > 0) {{
                    require(paymentToken.transfer(provider, providerRefund), "Provider refund failed");
                }}
                if (clientRefund > 0) {{
                    require(paymentToken.transfer(client, clientRefund), "Client refund failed");
                }}
            }}
        }}
        
        emit ContractCancelled(_reason);
    }}
    
    /**
     * @dev Update reputation scores (internal)
     */
    function _updateReputation(address _agent, bool _positive, uint256 _score) internal {{
        if (reputationContract != address(0)) {{
            // Call reputation contract to update scores
            // This would interface with the reputation system
            (bool success,) = reputationContract.call(
                abi.encodeWithSignature(
                    "updateReputation(address,bool,uint256,string)",
                    _agent,
                    _positive,
                    _score,
                    serviceType
                )
            );
            // Don't revert if reputation update fails
        }}
    }}
    
    /**
     * @dev Emergency pause (only owner)
     */
    function pause() external onlyOwner {{
        _pause();
    }}
    
    /**
     * @dev Unpause (only owner)
     */
    function unpause() external onlyOwner {{
        _unpause();
    }}
    
    /**
     * @dev Get contract info
     */
    function getContractInfo() external view returns (
        string memory,
        address,
        address,
        uint256,
        uint256,
        State,
        uint256
    ) {{
        return (
            serviceId,
            client,
            provider,
            paymentAmount,
            deliveryDeadline,
            contractState,
            createdAt
        );
    }}
    
    /**
     * @dev Check if deadline has passed
     */
    function isDeadlinePassed() external view returns (bool) {{
        return block.timestamp > deliveryDeadline;
    }}
    
    /**
     * @dev Get contract balance
     */
    function getContractBalance() external view returns (uint256) {{
        return paymentToken.balanceOf(address(this));
    }}
}}
"""

        return contract_code.strip()

    @staticmethod
    def generate_deployment_script(template: ServiceContractTemplate) -> str:
        """Generate deployment script for the contract"""

        script = f"""
# AGI Service Contract Deployment Script
# Service: {template.service_type}
# Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

const {{ ethers }} = require("hardhat");

async function main() {{
    console.log("Deploying AGI Service Contract for service: {template.service_id}");
    
    // Contract parameters
    const clientAddress = "{template.client_address}";
    const providerAddress = "{template.provider_address}";
    const paymentTokenAddress = "{template.token_address}"; // AGIX token
    const paymentAmount = ethers.utils.parseEther("{template.payment_amount}");
    const deliveryDeadline = {template.delivery_deadline};
    const arbiterAddress = "0x742d35Cc6671C0532925a3b8D26414759d7C2d85"; // Default arbiter
    const reputationContractAddress = "0x1234567890123456789012345678901234567890"; // Reputation contract
    
    // Get contract factory
    const AGIServiceContract = await ethers.getContractFactory("AGIServiceContract_{template.service_id}");
    
    // Deploy contract
    const contract = await AGIServiceContract.deploy(
        clientAddress,
        providerAddress,
        paymentTokenAddress,
        paymentAmount,
        deliveryDeadline,
        arbiterAddress,
        reputationContractAddress
    );
    
    await contract.deployed();
    
    console.log("Contract deployed to:", contract.address);
    console.log("Transaction hash:", contract.deployTransaction.hash);
    
    // Verify contract (optional)
    if (process.env.ETHERSCAN_API_KEY) {{
        console.log("Verifying contract on Etherscan...");
        await hre.run("verify:verify", {{
            address: contract.address,
            constructorArguments: [
                clientAddress,
                providerAddress,
                paymentTokenAddress,
                paymentAmount,
                deliveryDeadline,
                arbiterAddress,
                reputationContractAddress
            ],
        }});
    }}
    
    return contract.address;
}}

main()
    .then(() => process.exit(0))
    .catch((error) => {{
        console.error(error);
        process.exit(1);
    }});
"""

        return script.strip()

    @staticmethod
    def generate_interface_abi() -> str:
        """Generate ABI interface for frontend integration"""

        abi = """
[
  {
    "inputs": [
      {"internalType": "address", "name": "_client", "type": "address"},
      {"internalType": "address", "name": "_provider", "type": "address"},
      {"internalType": "address", "name": "_paymentToken", "type": "address"},
      {"internalType": "uint256", "name": "_paymentAmount", "type": "uint256"},
      {"internalType": "uint256", "name": "_deliveryDeadline", "type": "uint256"},
      {"internalType": "address", "name": "_arbiter", "type": "address"},
      {"internalType": "address", "name": "_reputationContract", "type": "address"}
    ],
    "stateMutability": "nonpayable",
    "type": "constructor"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": false, "internalType": "string", "name": "reason", "type": "string"}
    ],
    "name": "ContractCancelled",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": false, "internalType": "string", "name": "serviceId", "type": "string"},
      {"indexed": false, "internalType": "address", "name": "client", "type": "address"},
      {"indexed": false, "internalType": "address", "name": "provider", "type": "address"}
    ],
    "name": "ContractCreated",
    "type": "event"
  },
  {
    "inputs": [],
    "name": "fundContract",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {"internalType": "uint256", "name": "_stakeAmount", "type": "uint256"}
    ],
    "name": "stakeAndStartService",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {"internalType": "uint256", "name": "_qualityScore", "type": "uint256"},
      {"internalType": "bytes32", "name": "_deliveryHash", "type": "bytes32"}
    ],
    "name": "completeService",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {"internalType": "string", "name": "_reason", "type": "string"}
    ],
    "name": "raiseDispute",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getContractInfo",
    "outputs": [
      {"internalType": "string", "name": "", "type": "string"},
      {"internalType": "address", "name": "", "type": "address"},
      {"internalType": "address", "name": "", "type": "address"},
      {"internalType": "uint256", "name": "", "type": "uint256"},
      {"internalType": "uint256", "name": "", "type": "uint256"},
      {"internalType": "enum AGIServiceContract.State", "name": "", "type": "uint8"},
      {"internalType": "uint256", "name": "", "type": "uint256"}
    ],
    "stateMutability": "view",
    "type": "function"
  }
]
        """

        return abi.strip()

    @staticmethod
    def create_service_contract(
        service_id: str,
        service_type: str,
        client_address: str,
        provider_address: str,
        payment_amount: Decimal,
        token_address: str = "0x5B7533812759B45C2B44C19e320ba2cD2681b542",  # AGIX mainnet
        delivery_deadline: Optional[int] = None,
        quality_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Create a complete service contract package"""

        if delivery_deadline is None:
            delivery_deadline = int(time.time()) + 86400 * 7  # 1 week from now

        template = ServiceContractTemplate(
            contract_address="",  # Will be filled after deployment
            service_id=service_id,
            service_type=service_type,
            service_description=f"AGI service contract for {service_type}",
            client_address=client_address,
            provider_address=provider_address,
            payment_amount=payment_amount,
            token_address=token_address,
            delivery_deadline=delivery_deadline,
            quality_requirements=quality_requirements or {},
        )

        return {
            "solidity_code": AGIServiceContract.generate_solidity_contract(template),
            "deployment_script": AGIServiceContract.generate_deployment_script(template),
            "abi": AGIServiceContract.generate_interface_abi(),
            "template_config": json.dumps(
                {
                    "service_id": template.service_id,
                    "service_type": template.service_type,
                    "client_address": template.client_address,
                    "provider_address": template.provider_address,
                    "payment_amount": str(template.payment_amount),
                    "delivery_deadline": template.delivery_deadline,
                    "quality_requirements": template.quality_requirements,
                },
                indent=2,
            ),
        }

    @staticmethod
    def generate_deployment_script(template: ServiceContractTemplate) -> str:
        """Generate deployment script for the contract"""

        script = f"""
# AGI Service Contract Deployment Script
# Service: {template.service_type}
# Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

const {{ ethers }} = require("hardhat");

async function main() {{
    console.log("Deploying AGI Service Contract for service: {template.service_id}");
    
    // Contract parameters
    const clientAddress = "{template.client_address}";
    const providerAddress = "{template.provider_address}";
    const paymentTokenAddress = "{template.token_address}"; // AGIX token
    const paymentAmount = ethers.utils.parseEther("{template.payment_amount}");
    const deliveryDeadline = {template.delivery_deadline};
    const arbiterAddress = "0x742d35Cc6671C0532925a3b8D26414759d7C2d85"; // Default arbiter
    const reputationContractAddress = "0x1234567890123456789012345678901234567890"; // Reputation contract
    
    // Get contract factory
    const AGIServiceContract = await ethers.getContractFactory("AGIServiceContract_{template.service_id}");
    
    // Deploy contract
    const contract = await AGIServiceContract.deploy(
        clientAddress,
        providerAddress,
        paymentTokenAddress,
        paymentAmount,
        deliveryDeadline,
        arbiterAddress,
        reputationContractAddress
    );
    
    await contract.deployed();
    
    console.log("Contract deployed to:", contract.address);
    console.log("Transaction hash:", contract.deployTransaction.hash);
    
    return contract.address;
}}

main()
    .then(() => process.exit(0))
    .catch((error) => {{
        console.error(error);
        process.exit(1);
    }});
"""

        return script.strip()
