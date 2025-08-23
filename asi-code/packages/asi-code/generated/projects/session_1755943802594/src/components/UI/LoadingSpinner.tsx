import React from 'react';
import { Box, CircularProgress, Typography, styled } from '@mui/material';

const StyledLoadingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '200px',
  padding: theme.spacing(2),
  width: '100%',
}));

const StyledCircularProgress = styled(CircularProgress)(({ theme }) => ({
  marginBottom: theme.spacing(2),
}));

interface LoadingSpinnerProps {
  /**
   * Optional message to display below the spinner
   * @default 'Loading...'
   */
  message?: string;
  /**
   * Size of the loading spinner
   * @default 40
   */
  size?: number;
  /**
   * Whether the spinner is currently loading
   * @default true
   */
  loading?: boolean;
  /**
   * Custom data-testid for testing
   */
  'data-testid'?: string;
}

/**
 * LoadingSpinner component displays a circular progress indicator with an optional message
 * Used to indicate loading states throughout the dashboard
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading...',
  size = 40,
  loading = true,
  'data-testid': dataTestId = 'loading-spinner',
}) => {
  if (!loading) {
    return null;
  }

  return (
    <StyledLoadingContainer data-testid={dataTestId}>
      <StyledCircularProgress size={size} />
      <Typography variant="body2" color="text.secondary">
        {message}
      </Typography>
    </StyledLoadingContainer>
  );
};

export default LoadingSpinner;