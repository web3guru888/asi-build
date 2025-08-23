/**
 * ASI-Code Orchestration Coordination Protocol
 *
 * Implementation of distributed coordination mechanisms including
 * leader election, consensus, synchronization, and failure detection.
 */

import { EventEmitter } from 'eventemitter3';
import { Agent, AgentMessage, CoordinationProtocol } from './types.js';
import { getOrchestrationMessageBus } from './message-bus.js';

// Leader election algorithms
export type LeaderElectionAlgorithm =
  | 'bully'
  | 'ring'
  | 'raft'
  | 'weight_based';

// Consensus mechanisms
export type ConsensusAlgorithm = 'raft' | 'pbft' | 'majority' | 'unanimous';

// Synchronization modes
export type SynchronizationMode =
  | 'barrier'
  | 'phase'
  | 'logical_clock'
  | 'vector_clock';

// Coordination state
export interface CoordinationState {
  leaderId?: string;
  term: number;
  epoch: number;
  participants: Set<string>;
  synchronizationBarriers: Map<string, SynchronizationBarrier>;
  consensusProposals: Map<string, ConsensusProposal>;
}

// Leader election state
export interface LeaderElectionState {
  algorithm: LeaderElectionAlgorithm;
  currentLeader?: string;
  term: number;
  electionInProgress: boolean;
  lastElectionTime: number;
  candidates: Map<string, CandidateInfo>;
}

export interface CandidateInfo {
  agentId: string;
  priority: number;
  weight: number;
  isAlive: boolean;
  lastHeartbeat: number;
}

// Consensus proposal
export interface ConsensusProposal {
  id: string;
  proposer: string;
  proposal: any;
  algorithm: ConsensusAlgorithm;
  votes: Map<string, Vote>;
  status: 'pending' | 'accepted' | 'rejected' | 'timeout';
  createdAt: number;
  timeout: number;
}

export interface Vote {
  voter: string;
  decision: 'accept' | 'reject';
  reason?: string;
  timestamp: number;
}

// Synchronization barrier
export interface SynchronizationBarrier {
  id: string;
  participants: Set<string>;
  arrived: Set<string>;
  mode: SynchronizationMode;
  createdAt: number;
  timeout: number;
  phase?: string;
}

// Failure detection
export interface FailureDetector {
  heartbeatInterval: number;
  timeoutThreshold: number;
  suspicionThreshold: number;
  lastHeartbeats: Map<string, number>;
  suspectedAgents: Set<string>;
  failedAgents: Set<string>;
}

// Configuration
export interface CoordinationProtocolConfig {
  leaderElection: {
    algorithm: LeaderElectionAlgorithm;
    heartbeatInterval: number;
    electionTimeout: number;
    retryInterval: number;
  };
  consensus: {
    defaultAlgorithm: ConsensusAlgorithm;
    proposalTimeout: number;
    minParticipants: number;
  };
  synchronization: {
    defaultMode: SynchronizationMode;
    barrierTimeout: number;
  };
  failureDetection: {
    heartbeatInterval: number;
    timeoutThreshold: number;
    suspicionThreshold: number;
  };
}

