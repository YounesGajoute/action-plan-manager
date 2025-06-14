import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
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
  Typography,
  Skeleton,
  Tooltip,
  TextField,
  InputAdornment,
  Grid,
  MenuItem,
  Button,
  Toolbar,
  alpha,
} from '@mui/material';
import {
  Edit as EditIcon,
  Visibility as ViewIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  Add as AddIcon,
  FileDownload as ExportIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { Task } from '../../types/task';
import { TASK_STATUSES, TASK_CATEGORIES, TASK_PRIORITIES } from '../../utils/constants';
import { getStatusColor, getPriorityColor, isOverdue, getDaysUntilDeadline } from '../../utils/helpers';

interface TaskListProps {
  tasks: Task[];
  loading?: boolean;
  onEdit?: (task: Task) => void;
  onView?: (task: Task) => void;
  onDelete?: (taskId: string) => void;
  onCreate?: () => void;
  onExport?: () => void;
}

interface FilterState {
  search: string;
  status: string;
  category: string;
  priority: string;
  responsible: string;
}

const TaskList: React.FC<TaskListProps> = ({
  tasks,
  loading = false,
  onEdit,
  onView,
  onDelete,
  onCreate,
  onExport,
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    status: '',
    category: '',
    priority: '',
    responsible: '',
  });

  // Filter tasks based on current filters
  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const matchesSearch = !filters.search || 
        task.action_description.toLowerCase().includes(filters.search.toLowerCase()) ||
        task.customer.toLowerCase().includes(filters.search.toLowerCase()) ||
        task.po_number?.toLowerCase().includes(filters.search.toLowerCase()) ||
        task.responsible.toLowerCase().includes(filters.search.toLowerCase());

      const matchesStatus = !filters.status || task.status === filters.status;
      const matchesCategory = !filters.category || task.category === filters.category;
      const matchesPriority = !filters.priority || task.priority === filters.priority;
      const matchesResponsible = !filters.responsible || task.responsible === filters.responsible;

      return matchesSearch && matchesStatus && matchesCategory && matchesPriority && matchesResponsible;
    });
  }, [tasks, filters]);

  // Paginated tasks
  const paginatedTasks = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return filteredTasks.slice(startIndex, startIndex + rowsPerPage);
  }, [filteredTasks, page, rowsPerPage]);

  // Get unique responsible persons for filter
  const responsibleOptions = useMemo(() => {
    const unique = Array.from(new Set(tasks.map(task => task.responsible)));
    return unique.sort();
  }, [tasks]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleFilterChange = (field: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setPage(0); // Reset to first page when filtering
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      status: '',
      category: '',
      priority: '',
      responsible: '',
    });
    setPage(0);
  };

  const getDeadlineStatus = (deadline: string | undefined) => {
    if (!deadline) return null;
    
    const daysUntil = getDaysUntilDeadline(deadline);
    if (daysUntil === null) return null;
    
    if (daysUntil < 0) {
      return { text: `${Math.abs(daysUntil)} j. retard`, color: 'error' as const };
    } else if (daysUntil === 0) {
      return { text: 'Aujourd\'hui', color: 'warning' as const };
    } else if (daysUntil <= 3) {
      return { text: `${daysUntil} j. restants`, color: 'warning' as const };
    } else {
      return { text: `${daysUntil} j. restants`, color: 'info' as const };
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          {[...Array(10)].map((_, index) => (
            <Skeleton key={index} variant="rectangular" height={60} sx={{ mb: 1 }} />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {/* Toolbar */}
      <Toolbar
        sx={{
          pl: { sm: 2 },
          pr: { xs: 1, sm: 1 },
          bgcolor: (theme) => alpha(theme.palette.primary.main, 0.05),
        }}
      >
        <Typography
          sx={{ flex: '1 1 100%' }}
          variant="h6"
          id="tableTitle"
          component="div"
          fontWeight={600}
        >
          Gestion des Tâches
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          {onExport && (
            <Tooltip title="Exporter">
              <IconButton onClick={onExport}>
                <ExportIcon />
              </IconButton>
            </Tooltip>
          )}
          {onCreate && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={onCreate}
              size="small"
            >
              Nouvelle Tâche
            </Button>
          )}
        </Box>
      </Toolbar>

      {/* Filters */}
      <CardContent>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              size="small"
              placeholder="Rechercher..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          
          <Grid item xs={6} md={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Statut"
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
            >
              <MenuItem value="">Tous</MenuItem>
              {Object.values(TASK_STATUSES).map((status) => (
                <MenuItem key={status} value={status}>
                  {status}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={6} md={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Catégorie"
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
            >
              <MenuItem value="">Toutes</MenuItem>
              {Object.values(TASK_CATEGORIES).map((category) => (
                <MenuItem key={category} value={category}>
                  {category}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={6} md={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Priorité"
              value={filters.priority}
              onChange={(e) => handleFilterChange('priority', e.target.value)}
            >
              <MenuItem value="">Toutes</MenuItem>
              {Object.values(TASK_PRIORITIES).map((priority) => (
                <MenuItem key={priority} value={priority}>
                  {priority}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={6} md={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Responsable"
              value={filters.responsible}
              onChange={(e) => handleFilterChange('responsible', e.target.value)}
            >
              <MenuItem value="">Tous</MenuItem>
              {responsibleOptions.map((responsible) => (
                <MenuItem key={responsible} value={responsible}>
                  {responsible}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={12} md={1}>
            <Button
              fullWidth
              variant="outlined"
              size="small"
              onClick={clearFilters}
              sx={{ height: '40px' }}
            >
              Effacer
            </Button>
          </Grid>
        </Grid>

        {/* Results Count */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {filteredTasks.length} tâche(s) trouvée(s) sur {tasks.length} au total
        </Typography>

        {/* Table */}
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>PO / Action</TableCell>
                <TableCell>Client</TableCell>
                <TableCell>Responsable</TableCell>
                <TableCell>Statut</TableCell>
                <TableCell>Priorité</TableCell>
                <TableCell>Échéance</TableCell>
                <TableCell>Catégorie</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedTasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary" sx={{ py: 4 }}>
                      {filters.search || filters.status || filters.category || filters.priority || filters.responsible
                        ? 'Aucune tâche ne correspond aux filtres'
                        : 'Aucune tâche trouvée'
                      }
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedTasks.map((task) => {
                  const deadlineStatus = getDeadlineStatus(task.deadline);
                  
                  return (
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
                              maxWidth: 250,
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
                        {task.priority && (
                          <Chip
                            label={task.priority}
                            size="small"
                            color={getPriorityColor(task.priority)}
                            variant="outlined"
                          />
                        )}
                      </TableCell>
                      
                      <TableCell>
                        {task.deadline ? (
                          <Box>
                            <Typography variant="body2">
                              {format(new Date(task.deadline), 'dd/MM/yyyy', { locale: fr })}
                            </Typography>
                            {deadlineStatus && (
                              <Chip
                                label={deadlineStatus.text}
                                size="small"
                                color={deadlineStatus.color}
                                variant="outlined"
                                sx={{ mt: 0.5 }}
                              />
                            )}
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Non définie
                          </Typography>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        {task.category && (
                          <Chip
                            label={task.category}
                            size="small"
                            variant="outlined"
                          />
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
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        {filteredTasks.length > 0 && (
          <TablePagination
            rowsPerPageOptions={[5, 10, 25, 50]}
            component="div"
            count={filteredTasks.length}
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

export default TaskList;