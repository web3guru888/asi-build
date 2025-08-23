/**
 * Task Queue Implementation
 *
 * Priority queue implementation for managing tasks in the orchestration system.
 * Provides thread-safe operations and priority-based task ordering.
 */

import {
  TaskQueue as ITaskQueue,
  Task,
  TaskPriority,
  TaskStatus,
} from './types.js';
import { EventEmitter } from 'eventemitter3';
import { Logger } from '../logging/index.js';

/**
 * Priority levels for internal sorting
 */
const PRIORITY_LEVELS: Record<TaskPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

/**
 * Queue statistics
 */
export interface QueueStatistics {
  totalTasks: number;
  pendingTasks: number;
  assignedTasks: number;
  completedTasks: number;
  failedTasks: number;
  cancelledTasks: number;
  averageWaitTime: number;
  oldestTaskAge: number;
  priorityDistribution: Record<TaskPriority, number>;
}

/**
 * Queue configuration
 */
export interface QueueConfig {
  maxSize?: number;
  enableStatistics?: boolean;
  cleanupInterval?: number;
  maxCompletedHistory?: number;
  logger?: Logger;
}

/**
 * Task Queue Implementation
 *
 * Thread-safe priority queue that manages tasks by priority and creation time.
 * Tasks are sorted first by priority (critical > high > medium > low) and
 * then by creation time (older tasks first within the same priority).
 */
export class TaskQueue extends EventEmitter implements ITaskQueue {
  private readonly tasks: Map<string, Task> = new Map();
  private readonly pendingTasks: Task[] = [];
  private readonly completedTasks: Map<string, Task> = new Map();
  private readonly failedTasks: Map<string, Task> = new Map();
  private readonly cancelledTasks: Map<string, Task> = new Map();

  private readonly config: Required<QueueConfig>;
  private readonly logger: Logger;
  private readonly mutex: Promise<void> = Promise.resolve();
  private cleanupTimer: NodeJS.Timer | null = null;

  constructor(config: QueueConfig = {}) {
    super();

    this.config = {
      maxSize: config.maxSize || 10000,
      enableStatistics: config.enableStatistics ?? true,
      cleanupInterval: config.cleanupInterval || 300000, // 5 minutes
      maxCompletedHistory: config.maxCompletedHistory || 1000,
      logger:
        config.logger || new Logger({ component: 'TaskQueue', level: 'info' }),
    };

    this.logger = this.config.logger;
    this.startCleanupTimer();

    this.logger.info('TaskQueue initialized', {
      maxSize: this.config.maxSize,
      enableStatistics: this.config.enableStatistics,
      cleanupInterval: this.config.cleanupInterval,
    });
  }

  /**
   * Add a task to the queue
   */
  add(task: Task): void {
    this.withLock(async () => {
      // Check queue size limit
      if (this.tasks.size >= this.config.maxSize) {
        const error = new Error(
          `Queue is full. Maximum size: ${this.config.maxSize}`
        );
        this.logger.error('Failed to add task - queue full', {
          taskId: task.id,
          maxSize: this.config.maxSize,
        });
        throw error;
      }

      // Validate task
      this.validateTask(task);

      // Check for duplicate task ID
      if (this.tasks.has(task.id)) {
        const error = new Error(
          `Task with ID ${task.id} already exists in queue`
        );
        this.logger.error('Failed to add task - duplicate ID', {
          taskId: task.id,
        });
        throw error;
      }

      // Set task status to pending if not already set
      if (!task.status || task.status === 'pending') {
        task.status = 'pending';
      }

      // Add task to maps
      this.tasks.set(task.id, task);

      // Add to pending queue if task is pending
      if (task.status === 'pending') {
        this.insertTaskInOrder(task);
        this.logger.debug('Task added to pending queue', {
          taskId: task.id,
          priority: task.priority,
          queueSize: this.pendingTasks.length,
        });
      }

      this.emit('task:added', task);

      this.logger.info('Task added to queue', {
        taskId: task.id,
        type: task.type,
        priority: task.priority,
        totalTasks: this.tasks.size,
        pendingTasks: this.pendingTasks.length,
      });
    });
  }

  /**
   * Remove a task from the queue
   */
  remove(taskId: string): boolean {
    return this.withLockSync(() => {
      const task = this.tasks.get(taskId);
      if (!task) {
        this.logger.debug('Task not found for removal', { taskId });
        return false;
      }

      // Remove from main task map
      this.tasks.delete(taskId);

      // Remove from pending queue
      const pendingIndex = this.pendingTasks.findIndex(t => t.id === taskId);
      if (pendingIndex >= 0) {
        this.pendingTasks.splice(pendingIndex, 1);
      }

      // Remove from other collections
      this.completedTasks.delete(taskId);
      this.failedTasks.delete(taskId);
      this.cancelledTasks.delete(taskId);

      this.emit('task:removed', task);

      this.logger.info('Task removed from queue', {
        taskId,
        totalTasks: this.tasks.size,
        pendingTasks: this.pendingTasks.length,
      });

      return true;
    });
  }

