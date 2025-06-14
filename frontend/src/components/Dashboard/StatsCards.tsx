import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Avatar,
  Box,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Assignment as TasksIcon,
  CheckCircle as CompletedIcon,
  Schedule as InProgressIcon,
  Warning as OverdueIcon,
} from '@mui/icons-material';

interface StatsCardsProps {
  stats: {
    total: number;
    completed: number;
    inProgress: number;
    overdue: number;
    completionRate: number;
    changes?: {
      totalTasks?: number;
      completedTasks?: number;
      inProgressTasks?: number;
      overdueTasks?: number;
    };
  } | null;
}

interface StatCardProps {
  title: string;
  value: number;
  change?: number;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'warning' | 'error';
}

const StatCard: React.FC<StatCardProps> = React.memo(({ 
  title, 
  value, 
  change, 
  icon, 
  color 
}) => {
  const theme = useTheme();

  return (
    <Card
      sx={{
        height: '100%',
        '&:hover': {
          boxShadow: theme.shadows[4],
          transform: 'translateY(-2px)',
        },
        transition: 'all 0.2s ease-in-out',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
          <Avatar
            sx={{
              backgroundColor: alpha(theme.palette[color].main, 0.1),
              color: theme.palette[color].main,
              width: 48,
              height: 48,
            }}
          >
            {icon}
          </Avatar>
        </Box>

        <Typography
          variant="h4"
          component="div"
          sx={{ fontWeight: 700, mb: 0.5 }}
        >
          {value.toLocaleString('fr-FR')}
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {title}
        </Typography>

        {change !== undefined && (
          <Typography
            variant="caption"
            sx={{
              color: change >= 0 ? theme.palette.success.main : theme.palette.error.main,
              fontWeight: 600,
            }}
          >
            {change >= 0 ? '+' : ''}{change}% vs semaine dernière
          </Typography>
        )}
      </CardContent>
    </Card>
  );
});

StatCard.displayName = 'StatCard';

const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  if (!stats) return null;

  const cards = [
    {
      title: 'Total des Tâches',
      value: stats.total,
      change: stats.changes?.totalTasks,
      icon: <TasksIcon />,
      color: 'primary' as const,
    },
    {
      title: 'Tâches Terminées',
      value: stats.completed,
      change: stats.changes?.completedTasks,
      icon: <CompletedIcon />,
      color: 'success' as const,
    },
    {
      title: 'En Cours',
      value: stats.inProgress,
      change: stats.changes?.inProgressTasks,
      icon: <InProgressIcon />,
      color: 'warning' as const,
    },
    {
      title: 'En Retard',
      value: stats.overdue,
      change: stats.changes?.overdueTasks,
      icon: <OverdueIcon />,
      color: 'error' as const,
    },
  ];

  return (
    <Grid container spacing={3}>
      {cards.map((card, index) => (
        <Grid item xs={12} sm={6} md={3} key={index}>
          <StatCard {...card} />
        </Grid>
      ))}
    </Grid>
  );
};

export default React.memo(StatsCards);