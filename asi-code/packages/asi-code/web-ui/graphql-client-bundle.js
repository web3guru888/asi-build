/**
 * GraphQL Client Bundle for ASI-Code
 * Provides Apollo Client with real-time subscriptions to Hasura
 */

// Import required libraries (assumes they're loaded via CDN in HTML)
const { ApolloClient, InMemoryCache, gql, split, createHttpLink } = window['@apollo/client'];
const { WebSocketLink } = window['@apollo/client/link/ws'];
const { getMainDefinition } = window['@apollo/client/utilities'];
const { SubscriptionClient } = window['subscriptions-transport-ws'];

// Configuration
const HASURA_ENDPOINT = 'http://localhost:8085/v1/graphql';
const HASURA_WS_ENDPOINT = 'ws://localhost:8085/v1/graphql';
const HASURA_ADMIN_SECRET = 'asi_hasura_admin_secret_2024';

// Create HTTP link for queries and mutations
const httpLink = createHttpLink({
    uri: HASURA_ENDPOINT,
    headers: {
        'x-hasura-admin-secret': HASURA_ADMIN_SECRET,
        'content-type': 'application/json'
    }
});

// Create WebSocket client for subscriptions
const wsClient = new SubscriptionClient(HASURA_WS_ENDPOINT, {
    reconnect: true,
    connectionParams: {
        headers: {
            'x-hasura-admin-secret': HASURA_ADMIN_SECRET
        }
    },
    connectionCallback: (error) => {
        if (error) {
            console.error('WebSocket connection error:', error);
            window.updateGraphQLStatus && window.updateGraphQLStatus(false);
        } else {
            console.log('WebSocket connected to Hasura');
            window.updateGraphQLStatus && window.updateGraphQLStatus(true);
        }
    }
});

// Create WebSocket link
const wsLink = new WebSocketLink(wsClient);

// Split link - use WebSocket for subscriptions, HTTP for everything else
const splitLink = split(
    ({ query }) => {
        const definition = getMainDefinition(query);
        return (
            definition.kind === 'OperationDefinition' &&
            definition.operation === 'subscription'
        );
    },
    wsLink,
    httpLink
);

// Create Apollo Client instance
export const apolloClient = new ApolloClient({
    link: splitLink,
    cache: new InMemoryCache({
        typePolicies: {
            sessions: {
                keyFields: ['session_id']
            },
            tasks: {
                keyFields: ['task_id']
            },
            orchestrations: {
                keyFields: ['orchestration_id']
            },
            agents: {
                keyFields: ['agent_id']
            },
            generated_files: {
                keyFields: ['id']
            }
        }
    }),
    defaultOptions: {
        watchQuery: {
            fetchPolicy: 'cache-and-network',
            errorPolicy: 'all'
        },
        query: {
            fetchPolicy: 'network-only',
            errorPolicy: 'all'
        }
    }
});

// GraphQL Queries and Subscriptions
export const QUERIES = {
    // Session Statistics
    SESSION_STATS: gql`
        query GetSessionStats {
            sessions_aggregate {
                aggregate {
                    count
                }
            }
            tasks_aggregate(where: {status: {_eq: "in_progress"}}) {
                aggregate {
                    count
                }
            }
            tasks_aggregate(where: {status: {_eq: "completed"}}) {
                aggregate {
                    count
                }
            }
            tasks_aggregate(where: {status: {_eq: "failed"}}) {
                aggregate {
                    count
                }
            }
            generated_files_aggregate {
                aggregate {
                    count
                    sum {
                        file_size_bytes
                    }
                }
            }
        }
    `,

    // Get Latest Sessions
    LATEST_SESSIONS: gql`
        query GetLatestSessions($limit: Int = 10) {
            sessions(order_by: {created_at: desc}, limit: $limit) {
                session_id
                created_at
                is_active
                last_active_at
                conversations_aggregate {
                    aggregate { count }
                }
                orchestrations_aggregate {
                    aggregate { count }
                }
                projects_aggregate {
                    aggregate { count }
                }
            }
        }
    `,

    // Get Files for Project
    PROJECT_FILES: gql`
        query GetProjectFiles($projectId: uuid!) {
            generated_files(where: {project_id: {_eq: $projectId}}) {
                id
                file_name
                file_path
                content
                language
                file_size_bytes
                created_at
            }
        }
    `
};