  /**
   * Get a task by ID
   */
  get(taskId: string): Task | undefined {
    return this.tasks.get(taskId);
  }

  /**
   * Get the next highest priority task
   */
  getNext(): Task | undefined {
    return this.withLockSync(() => {
      if (this.pendingTasks.length === 0) {
        return undefined;
      }

      // The first task in the array is the highest priority
      const task = this.pendingTasks[0];

      this.logger.debug('Retrieved next task', {
        taskId: task.id,
        priority: task.priority,
        remainingPending: this.pendingTasks.length - 1,
      });

      return task;
    });
  }

  /**
   * Get all pending tasks
   */
  getPending(): Task[] {
    return [...this.pendingTasks];
  }

  /**
   * Get tasks by priority
   */
  getByPriority(priority: TaskPriority): Task[] {
    return this.pendingTasks.filter(task => task.priority === priority);
  }

  /**
   * Get queue size (total number of tasks)
   */
  size(): number {
    return this.tasks.size;
  }

  /**
   * Get pending queue size
   */
  pendingSize(): number {
    return this.pendingTasks.length;
  }

  /**
   * Clear all tasks from the queue
   */
  clear(): void {
    this.withLock(async () => {
      const taskCount = this.tasks.size;

      this.tasks.clear();
      this.pendingTasks.length = 0;
      this.completedTasks.clear();
      this.failedTasks.clear();
      this.cancelledTasks.clear();

      this.emit('queue:cleared');

      this.logger.info('Queue cleared', { clearedTasks: taskCount });
    });
  }

  /**
   * Update task status
   */
  updateTaskStatus(
    taskId: string,
    status: TaskStatus,
    result?: any,
    error?: Error
  ): boolean {
    return this.withLockSync(() => {
      const task = this.tasks.get(taskId);
      if (!task) {
        this.logger.warn('Attempted to update status of non-existent task', {
          taskId,
          status,
        });
        return false;
      }

      const oldStatus = task.status;
      task.status = status;

      // Update timestamps
      switch (status) {
        case 'assigned':
          // Remove from pending queue when assigned
          const pendingIndex = this.pendingTasks.findIndex(
            t => t.id === taskId
          );
          if (pendingIndex >= 0) {
            this.pendingTasks.splice(pendingIndex, 1);
          }
          break;

        case 'in_progress':
          if (!task.startedAt) {
            task.startedAt = Date.now();
          }
          break;

        case 'completed':
          task.completedAt = Date.now();
          if (result !== undefined) {
            task.output = result;
          }
          this.completedTasks.set(taskId, task);
          break;

        case 'failed':
          task.completedAt = Date.now();
          if (error) {
            task.error = error;
          }
          this.failedTasks.set(taskId, task);
          break;

        case 'cancelled':
          task.completedAt = Date.now();
          this.cancelledTasks.set(taskId, task);
          break;

        case 'pending':
          // Re-add to pending queue if status changed back to pending
          if (oldStatus !== 'pending') {
            this.insertTaskInOrder(task);
          }
          break;
      }

      this.emit('task:status_changed', { task, oldStatus, newStatus: status });

      this.logger.debug('Task status updated', {
        taskId,
        oldStatus,
        newStatus: status,
        pendingCount: this.pendingTasks.length,
      });

      return true;
    });
  }

  /**
   * Get tasks by status
   */
  getTasksByStatus(status: TaskStatus): Task[] {
    return Array.from(this.tasks.values()).filter(
      task => task.status === status
    );
  }

  /**
   * Get completed tasks
   */
  getCompletedTasks(): Task[] {
    return Array.from(this.completedTasks.values());
  }

  /**
   * Get failed tasks
   */
  getFailedTasks(): Task[] {
    return Array.from(this.failedTasks.values());
  }

  /**
   * Get cancelled tasks
   */
  getCancelledTasks(): Task[] {
    return Array.from(this.cancelledTasks.values());
  }

  /**
   * Get queue statistics
   */
  getStatistics(): QueueStatistics {
    if (!this.config.enableStatistics) {
      throw new Error('Statistics are disabled for this queue');
    }

    const allTasks = Array.from(this.tasks.values());
    const now = Date.now();

    // Calculate average wait time for completed tasks
    let totalWaitTime = 0;
    let waitTimeCount = 0;

    for (const task of this.completedTasks.values()) {
      if (task.startedAt) {
        totalWaitTime += task.startedAt - task.createdAt;
        waitTimeCount++;
      }
    }

    // Find oldest pending task
    let oldestTaskAge = 0;
    if (this.pendingTasks.length > 0) {
      const oldestTask = this.pendingTasks[this.pendingTasks.length - 1]; // Last in queue is oldest
      oldestTaskAge = now - oldestTask.createdAt;
    }

    // Priority distribution
    const priorityDistribution: Record<TaskPriority, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    };

    for (const task of this.pendingTasks) {
      priorityDistribution[task.priority]++;
    }

