import React, { useMemo } from 'react';
import {
  Box,
  Grid,
  Typography,
  Alert,
} from '@mui/material';
import { useGetTasksQuery, useGetDashboardAnalyticsQuery } from '../../store/api/tasksApi';
import { useAppSelector } from '../../hooks/redux';
import StatsCards from './StatsCards';
import ChartsSection from './ChartsSection';
import RecentTasksTable from './RecentTasksTable';
import QuickActions from './QuickActions';
import RecentActivity from './RecentActivity';

const Dashboard: React.FC = () => {
  const { user } = useAppSelector((state) => state.auth);
  
  // Fetch data using RTK Query
  const {
    data: tasksData,
    isLoading: tasksLoading,
    error: tasksError,
  } = useGetTasksQuery({ limit: 10 }); // Get recent 10 tasks
  
  const {
    data: analyticsData,
    isLoading: analyticsLoading,
    error: analyticsError,
  } = useGetDashboardAnalyticsQuery();

  // Memoized calculations for performance
  const dashboardStats = useMemo(() => {
    if (!tasksData?.counts) return null;
    
    const { counts } = tasksData;
    const completionRate = counts.total > 0 ? 
      Math.round((counts.completed / counts.total) * 100) : 0;
    
    return {
      total: counts.total,
      completed: counts.completed,
      inProgress: counts.inProgress,
      overdue: counts.overdue,
      completionRate,
      changes: analyticsData?.changes || {},
    };
  }, [tasksData?.counts, analyticsData?.changes]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bonjour';
    if (hour < 18) return 'Bon après-midi';
    return 'Bonsoir';
  };

  // Error handling
  if (tasksError || analyticsError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Erreur lors du chargement du tableau de bord. Veuillez actualiser la page.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          sx={{ fontWeight: 700, mb: 1 }}
        >
          {getGreeting()}, {user?.name?.split(' ')[0] || 'Utilisateur'} 👋
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Voici un aperçu de vos tâches et performances aujourd'hui.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12}>
          {tasksLoading ? (
            <Grid container spacing={2}>
              {[1, 2, 3, 4].map((i) => (
                <Grid item xs={12} sm={6} md={3} key={i}>
                  <Skeleton variant="rectangular" height={120} />
                </Grid>
              ))}
            </Grid>
          ) : (
            <StatsCards stats={dashboardStats} />
          )}
        </Grid>

        {/* Charts Section */}
        <Grid item xs={12}>
          {analyticsLoading ? (
            <Skeleton variant="rectangular" height={400} />
          ) : (
            <ChartsSection data={analyticsData} />
          )}
        </Grid>

        {/* Recent Tasks Table */}
        <Grid item xs={12} lg={8}>
          <RecentTasksTable
            tasks={tasksData?.tasks || []}
            loading={tasksLoading}
          />
        </Grid>

        {/* Quick Actions & Recent Activity */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <QuickActions />
            </Grid>
            <Grid item xs={12}>
              <RecentActivity />
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;