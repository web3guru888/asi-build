/**
 * Apollo Client Configuration for ASI-Code
 * Connects to Hasura GraphQL with real-time subscriptions
 */

import { ApolloClient, InMemoryCache, split, HttpLink, ApolloLink } from '@apollo/client';
import { WebSocketLink } from '@apollo/client/link/ws';
import { getMainDefinition } from '@apollo/client/utilities';
import { onError } from '@apollo/client/link/error';

// Configuration
const HASURA_GRAPHQL_ENDPOINT = 'http://localhost:8085/v1/graphql';
const HASURA_WS_ENDPOINT = 'ws://localhost:8085/v1/graphql';
const HASURA_ADMIN_SECRET = 'asi_hasura_admin_secret_2024';

// Error handling link
const errorLink = onError(({ graphQLErrors, networkError }) => {
  if (graphQLErrors) {
    graphQLErrors.forEach(({ message, locations, path }) => {
      console.error(`GraphQL error: Message: ${message}, Location: ${locations}, Path: ${path}`);
    });
  }
  if (networkError) {
    console.error(`Network error: ${networkError}`);
  }
});

// HTTP connection for queries and mutations
const httpLink = new HttpLink({
  uri: HASURA_GRAPHQL_ENDPOINT,
  headers: {
    'x-hasura-admin-secret': HASURA_ADMIN_SECRET,
    'content-type': 'application/json'
  }
});

// WebSocket connection for subscriptions
const wsLink = new WebSocketLink({
  uri: HASURA_WS_ENDPOINT,
  options: {
    reconnect: true,
    lazy: true,
    connectionParams: {
      headers: {
        'x-hasura-admin-secret': HASURA_ADMIN_SECRET
      }
    },
    connectionCallback: (error: any) => {
      if (error) {
        console.error('WebSocket connection error:', error);
      } else {
        console.log('WebSocket connected to Hasura');
      }
    }
  }
});

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

// Combine error handling with split link
const link = ApolloLink.from([errorLink, splitLink]);

// Apollo Client instance
export const apolloClient = new ApolloClient({
  link,
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
});

// Export configured client
export default apolloClient;