import React from 'react';
import { Typography, AppBar, Toolbar, IconButton, Container } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';

interface HeaderProps {
  title: string;
  onMenuClick?: () => void;
}

/**
 * Header component for the dashboard
 * Displays application title and navigation menu toggle
 */
const Header: React.FC<HeaderProps> = ({ title = 'Dashboard', onMenuClick }) => {
  return (
    <AppBar position="sticky" elevation={1} sx={{ backgroundColor: '#fff', color: '#1a1a1a' }}>
      <Container maxWidth={false} disableGutters>
        <Toolbar variant="dense" sx={{ paddingLeft: 2, paddingRight: 2 }}>
          <IconButton
            edge="start"
            color="inherit"
            aria-label="menu"
            onClick={onMenuClick}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 500 }}>
            {title}
          </Typography>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Header;