export const SUBSCRIPTIONS = {
    // Watch Tasks in Real-time
    WATCH_TASKS: gql`
        subscription WatchTasks($orchestrationId: String) {
            tasks(
                where: {
                    orchestration: {
                        orchestration_id: {_eq: $orchestrationId}
                    }
                }
                order_by: {started_at: desc}
            ) {
                task_id
                name
                status
                assigned_agent
                started_at
                completed_at
                result
                error_message
                estimated_hours
                actual_hours
                can_parallel
                dependencies
            }
        }
    `,

    // Watch All Active Tasks
    ACTIVE_TASKS: gql`
        subscription ActiveTasks {
            tasks(
                where: {status: {_in: ["pending", "in_progress"]}}
                order_by: {started_at: desc}
            ) {
                task_id
                name
                status
                assigned_agent
                started_at
                estimated_hours
            }
        }
    `,

    // Watch Agent Status
    WATCH_AGENTS: gql`
        subscription WatchAgents {
            agents(order_by: {last_active_at: desc}) {
                agent_id
                agent_name
                agent_type
                status
                capabilities
                last_active_at
                current_task_id
            }
        }
    `,

    // Watch WebSocket Messages
    WATCH_MESSAGES: gql`
        subscription WatchMessages($sessionId: String!) {
            websocket_messages(
                where: {
                    connection: {
                        session: {session_id: {_eq: $sessionId}}
                    }
                }
                order_by: {timestamp: desc}
                limit: 50
            ) {
                id
                direction
                message_type
                message_data
                timestamp
            }
        }
    `,

    // System Logs Stream
    SYSTEM_LOGS: gql`
        subscription SystemLogs($level: String) {
            system_logs(
                where: {log_level: {_eq: $level}}
                order_by: {created_at: desc}
                limit: 100
            ) {
                log_level
                source
                message
                context
                created_at
            }
        }
    `,

    // Performance Metrics Stream
    PERFORMANCE_METRICS: gql`
        subscription PerformanceMetrics {
            performance_metrics(
                order_by: {created_at: desc}
                limit: 50
            ) {
                metric_name
                metric_value
                metric_unit
                tags
                created_at
            }
        }
    `
};

export const MUTATIONS = {
    // Update Task Status
    UPDATE_TASK_STATUS: gql`
        mutation UpdateTaskStatus($taskId: String!, $status: String!, $result: String) {
            update_tasks(
                where: {task_id: {_eq: $taskId}}
                _set: {
                    status: $status
                    result: $result
                    completed_at: "now()"
                }
            ) {
                affected_rows
                returning {
                    task_id
                    status
                    result
                }
            }
        }
    `,

    // Create System Log
    CREATE_LOG: gql`
        mutation CreateLog($level: String!, $source: String!, $message: String!, $context: jsonb) {
            insert_system_logs_one(object: {
                log_level: $level
                source: $source
                message: $message
                context: $context
            }) {
                id
                created_at
            }
        }
    `,

    // Insert Performance Metric
    INSERT_METRIC: gql`
        mutation InsertMetric($name: String!, $value: numeric!, $unit: String!, $tags: jsonb) {
            insert_performance_metrics_one(object: {
                metric_name: $name
                metric_value: $value
                metric_unit: $unit
                tags: $tags
            }) {
                id
                created_at
            }
        }
    `
};

// Utility functions for data fetching
export const GraphQLClient = {
    // Execute a query
    async query(query, variables = {}) {
        try {
            const result = await apolloClient.query({
                query,
                variables,
                fetchPolicy: 'network-only'
            });
            return result.data;
        } catch (error) {
            console.error('GraphQL query error:', error);
            throw error;
        }
    },

    // Execute a mutation
    async mutate(mutation, variables = {}) {
        try {
            const result = await apolloClient.mutate({
                mutation,
                variables
            });
            return result.data;
        } catch (error) {
            console.error('GraphQL mutation error:', error);
            throw error;
        }
    },

    // Subscribe to a subscription
    subscribe(subscription, variables = {}, onNext, onError) {
        return apolloClient.subscribe({
            query: subscription,
            variables
        }).subscribe({
            next: onNext,
            error: onError || ((err) => console.error('Subscription error:', err))
        });
    },

    // Get session stats
    async getSessionStats() {
        return this.query(QUERIES.SESSION_STATS);
    },

    // Get latest sessions
    async getLatestSessions(limit = 10) {
        return this.query(QUERIES.LATEST_SESSIONS, { limit });
    },

    // Subscribe to active tasks
    subscribeToActiveTasks(onUpdate) {
        return this.subscribe(
            SUBSCRIPTIONS.ACTIVE_TASKS,
            {},
            (result) => onUpdate(result.data.tasks)
        );
    },

    // Subscribe to agent status
    subscribeToAgents(onUpdate) {
        return this.subscribe(
            SUBSCRIPTIONS.WATCH_AGENTS,
            {},
            (result) => onUpdate(result.data.agents)
        );
    },

    // Subscribe to system logs
    subscribeToLogs(level, onUpdate) {
        return this.subscribe(
            SUBSCRIPTIONS.SYSTEM_LOGS,
            { level },
            (result) => onUpdate(result.data.system_logs)
        );
    },

    // Update task status
    async updateTaskStatus(taskId, status, result = null) {
        return this.mutate(MUTATIONS.UPDATE_TASK_STATUS, {
            taskId,
            status,
            result
        });
    },

    // Log an event
    async logEvent(level, source, message, context = {}) {
        return this.mutate(MUTATIONS.CREATE_LOG, {
            level,
            source,
            message,
            context
        });
    }
};

// Export for global access
window.ASIGraphQLClient = GraphQLClient;
window.apolloClient = apolloClient;

// Auto-connect and monitor connection
wsClient.onConnected(() => {
    console.log('✅ GraphQL WebSocket connected');
    window.dispatchEvent(new CustomEvent('graphql-connected'));
});

wsClient.onReconnected(() => {
    console.log('🔄 GraphQL WebSocket reconnected');
    window.dispatchEvent(new CustomEvent('graphql-reconnected'));
});

wsClient.onDisconnected(() => {
    console.log('❌ GraphQL WebSocket disconnected');
    window.dispatchEvent(new CustomEvent('graphql-disconnected'));
});

console.log('GraphQL Client Bundle loaded successfully');