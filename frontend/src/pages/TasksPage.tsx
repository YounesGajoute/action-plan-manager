import React, { useState } from 'react';
import { Box, Typography, Fab, Dialog } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useGetTasksQuery, useCreateTaskMutation, useUpdateTaskMutation, useDeleteTaskMutation } from '../store/api/tasksApi';
import { Task } from '../types/task';
import TaskList from '../components/Tasks/TaskList';
import TaskForm from '../components/Tasks/TaskForm';
import toast from 'react-hot-toast';

const TasksPage: React.FC = () => {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  // API hooks
  const { data: tasksData, isLoading, refetch } = useGetTasksQuery();
  const [createTask, { isLoading: isCreating }] = useCreateTaskMutation();
  const [updateTask, { isLoading: isUpdating }] = useUpdateTaskMutation();
  const [deleteTask] = useDeleteTaskMutation();

  const tasks = tasksData?.tasks || [];

  const handleCreateTask = () => {
    setSelectedTask(null);
    setFormOpen(true);
  };

  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    setFormOpen(true);
  };

  const handleViewTask = (task: Task) => {
    // Navigate to task detail page or open view modal
    console.log('View task:', task);
  };

  const handleDeleteTask = async (taskId: string) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cette tâche ?')) {
      try {
        await deleteTask(taskId).unwrap();
        toast.success('Tâche supprimée avec succès');
      } catch (error) {
        toast.error('Erreur lors de la suppression de la tâche');
      }
    }
  };

  const handleFormSubmit = async (data: Partial<Task>) => {
    try {
      if (selectedTask) {
        await updateTask({ id: selectedTask.id, data }).unwrap();
        toast.success('Tâche mise à jour avec succès');
      } else {
        await createTask(data).unwrap();
        toast.success('Tâche créée avec succès');
      }
      setFormOpen(false);
      refetch();
    } catch (error) {
      const message = selectedTask ? 'Erreur lors de la mise à jour' : 'Erreur lors de la création';
      toast.error(message);
      throw error;
    }
  };

  const handleExport = () => {
    // Implement export functionality
    toast.info('Export en cours de développement');
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight={700}>
          Gestion des Tâches
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Créez, modifiez et suivez vos tâches en temps réel
        </Typography>
      </Box>

      {/* Task List */}
      <TaskList
        tasks={tasks}
        loading={isLoading}
        onEdit={handleEditTask}
        onView={handleViewTask}
        onDelete={handleDeleteTask}
        onCreate={handleCreateTask}
        onExport={handleExport}
      />

      {/* Task Form Dialog */}
      <TaskForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={handleFormSubmit}
        task={selectedTask}
        loading={isCreating || isUpdating}
      />

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add task"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
        }}
        onClick={handleCreateTask}
      >
        <AddIcon />
      </Fab>
    </Box>
  );
};

export default TasksPage;