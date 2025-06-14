import React, { useState } from 'react';
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
  TablePagination,
  Chip,
  IconButton,
  Avatar,
  Box,
  Typography,
  Skeleton,
  Tooltip,
} from '@mui/material';
import {
  Edit as EditIcon,
  Visibility as ViewIcon,
  Delete as DeleteIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';

interface Task {
  id: string;
  po_number: string;
  action_description: string;
  customer: string;
  requester: string;
  responsible: string;
  category?: string;
  status: string;
  priority: string;
  deadline?: string;
  created_at: string;
}

interface TasksTableProps {
  title?: string;
  tasks: Task[];
  loading?: boolean;
  showPagination?: boolean;
  onEdit?: (task: Task) => void;
  onView?: (task: Task) => void;
  onDelete?: (taskId: string) => void;
}

const TasksTable: React.FC<TasksTableProps> = ({
  title = 'Tâches',
  tasks,
  loading = false,
  showPagination = true,
  onEdit,
  onView,
  onDelete,
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'done':
      case 'terminé':
        return 'success';
      case 'in-progress':
      case 'en cours':
        return 'warning';
      case 'pending':
      case 'en attente':
        return 'info';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
      case 'élevé':
        return 'error';
      case 'medium':
      case 'moyen':
        return 'warning';
      case 'low':
      case 'faible':
        return 'success';
      default:
        return 'default';
    }
  };

  const paginatedTasks = showPagination 
    ? tasks.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
    : tasks;

  if (loading) {
    return (
      <Card>
        <CardHeader title={title} />
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
      <CardHeader title={title} />
      <CardContent sx={{ p: 0 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>PO</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Client</TableCell>
                <TableCell>Responsable</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell>Priorité</TableCell>
                <TableCell>Échéance</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedTasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary" sx={{ py: 4 }}>
                      Aucune tâche trouvée
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedTasks.map((task) => (
                  <TableRow key={task.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {task.po_number}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ maxWidth: 200 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {task.action_description}
                        </Typography>
                        {task.category && (
                          <Chip
                            label={task.category}
                            size="small"
                            variant="outlined"
                            sx={{ mt: 0.5 }}
                          />
                        )}
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
                      <Chip
                        label={task.priority}
                        size="small"
                        color={getPriorityColor(task.priority)}
                        variant="outlined"
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
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {onView && (
                          <Tooltip title="Voir">
                            <IconButton size="small" onClick={() => onView(task)}>
                              <ViewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {onEdit && (
                          <Tooltip title="Modifier">
                            <IconButton size="small" onClick={() => onEdit(task)}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {onDelete && (
                          <Tooltip title="Supprimer">
                            <IconButton 
                              size="small" 
                              onClick={() => onDelete(task.id)}
                              color="error"
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {showPagination && tasks.length > 0 && (
          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={tasks.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            labelRowsPerPage="Lignes par page:"
            labelDisplayedRows={({ from, to, count }) =>
              `${from}-${to} sur ${count !== -1 ? count : `plus de ${to}`}`
            }
          />
        )}
      </CardContent>
    </Card>
  );
};

export default TasksTable;