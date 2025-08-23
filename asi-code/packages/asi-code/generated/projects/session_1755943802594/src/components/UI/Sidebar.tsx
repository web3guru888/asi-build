import React from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, Box, Divider, Typography, IconButton } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import BarChartIcon from '@mui/icons-material/BarChart';
import LineStyleIcon from '@mui/icons-material/LineStyle';
import PieChartIcon from '@mui/icons-material/PieChart';
import WidgetsIcon from '@mui/icons-material/Widgets';
import SettingsIcon from '@mui/icons-material/Settings';

const drawerWidth = 240;

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  return (
    <Drawer
      variant="temporary"
      open={open}
      onClose={onClose}
      ModalProps={{
        keepMounted: true,
      }}
      sx={{
        display: { xs: 'block', sm: 'none' },
        '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
      }}
      PaperProps={{
        elevation: 4,
      }}
    >
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Logo/Header Section */}
        <Box
          sx={{
            p: 2,
            display: 'flex',
            justifyContent: 'center',
            backgroundColor: 'primary.main',
            color: 'white',
          }}
        >
          <Typography variant="h6" noWrap>
            Dashboard
          </Typography>
        </Box>

        <Divider />

        {/* Navigation Links */}
        <List>
          <ListItem button component="a" href="#dashboard">
            <ListItemIcon sx={{ color: 'primary.main' }}>
              <DashboardIcon />
            </ListItemIcon>
            <ListItemText primary="Dashboard" />
          </ListItem>
          <ListItem button component="a" href="#barchart">
            <ListItemIcon sx={{ color: 'primary.main' }}>
              <BarChartIcon />
            </ListItemIcon>
            <ListItemText primary="Bar Chart" />
          </ListItem>
          <ListItem button component="a" href="#linechart">
            <ListItemIcon sx={{ color: 'primary.main' }}>
              <LineStyleIcon />
            </ListItemIcon>
            <ListItemText primary="Line Chart" />
          </ListItem>
          <ListItem button component="a" href="#piechart">
            <ListItemIcon sx={{ color: 'primary.main' }}>
              <PieChartIcon />
            </ListItemIcon>
            <ListItemText primary="Pie Chart" />
          </ListItem>
          <ListItem button component="a" href="#widgets">
            <ListItemIcon sx={{ color: 'primary.main' }}>
              <WidgetsIcon />
            </ListItemIcon>
            <ListItemText primary="Widgets" />
          </ListItem>
          <ListItem button component="a" href="#settings">
            <ListItemIcon sx={{ color: 'primary.main' }}>
              <SettingsIcon />
            </ListItemIcon>
            <ListItemText primary="Settings" />
          </ListItem>
        </List>

        {/* Footer */}
        <Box sx={{ mt: 'auto', p: 2 }}>
          <Typography variant="caption" color="textSecondary" align="center">
            © {new Date().getFullYear()} Dashboard App. All rights reserved.
          </Typography>
        </Box>
      </Box>
    </Drawer>
  );
};

export default Sidebar;