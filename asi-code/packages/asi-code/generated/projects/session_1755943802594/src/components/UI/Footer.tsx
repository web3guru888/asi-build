import React from 'react';
import { Box, Container, Typography, Divider } from '@mui/material';

interface FooterProps {
  /**
   * Optional custom message to display in the footer
   * @default '© 2025 Dashboard App. All rights reserved.'
   */
  message?: string;
}

/**
 * Footer component for the dashboard layout
 * Displays copyright information and optional custom message
 * Compatible with Material-UI and responsive design
 */
const Footer: React.FC<FooterProps> = ({ message = '© 2025 Dashboard App. All rights reserved.' }) => {
  return (
    <Box
      component="footer"
      sx={{
        py: 3,
        px: 2,
        mt: 'auto',
        backgroundColor: (theme) =>
          theme.palette.mode === 'light' ? theme.palette.grey[200] : theme.palette.grey[800],
      }}
    >
      <Container maxWidth="lg">
        <Divider sx={{ mb: 2 }} />
        <Typography variant="body2" color="textSecondary" align="center">
          {message}
        </Typography>
      </Container>
    </Box>
  );
};

export default Footer;