export class OrchestrationCoordinationProtocol
  extends EventEmitter
  implements CoordinationProtocol
{
  private readonly state: CoordinationState;
  private readonly leaderElectionState: LeaderElectionState;
  private readonly failureDetector: FailureDetector;
  private readonly config: CoordinationProtocolConfig;
  private readonly messageBus = getOrchestrationMessageBus();
  private readonly timers = new Map<string, NodeJS.Timeout>();

  constructor(config?: Partial<CoordinationProtocolConfig>) {
    super();

    this.config = {
      leaderElection: {
        algorithm: 'bully',
        heartbeatInterval: 5000,
        electionTimeout: 10000,
        retryInterval: 2000,
      },
      consensus: {
        defaultAlgorithm: 'majority',
        proposalTimeout: 30000,
        minParticipants: 1,
      },
      synchronization: {
        defaultMode: 'barrier',
        barrierTimeout: 60000,
      },
      failureDetection: {
        heartbeatInterval: 3000,
        timeoutThreshold: 10000,
        suspicionThreshold: 6000,
      },
      ...config,
    };

    this.state = {
      term: 0,
      epoch: 0,
      participants: new Set(),
      synchronizationBarriers: new Map(),
      consensusProposals: new Map(),
    };

    this.leaderElectionState = {
      algorithm: this.config.leaderElection.algorithm,
      term: 0,
      electionInProgress: false,
      lastElectionTime: 0,
      candidates: new Map(),
    };

    this.failureDetector = {
      heartbeatInterval: this.config.failureDetection.heartbeatInterval,
      timeoutThreshold: this.config.failureDetection.timeoutThreshold,
      suspicionThreshold: this.config.failureDetection.suspicionThreshold,
      lastHeartbeats: new Map(),
      suspectedAgents: new Set(),
      failedAgents: new Set(),
    };

    this.setupMessageHandlers();
    this.startFailureDetection();
  }

  /**
   * Elect a leader from available agents using configured algorithm
   */
  electLeader(agents: Agent[]): Agent {
    if (agents.length === 0) {
      throw new Error('Cannot elect leader from empty agent list');
    }

    if (agents.length === 1) {
      const leader = agents[0];
      this.setLeader(leader.id);
      return leader;
    }

    switch (this.config.leaderElection.algorithm) {
      case 'bully':
        return this.bullyElection(agents);
      case 'ring':
        return this.ringElection(agents);
      case 'raft':
        return this.raftElection(agents);
      case 'weight_based':
        return this.weightBasedElection(agents);
      default:
        throw new Error(
          `Unknown leader election algorithm: ${this.config.leaderElection.algorithm}`
        );
    }
  }

  /**
   * Synchronize agents using barriers or other mechanisms
   */
  async synchronize(agents: Agent[]): Promise<void> {
    const barrierId = `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const participantIds = agents.map(agent => agent.id);

    const barrier: SynchronizationBarrier = {
      id: barrierId,
      participants: new Set(participantIds),
      arrived: new Set(),
      mode: this.config.synchronization.defaultMode,
      createdAt: Date.now(),
      timeout: Date.now() + this.config.synchronization.barrierTimeout,
    };

    this.state.synchronizationBarriers.set(barrierId, barrier);

    // Notify all participants about the synchronization barrier
    await this.messageBus.multicast(
      {
        type: 'coordination',
        from: 'coordination-protocol',
        to: 'multicast',
        payload: {
          action: 'synchronization_barrier',
          barrierId,
          participants: participantIds,
          timeout: barrier.timeout,
        },
      },
      participantIds
    );

    // Wait for all participants to arrive at the barrier
    return new Promise((resolve, reject) => {
      const checkBarrier = () => {
        const currentBarrier =
          this.state.synchronizationBarriers.get(barrierId);
        if (!currentBarrier) {
          reject(new Error('Synchronization barrier was removed'));
          return;
        }

        if (currentBarrier.arrived.size === currentBarrier.participants.size) {
          this.state.synchronizationBarriers.delete(barrierId);
          this.emit('synchronization:completed', {
            barrierId,
            participants: participantIds,
          });
          resolve();
        } else if (Date.now() > currentBarrier.timeout) {
          this.state.synchronizationBarriers.delete(barrierId);
          this.emit('synchronization:timeout', {
            barrierId,
            participants: participantIds,
          });
          reject(new Error('Synchronization timeout'));
        }
      };

      const timerId = setInterval(checkBarrier, 100);
      this.timers.set(`barrier_${barrierId}`, timerId);

      // Initial check
      checkBarrier();
    });
  }

  /**
   * Broadcast a message to all agents
   */
  async broadcast(message: AgentMessage, agents: Agent[]): Promise<void> {
    const agentIds = agents.map(agent => agent.id);

    // Use message bus for reliable delivery
    await this.messageBus.multicast(
      {
        type: message.type,
        from: message.from,
        to: 'broadcast',
        payload: {
          originalMessage: message,
          broadcast: true,
          targets: agentIds,
        },
      },
      agentIds
    );

    this.emit('broadcast:sent', {
      messageId: message.id,
      targets: agentIds,
      messageType: message.type,
    });
  }

  /**
   * Achieve consensus on a proposal using configured algorithm
   */
  async consensus(proposal: any, agents: Agent[]): Promise<boolean> {
    if (agents.length < this.config.consensus.minParticipants) {
      throw new Error(
        `Insufficient participants for consensus (need ${this.config.consensus.minParticipants}, got ${agents.length})`
      );
    }

    const proposalId = `prop_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const participantIds = agents.map(agent => agent.id);

    const consensusProposal: ConsensusProposal = {
      id: proposalId,
      proposer: 'coordination-protocol',
      proposal,
      algorithm: this.config.consensus.defaultAlgorithm,
      votes: new Map(),
      status: 'pending',
      createdAt: Date.now(),
      timeout: Date.now() + this.config.consensus.proposalTimeout,
    };

    this.state.consensusProposals.set(proposalId, consensusProposal);

    // Send proposal to all participants
    await this.messageBus.multicast(
      {
        type: 'coordination',
        from: 'coordination-protocol',
        to: 'multicast',
        payload: {
          action: 'consensus_proposal',
          proposalId,
          proposal,
          algorithm: consensusProposal.algorithm,
          timeout: consensusProposal.timeout,
        },
      },
      participantIds
    );

    // Wait for consensus
    return new Promise((resolve, reject) => {
      const checkConsensus = () => {
        const currentProposal = this.state.consensusProposals.get(proposalId);
        if (!currentProposal) {
          reject(new Error('Consensus proposal was removed'));
          return;
        }

        if (Date.now() > currentProposal.timeout) {
          currentProposal.status = 'timeout';
          this.state.consensusProposals.delete(proposalId);
          this.emit('consensus:timeout', { proposalId });
          resolve(false);
          return;
        }

        const result = this.evaluateConsensus(currentProposal, participantIds);
        if (result !== null) {
          currentProposal.status = result ? 'accepted' : 'rejected';
          this.state.consensusProposals.delete(proposalId);

          if (result) {
            this.emit('consensus:accepted', { proposalId, proposal });
          } else {
            this.emit('consensus:rejected', { proposalId, proposal });
          }

          resolve(result);
        }
      };

      const timerId = setInterval(checkConsensus, 100);
      this.timers.set(`consensus_${proposalId}`, timerId);

      // Initial check
      checkConsensus();
    });
  }

  /**
   * Add agent to coordination
   */
  addAgent(agentId: string, weight = 1): void {
    this.state.participants.add(agentId);
    this.leaderElectionState.candidates.set(agentId, {
      agentId,
      priority: weight,
      weight,
      isAlive: true,
      lastHeartbeat: Date.now(),
    });

    this.failureDetector.lastHeartbeats.set(agentId, Date.now());
    this.emit('agent:added', { agentId, weight });
  }

  /**
   * Remove agent from coordination
   */
  removeAgent(agentId: string): void {
    this.state.participants.delete(agentId);
    this.leaderElectionState.candidates.delete(agentId);
    this.failureDetector.lastHeartbeats.delete(agentId);
    this.failureDetector.suspectedAgents.delete(agentId);
    this.failureDetector.failedAgents.delete(agentId);

    // Trigger new election if this was the leader
    if (this.state.leaderId === agentId) {
      this.state.leaderId = undefined;
      this.triggerLeaderElection();
    }

    this.emit('agent:removed', { agentId });
  }

  /**
   * Get current coordination state
   */
  getState(): CoordinationState {
    return { ...this.state };
  }

  /**
   * Get current leader
   */
  getCurrentLeader(): string | undefined {
    return this.state.leaderId;
  }

  /**
   * Shutdown the coordination protocol
   */
  shutdown(): void {
    // Clear all timers
    for (const timer of this.timers.values()) {
      clearInterval(timer);
    }
    this.timers.clear();

    // Clear state
    this.state.participants.clear();
    this.state.synchronizationBarriers.clear();
    this.state.consensusProposals.clear();
    this.leaderElectionState.candidates.clear();

    this.emit('coordination:shutdown');
  }

  // Private methods

  private setupMessageHandlers(): void {
    // Subscribe to coordination messages
    this.messageBus.subscribe(
      'coordination-protocol',
      ['coordination', 'health_check'],
      this.handleCoordinationMessage.bind(this)
    );
  }

  private async handleCoordinationMessage(
    message: AgentMessage
  ): Promise<void> {
    const { payload } = message;

    switch (payload.action) {
      case 'heartbeat':
        this.handleHeartbeat(message.from);
        break;

      case 'election_start':
        await this.handleElectionStart(payload);
        break;

      case 'election_victory':
        this.handleElectionVictory(message.from, payload);
        break;

      case 'synchronization_arrived':
        this.handleSynchronizationArrived(payload);
        break;

      case 'consensus_vote':
        this.handleConsensusVote(payload);
        break;

      default:
        this.emit('message:unknown', { message, action: payload.action });
    }
  }

  private handleHeartbeat(agentId: string): void {
    this.failureDetector.lastHeartbeats.set(agentId, Date.now());
    this.failureDetector.suspectedAgents.delete(agentId);
    this.failureDetector.failedAgents.delete(agentId);

    const candidate = this.leaderElectionState.candidates.get(agentId);
    if (candidate) {
      candidate.isAlive = true;
      candidate.lastHeartbeat = Date.now();
    }
  }

  private async handleElectionStart(payload: any): Promise<void> {
    // Handle election participation based on algorithm
    if (this.config.leaderElection.algorithm === 'bully') {
      // In bully algorithm, higher priority agents respond to election calls
      // Implementation would depend on specific bully algorithm details
    }
  }

  private handleElectionVictory(leaderId: string, payload: any): void {
    if (this.isValidLeader(leaderId, payload.term)) {
      this.setLeader(leaderId);
    }
  }

  private handleSynchronizationArrived(payload: any): void {
    const { barrierId, agentId } = payload;
    const barrier = this.state.synchronizationBarriers.get(barrierId);

    if (barrier?.participants.has(agentId)) {
      barrier.arrived.add(agentId);
      this.emit('synchronization:agent_arrived', { barrierId, agentId });
    }
  }

  private handleConsensusVote(payload: any): void {
    const { proposalId, vote, voter } = payload;
    const proposal = this.state.consensusProposals.get(proposalId);

    if (proposal) {
      proposal.votes.set(voter, {
        voter,
        decision: vote.decision,
        reason: vote.reason,
        timestamp: Date.now(),
      });

      this.emit('consensus:vote_received', {
        proposalId,
        voter,
        decision: vote.decision,
      });
    }
  }

  private bullyElection(agents: Agent[]): Agent {
    // Bully algorithm: highest ID/priority wins
    const sortedAgents = agents
      .filter(agent => !this.failureDetector.failedAgents.has(agent.id))
      .sort((a, b) => {
        const candidateA = this.leaderElectionState.candidates.get(a.id);
        const candidateB = this.leaderElectionState.candidates.get(b.id);
        const priorityA = candidateA?.priority || 0;
        const priorityB = candidateB?.priority || 0;
        return priorityB - priorityA; // Higher priority first
      });

    const leader = sortedAgents[0];
    this.setLeader(leader.id);
    return leader;
  }

  private ringElection(agents: Agent[]): Agent {
    // Ring algorithm: agents are arranged in a logical ring
    // For simplicity, we'll use a sorted approach
    const aliveAgents = agents
      .filter(agent => !this.failureDetector.failedAgents.has(agent.id))
      .sort((a, b) => a.id.localeCompare(b.id));

    if (aliveAgents.length === 0) {
      throw new Error('No alive agents for ring election');
    }

    // In a real ring election, we'd pass a token around
    // For this implementation, we'll select based on position
    const leader = aliveAgents[0];
    this.setLeader(leader.id);
    return leader;
  }

  private raftElection(agents: Agent[]): Agent {
    // Simplified Raft leader election
    // In real Raft, this would involve terms, log consistency, etc.
    const aliveAgents = agents.filter(
      agent => !this.failureDetector.failedAgents.has(agent.id)
    );

    if (aliveAgents.length === 0) {
      throw new Error('No alive agents for Raft election');
    }

    // Simple implementation: random selection among candidates
    const randomIndex = Math.floor(Math.random() * aliveAgents.length);
    const leader = aliveAgents[randomIndex];

    this.leaderElectionState.term++;
    this.setLeader(leader.id);
    return leader;
  }

  private weightBasedElection(agents: Agent[]): Agent {
    // Weight-based election: agent with highest weight wins
    let bestAgent = agents[0];
    let bestWeight = 0;

    for (const agent of agents) {
      if (this.failureDetector.failedAgents.has(agent.id)) continue;

      const candidate = this.leaderElectionState.candidates.get(agent.id);
      const weight = candidate?.weight || 1;

      if (weight > bestWeight) {
        bestWeight = weight;
        bestAgent = agent;
      }
    }

    this.setLeader(bestAgent.id);
    return bestAgent;
  }

  private evaluateConsensus(
    proposal: ConsensusProposal,
    participantIds: string[]
  ): boolean | null {
    const totalParticipants = participantIds.length;
    const currentVotes = proposal.votes.size;

    switch (proposal.algorithm) {
      case 'majority':
        if (currentVotes >= Math.floor(totalParticipants / 2) + 1) {
          const acceptVotes = Array.from(proposal.votes.values()).filter(
            vote => vote.decision === 'accept'
          ).length;
          return acceptVotes > totalParticipants / 2;
        }
        break;

      case 'unanimous':
        if (currentVotes === totalParticipants) {
          return Array.from(proposal.votes.values()).every(
            vote => vote.decision === 'accept'
          );
        }
        break;

      case 'raft':
        // Simplified Raft consensus
        if (currentVotes >= Math.floor(totalParticipants / 2) + 1) {
          const acceptVotes = Array.from(proposal.votes.values()).filter(
            vote => vote.decision === 'accept'
          ).length;
          return acceptVotes >= Math.floor(totalParticipants / 2) + 1;
        }
        break;

      case 'pbft':
        // Simplified PBFT (would need 2f+1 where f is max faulty nodes)
        const requiredVotes = Math.floor((totalParticipants - 1) / 3) * 2 + 1;
        if (currentVotes >= requiredVotes) {
          const acceptVotes = Array.from(proposal.votes.values()).filter(
            vote => vote.decision === 'accept'
          ).length;
          return acceptVotes >= requiredVotes;
        }
        break;
    }

    return null; // Not enough votes yet
  }

  private setLeader(leaderId: string): void {
    const previousLeader = this.state.leaderId;
    this.state.leaderId = leaderId;
    this.leaderElectionState.currentLeader = leaderId;
    this.leaderElectionState.electionInProgress = false;
    this.leaderElectionState.lastElectionTime = Date.now();
    this.state.term++;

    this.emit('leader:elected', {
      leaderId,
      previousLeader,
      term: this.state.term,
      algorithm: this.config.leaderElection.algorithm,
    });
  }

  private isValidLeader(leaderId: string, term: number): boolean {
    return (
      term >= this.leaderElectionState.term &&
      this.state.participants.has(leaderId) &&
      !this.failureDetector.failedAgents.has(leaderId)
    );
  }

  private triggerLeaderElection(): void {
    if (this.leaderElectionState.electionInProgress) return;

    this.leaderElectionState.electionInProgress = true;
    this.emit('leader:election_started', {
      algorithm: this.config.leaderElection.algorithm,
      term: this.leaderElectionState.term + 1,
    });

    // The actual election would be triggered by submitting agents
    // This is a placeholder for the election trigger mechanism
  }

  private startFailureDetection(): void {
    const detectionTimer = setInterval(() => {
      const now = Date.now();

      for (const [agentId, lastHeartbeat] of this.failureDetector
        .lastHeartbeats) {
        const timeSinceHeartbeat = now - lastHeartbeat;

        if (timeSinceHeartbeat > this.failureDetector.timeoutThreshold) {
          if (!this.failureDetector.failedAgents.has(agentId)) {
            this.failureDetector.failedAgents.add(agentId);
            this.emit('agent:failed', { agentId, timeSinceHeartbeat });

            // Trigger leader election if failed agent was the leader
            if (this.state.leaderId === agentId) {
              this.state.leaderId = undefined;
              this.triggerLeaderElection();
            }
          }
        } else if (
          timeSinceHeartbeat > this.failureDetector.suspicionThreshold
        ) {
          if (!this.failureDetector.suspectedAgents.has(agentId)) {
            this.failureDetector.suspectedAgents.add(agentId);
            this.emit('agent:suspected', { agentId, timeSinceHeartbeat });
          }
        }
      }
    }, this.failureDetector.heartbeatInterval);

    this.timers.set('failure_detection', detectionTimer);
  }
}

// Default instance
let coordinationProtocolInstance: OrchestrationCoordinationProtocol | null =
  null;

/**
 * Get the global coordination protocol instance
 */
export function getCoordinationProtocol(
  config?: Partial<CoordinationProtocolConfig>
): OrchestrationCoordinationProtocol {
  if (!coordinationProtocolInstance) {
    coordinationProtocolInstance = new OrchestrationCoordinationProtocol(
      config
    );
  }
  return coordinationProtocolInstance;
}

/**
 * Reset the global coordination protocol instance (for testing)
 */
export function resetCoordinationProtocol(): void {
  if (coordinationProtocolInstance) {
    coordinationProtocolInstance.shutdown();
    coordinationProtocolInstance = null;
  }
}
