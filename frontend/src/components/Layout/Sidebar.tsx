import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Divider,
  Chip,
  Avatar,
  useTheme,
  alpha,
  Collapse,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Assignment as TasksIcon,
  Analytics as AnalyticsIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  Build as InstallationIcon,
  RepairServices as RepairIcon,
  Code as DevelopmentIcon,
  LocalShipping as DeliveryIcon,
  Business as CommercialIcon,
  ExpandLess,
  ExpandMore,
  Circle as CircleIcon,
  Inbox as InboxIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAppSelector, useAppDispatch } from '../../hooks/redux';
import { toggleSidebar } from '../../store/slices/uiSlice';
import { useTasks } from '../../hooks/useTasks';

const DRAWER_WIDTH = 280;

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;
  children?: NavigationItem[];
}

const Sidebar: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  
  // Redux state
  const { sidebarOpen, darkMode } = useAppSelector((state) => state.ui);
  const { user } = useAppSelector((state) => state.auth);
  
  // Get task counts for badges
  const { taskCounts } = useTasks();
  
  // Local state for expandable items
  const [expandedItems, setExpandedItems] = React.useState<Record<string, boolean>>({
    tasks: true, // Tasks section expanded by default
  });

  const handleToggleExpand = (itemId: string) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    // Close sidebar on mobile after navigation
    if (window.innerWidth < theme.breakpoints.values.md) {
      dispatch(toggleSidebar());
    }
  };

  const isPathActive = (path: string): boolean => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  // Navigation configuration
  const navigationItems: NavigationItem[] = [
    {
      id: 'dashboard',
      label: 'Tableau de Bord',
      icon: <DashboardIcon />,
      path: '/dashboard',
    },
    {
      id: 'tasks',
      label: 'Gestion des Tâches',
      icon: <TasksIcon />,
      path: '/tasks',
      badge: taskCounts?.total || 0,
      children: [
        {
          id: 'all-tasks',
          label: 'Toutes les Tâches',
          icon: <InboxIcon />,
          path: '/tasks/all',
          badge: taskCounts?.total || 0,
        },
        {
          id: 'pending-tasks',
          label: 'En Attente',
          icon: <ScheduleIcon />,
          path: '/tasks/pending',
          badge: taskCounts?.pending || 0,
        },
        {
          id: 'in-progress-tasks',
          label: 'En Cours',
          icon: <CircleIcon color="warning" />,
          path: '/tasks/in-progress',
          badge: taskCounts?.inProgress || 0,
        },
        {
          id: 'completed-tasks',
          label: 'Terminées',
          icon: <CheckCircleIcon color="success" />,
          path: '/tasks/completed',
          badge: taskCounts?.completed || 0,
        },
      ],
    },
    {
      id: 'categories',
      label: 'Catégories',
      icon: <InstallationIcon />,
      path: '/categories',
      children: [
        {
          id: 'installation',
          label: 'Installation',
          icon: <InstallationIcon />,
          path: '/tasks/category/installation',
          badge: taskCounts?.byCategory?.installation || 0,
        },
        {
          id: 'reparation',
          label: 'Réparation',
          icon: <RepairIcon />,
          path: '/tasks/category/reparation',
          badge: taskCounts?.byCategory?.reparation || 0,
        },
        {
          id: 'developpement',
          label: 'Développement',
          icon: <DevelopmentIcon />,
          path: '/tasks/category/developpement',
          badge: taskCounts?.byCategory?.developpement || 0,
        },
        {
          id: 'livraison',
          label: 'Livraison',
          icon: <DeliveryIcon />,
          path: '/tasks/category/livraison',
          badge: taskCounts?.byCategory?.livraison || 0,
        },
        {
          id: 'commercial',
          label: 'Commercial',
          icon: <CommercialIcon />,
          path: '/tasks/category/commercial',
          badge: taskCounts?.byCategory?.commercial || 0,
        },
      ],
    },
    {
      id: 'analytics',
      label: 'Analyses',
      icon: <AnalyticsIcon />,
      path: '/analytics',
    },
  ];

  // Admin-only navigation items
  const adminNavigationItems: NavigationItem[] = [
    {
      id: 'users',
      label: 'Gestion Utilisateurs',
      icon: <PeopleIcon />,
      path: '/users',
    },
    {
      id: 'settings',
      label: 'Paramètres',
      icon: <SettingsIcon />,
      path: '/settings',
    },
  ];

  const renderNavigationItem = (item: NavigationItem, depth: number = 0) => {
    const isActive = isPathActive(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems[item.id];

    return (
      <React.Fragment key={item.id}>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => {
              if (hasChildren) {
                handleToggleExpand(item.id);
              } else {
                handleNavigate(item.path);
              }
            }}
            sx={{
              pl: 2 + depth * 2,
              pr: 2,
              py: 1,
              minHeight: 48,
              borderRadius: 1,
              mx: 1,
              mb: 0.5,
              backgroundColor: isActive 
                ? alpha(theme.palette.primary.main, 0.12)
                : 'transparent',
              color: isActive 
                ? theme.palette.primary.main 
                : theme.palette.text.primary,
              '&:hover': {
                backgroundColor: isActive 
                  ? alpha(theme.palette.primary.main, 0.16)
                  : alpha(theme.palette.action.hover, 0.04),
              },
              '&:before': isActive ? {
                content: '""',
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: 3,
                backgroundColor: theme.palette.primary.main,
                borderRadius: '0 2px 2px 0',
              } : {},
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 40,
                color: isActive 
                  ? theme.palette.primary.main 
                  : theme.palette.text.secondary,
              }}
            >
              {item.icon}
            </ListItemIcon>
            
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{
                fontSize: '14px',
                fontWeight: isActive ? 600 : 400,
              }}
            />
            
            {item.badge !== undefined && item.badge > 0 && (
              <Chip
                label={item.badge}
                size="small"
                sx={{
                  height: 20,
                  fontSize: '11px',
                  backgroundColor: theme.palette.primary.main,
                  color: theme.palette.primary.contrastText,
                  ml: 1,
                }}
              />
            )}
            
            {hasChildren && (
              isExpanded ? <ExpandLess /> : <ExpandMore />
            )}
          </ListItemButton>
        </ListItem>

        {/* Render children */}
        {hasChildren && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {item.children!.map((child) => 
                renderNavigationItem(child, depth + 1)
              )}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header with Logo and Title */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          minHeight: 64,
        }}
      >
        <Avatar
          sx={{
            width: 40,
            height: 40,
            backgroundColor: theme.palette.primary.main,
            color: theme.palette.primary.contrastText,
            fontWeight: 'bold',
          }}
        >
          AP
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              fontSize: '18px',
              color: theme.palette.text.primary,
              lineHeight: 1.2,
            }}
          >
            Action Plan
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: theme.palette.text.secondary,
              fontSize: '12px',
            }}
          >
            Management System
          </Typography>
        </Box>
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, overflowY: 'auto', py: 1 }}>
        <List sx={{ py: 0 }}>
          {navigationItems.map((item) => renderNavigationItem(item))}
        </List>

        {/* Admin Section */}
        {user?.roles?.includes('admin') && (
          <>
            <Divider sx={{ mx: 2, my: 2 }} />
            <Typography
              variant="overline"
              sx={{
                px: 3,
                py: 1,
                color: theme.palette.text.secondary,
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.5px',
              }}
            >
              Administration
            </Typography>
            <List sx={{ py: 0 }}>
              {adminNavigationItems.map((item) => renderNavigationItem(item))}
            </List>
          </>
        )}
      </Box>

      {/* Footer with User Info */}
      <Box
        sx={{
          p: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
          backgroundColor: alpha(theme.palette.background.paper, 0.8),
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              width: 32,
              height: 32,
              backgroundColor: theme.palette.secondary.main,
              fontSize: '14px',
            }}
          >
            {user?.name?.charAt(0).toUpperCase() || 'U'}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant="subtitle2"
              sx={{
                fontWeight: 600,
                fontSize: '13px',
                color: theme.palette.text.primary,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {user?.name || 'Utilisateur'}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: theme.palette.text.secondary,
                fontSize: '11px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                display: 'block',
              }}
            >
              {user?.email || 'email@example.com'}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );

  return (
    <>
      {/* Desktop Drawer */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={sidebarOpen}
        sx={{
          display: { xs: 'none', md: 'block' },
          width: sidebarOpen ? DRAWER_WIDTH : 0,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            backgroundColor: theme.palette.background.paper,
            borderRight: `1px solid ${theme.palette.divider}`,
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        anchor="left"
        open={sidebarOpen}
        onClose={() => dispatch(toggleSidebar())}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            backgroundColor: theme.palette.background.paper,
          },
        }}
      >
        {drawerContent}
      </Drawer>
    </>
  );
};

export default Sidebar;