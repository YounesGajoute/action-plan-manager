import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Assignment as TaskIcon,
  Edit as EditIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';

interface Activity {
  id: string;
  type: 'task_created' | 'task_completed' | 'task_updated' | 'user_joined';
  title: string;
  description: string;
  user: string;
  timestamp: string;
}

const RecentActivity: React.FC = () => {
  // Mock data - this would come from your API
  const activities: Activity[] = [
    {
      id: '1',
      type: 'task_completed',
      title: 'Tâche terminée',
      description: 'Réparation machine TDR701',
      user: 'Amine',
      timestamp: new Date().toISOString(),
    },
    {
      id: '2',
      type: 'task_created',
      title: 'Nouvelle tâche',
      description: 'Installation équipement client ABC',
      user: 'Hassan',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: '3',
      type: 'task_updated',
      title: 'Tâche mise à jour',
      description: 'Développement module X',
      user: 'Youssef',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
    },
  ];

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'task_completed':
        return <CheckCircleIcon color="success" />;
      case 'task_created':
        return <TaskIcon color="primary" />;
      case 'task_updated':
        return <EditIcon color="warning" />;
      case 'user_joined':
        return <PersonIcon color="info" />;
      default:
        return <TaskIcon />;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'task_completed':
        return 'success';
      case 'task_created':
        return 'primary';
      case 'task_updated':
        return 'warning';
      case 'user_joined':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Card>
      <CardHeader title="Activité Récente" />
      <CardContent sx={{ p: 0 }}>
        {activities.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="text.secondary">
              Aucune activité récente
            </Typography>
          </Box>
        ) : (
          <List>
            {activities.map((activity) => (
              <ListItem key={activity.id}>
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: 'transparent' }}>
                    {getActivityIcon(activity.type)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography variant="subtitle2">
                        {activity.title}
                      </Typography>
                      <Chip
                        label={activity.user}
                        size="small"
                        color={getActivityColor(activity.type)}
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.secondary">
                        {activity.description}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {format(new Date(activity.timestamp), 'PPp', { locale: fr })}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
};

export default RecentActivity;