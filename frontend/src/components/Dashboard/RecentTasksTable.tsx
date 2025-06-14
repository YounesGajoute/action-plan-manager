import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Avatar,
  Box,
  Typography,
  Skeleton,
  Button,
} from '@mui/material';
import { Visibility as ViewIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';

interface Task {
  id: string;
  po_number?: string;
  action_description: string;
  customer: string;
  responsible: string;
  status: string;
  deadline?: string;
  created_at: string;
}

interface RecentTasksTableProps {
  tasks: Task[];
  loading?: boolean;
}

const RecentTasksTable: React.FC<RecentTasksTableProps> = ({ tasks, loading }) => {
  const navigate = useNavigate();

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'done':
      case 'terminé':
        return 'success';
      case 'en cours':
      case 'in-progress':
        return 'warning';
      case 'en attente':
      case 'pending':
        return 'info';
      default:
        return 'default';
    }
  };

  const handleViewTask = (taskId: string) => {
    navigate(`/tasks/${taskId}`);
  };

  const handleViewAllTasks = () => {
    navigate('/tasks');
  };

  if (loading) {
    return (
      <Card>
        <CardHeader title="Tâches Récentes" />
        <CardContent>
          {[...Array(5)].map((_, index) => (
            <Skeleton key={index} variant="rectangular" height={60} sx={{ mb: 1 }} />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader 
        title="Tâches Récentes" 
        action={
          <Button variant="outlined" size="small" onClick={handleViewAllTasks}>
            Voir Tout
          </Button>
        }
      />
      <CardContent sx={{ p: 0 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Tâche</TableCell>
                <TableCell>Client</TableCell>
                <TableCell>Responsable</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell>Échéance</TableCell>
                <TableCell align="right">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary" sx={{ py: 4 }}>
                      Aucune tâche récente
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                tasks.slice(0, 5).map((task) => (
                  <TableRow key={task.id} hover>
                    <TableCell>
                      <Box>
                        <Typography variant="subtitle2" fontWeight={600}>
                          {task.po_number || 'N/A'}
                        </Typography>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            maxWidth: 200,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {task.action_description}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {task.customer}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Avatar sx={{ width: 24, height: 24, fontSize: '12px' }}>
                          {task.responsible.charAt(0).toUpperCase()}
                        </Avatar>
                        <Typography variant="body2">
                          {task.responsible}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={task.status}
                        size="small"
                        color={getStatusColor(task.status)}
                      />
                    </TableCell>
                    <TableCell>
                      {task.deadline ? (
                        <Typography variant="body2">
                          {format(new Date(task.deadline), 'dd/MM/yyyy', { locale: fr })}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Non définie
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        startIcon={<ViewIcon />}
                        onClick={() => handleViewTask(task.id)}
                      >
                        Voir
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};

export default RecentTasksTable;