    return {
      totalTasks: this.tasks.size,
      pendingTasks: this.pendingTasks.length,
      assignedTasks: this.getTasksByStatus('assigned').length,
      completedTasks: this.completedTasks.size,
      failedTasks: this.failedTasks.size,
      cancelledTasks: this.cancelledTasks.size,
      averageWaitTime: waitTimeCount > 0 ? totalWaitTime / waitTimeCount : 0,
      oldestTaskAge,
      priorityDistribution,
    };
  }

  /**
   * Cleanup completed/failed/cancelled tasks that exceed history limit
   */
  cleanup(): void {
    this.withLock(async () => {
      const maxHistory = this.config.maxCompletedHistory;
      let cleanedCount = 0;

      // Cleanup completed tasks
      if (this.completedTasks.size > maxHistory) {
        const toRemove = this.completedTasks.size - maxHistory;
        const entries = Array.from(this.completedTasks.entries());

        // Sort by completion time and remove oldest
        entries.sort(
          (a, b) => (a[1].completedAt || 0) - (b[1].completedAt || 0)
        );

        for (let i = 0; i < toRemove; i++) {
          const [taskId] = entries[i];
          this.completedTasks.delete(taskId);
          this.tasks.delete(taskId);
          cleanedCount++;
        }
      }

      // Cleanup failed tasks
      if (this.failedTasks.size > maxHistory) {
        const toRemove = this.failedTasks.size - maxHistory;
        const entries = Array.from(this.failedTasks.entries());

        entries.sort(
          (a, b) => (a[1].completedAt || 0) - (b[1].completedAt || 0)
        );

        for (let i = 0; i < toRemove; i++) {
          const [taskId] = entries[i];
          this.failedTasks.delete(taskId);
          this.tasks.delete(taskId);
          cleanedCount++;
        }
      }

      // Cleanup cancelled tasks
      if (this.cancelledTasks.size > maxHistory) {
        const toRemove = this.cancelledTasks.size - maxHistory;
        const entries = Array.from(this.cancelledTasks.entries());

        entries.sort(
          (a, b) => (a[1].completedAt || 0) - (b[1].completedAt || 0)
        );

        for (let i = 0; i < toRemove; i++) {
          const [taskId] = entries[i];
          this.cancelledTasks.delete(taskId);
          this.tasks.delete(taskId);
          cleanedCount++;
        }
      }

      if (cleanedCount > 0) {
        this.emit('queue:cleaned', { removedTasks: cleanedCount });
        this.logger.info('Queue cleanup completed', {
          removedTasks: cleanedCount,
        });
      }
    });
  }

  /**
   * Destroy the queue and cleanup resources
   */
  destroy(): void {
    this.logger.info('Destroying TaskQueue');

    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }

    this.clear();
    this.removeAllListeners();

    this.logger.info('TaskQueue destroyed');
  }

  /**
   * Insert task in priority order
   */
  private insertTaskInOrder(task: Task): void {
    const taskPriorityLevel = PRIORITY_LEVELS[task.priority];

    // Find the correct position to insert the task
    let insertIndex = this.pendingTasks.length;

    for (let i = 0; i < this.pendingTasks.length; i++) {
      const existingTask = this.pendingTasks[i];
      const existingPriorityLevel = PRIORITY_LEVELS[existingTask.priority];

      // If new task has higher priority (lower number), insert here
      if (taskPriorityLevel < existingPriorityLevel) {
        insertIndex = i;
        break;
      }

      // If same priority, sort by creation time (older first)
      if (
        taskPriorityLevel === existingPriorityLevel &&
        task.createdAt < existingTask.createdAt
      ) {
        insertIndex = i;
        break;
      }
    }

    this.pendingTasks.splice(insertIndex, 0, task);
  }

  /**
   * Validate task before adding to queue
   */
  private validateTask(task: Task): void {
    if (!task.id) {
      throw new Error('Task ID is required');
    }

    if (!task.type) {
      throw new Error('Task type is required');
    }

    if (!task.priority) {
      throw new Error('Task priority is required');
    }

    if (!Object.keys(PRIORITY_LEVELS).includes(task.priority)) {
      throw new Error(`Invalid task priority: ${task.priority}`);
    }

    if (!task.createdAt) {
      task.createdAt = Date.now();
    }
  }

  /**
   * Start cleanup timer
   */
  private startCleanupTimer(): void {
    if (this.config.cleanupInterval > 0) {
      this.cleanupTimer = setInterval(() => {
        this.cleanup();
      }, this.config.cleanupInterval);
    }
  }

  /**
   * Thread-safe lock wrapper for async operations
   */
  private async withLock<T>(operation: () => Promise<T>): Promise<T> {
    await this.mutex;
    return operation();
  }

  /**
   * Thread-safe lock wrapper for synchronous operations
   */
  private withLockSync<T>(operation: () => T): T {
    // For synchronous operations, we'll use a simple flag-based locking
    // In a real implementation with true concurrency, you'd use proper synchronization
    return operation();
  }
}
