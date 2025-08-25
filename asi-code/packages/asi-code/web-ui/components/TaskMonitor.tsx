/**
 * Real-time Task Monitor Component
 * Displays live task execution using GraphQL subscriptions
 */

import React from 'react';
import { useSubscription, gql } from '@apollo/client';

// GraphQL subscription for real-time task monitoring
const TASK_SUBSCRIPTION = gql`
  subscription WatchTasks($orchestrationId: String!) {
    tasks(
      where: { 
        orchestration: { orchestration_id: { _eq: $orchestrationId } }
      }
      order_by: { id: asc }
    ) {
      task_id
      name
      assigned_agent
      status
      can_parallel
      dependencies
      estimated_hours
      started_at
      completed_at
      result
      error_message
    }
  }
`;

interface Task {
  task_id: string;
  name: string;
  assigned_agent: string;
  status: string;
  can_parallel: boolean;
  dependencies: any;
  estimated_hours: number;
  started_at: string | null;
  completed_at: string | null;
  result: string | null;
  error_message: string | null;
}

interface TaskMonitorProps {
  orchestrationId: string;
}

export const TaskMonitor: React.FC<TaskMonitorProps> = ({ orchestrationId }) => {
  const { data, loading, error } = useSubscription<{ tasks: Task[] }>(
    TASK_SUBSCRIPTION,
    { 
      variables: { orchestrationId },
      shouldResubscribe: true
    }
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
        <span className="ml-3 text-gray-600">Connecting to real-time data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold">Connection Error</h3>
        <p className="text-red-600">{error.message}</p>
      </div>
    );
  }

  const tasks = data?.tasks || [];
  
  // Group tasks by status
  const tasksByStatus = {
    pending: tasks.filter(t => t.status === 'pending'),
    in_progress: tasks.filter(t => t.status === 'in_progress'),
    completed: tasks.filter(t => t.status === 'completed'),
    failed: tasks.filter(t => t.status === 'failed')
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-gray-100 text-gray-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800 animate-pulse';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getAgentIcon = (agent: string) => {
    if (agent.includes('architect')) return '🏗️';
    if (agent.includes('frontend')) return '🎨';
    if (agent.includes('backend')) return '⚙️';
    if (agent.includes('database')) return '💾';
    if (agent.includes('security')) return '🔒';
    if (agent.includes('worker')) return '👷';
    return '🤖';
  };

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-gray-900">{tasks.length}</div>
          <div className="text-sm text-gray-500">Total Tasks</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-blue-600">{tasksByStatus.in_progress.length}</div>
          <div className="text-sm text-gray-500">In Progress</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">{tasksByStatus.completed.length}</div>
          <div className="text-sm text-gray-500">Completed</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-red-600">{tasksByStatus.failed.length}</div>
          <div className="text-sm text-gray-500">Failed</div>
        </div>
      </div>

      {/* Task List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Task Execution Timeline</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {tasks.map((task) => (
            <div key={task.task_id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <span className="text-2xl">{getAgentIcon(task.assigned_agent)}</span>
                  <div>
                    <h4 className="text-sm font-medium text-gray-900">{task.name}</h4>
                    <p className="text-sm text-gray-500">
                      Agent: <span className="font-mono">{task.assigned_agent}</span>
                      {task.can_parallel && (
                        <span className="ml-2 text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                          Parallel
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                    {task.status.replace('_', ' ').toUpperCase()}
                  </span>
                  {task.estimated_hours && (
                    <span className="text-sm text-gray-500">
                      {task.estimated_hours}h estimated
                    </span>
                  )}
                </div>
              </div>
              
              {/* Progress Bar for In-Progress Tasks */}
              {task.status === 'in_progress' && (
                <div className="mt-3">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                  </div>
                </div>
              )}
              
              {/* Result or Error */}
              {task.result && (
                <div className="mt-2 text-sm text-green-600 bg-green-50 p-2 rounded">
                  ✅ {task.result}
                </div>
              )}
              {task.error_message && (
                <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                  ❌ {task.error_message}
                </div>
              )}
              
              {/* Timing Info */}
              {(task.started_at || task.completed_at) && (
                <div className="mt-2 text-xs text-gray-500">
                  {task.started_at && `Started: ${new Date(task.started_at).toLocaleTimeString()}`}
                  {task.completed_at && ` • Completed: ${new Date(task.completed_at).toLocaleTimeString()}`}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TaskMonitor;