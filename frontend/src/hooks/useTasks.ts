// ===================================================================
// frontend/src/hooks/useTasks.ts
// ===================================================================
import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import {
  setTasks,
  setTaskCounts,
  setLoading,
  setError,
  addTask,
  updateTask,
  deleteTask,
} from '../store/slices/tasksSlice';

interface TaskData {
  id?: string;
  po_number: string;
  action_description: string;
  customer: string;
  requester: string;
  responsible: string;
  category?: string;
  status?: string;
  priority?: string;
  deadline?: string;
  notes?: string;
}

export const useTasks = () => {
  const dispatch = useAppDispatch();
  const { tasks, taskCounts, loading, error, filters } = useAppSelector(
    (state) => state.tasks
  );

  const fetchTasks = useCallback(async () => {
    dispatch(setLoading(true));
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch('/api/tasks', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch tasks');
      }

      const data = await response.json();
      dispatch(setTasks(data.tasks || []));
      dispatch(setTaskCounts(data.counts || null));
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const createTask = useCallback(async (taskData: TaskData) => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData),
      });

      if (!response.ok) {
        throw new Error('Failed to create task');
      }

      const newTask = await response.json();
      dispatch(addTask(newTask));
      return newTask;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Unknown error'));
      throw error;
    }
  }, [dispatch]);

  const updateTaskById = useCallback(async (id: string, taskData: Partial<TaskData>) => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch(`/api/tasks/${id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData),
      });

      if (!response.ok) {
        throw new Error('Failed to update task');
      }

      const updatedTask = await response.json();
      dispatch(updateTask(updatedTask));
      return updatedTask;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Unknown error'));
      throw error;
    }
  }, [dispatch]);

  const deleteTaskById = useCallback(async (id: string) => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch(`/api/tasks/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete task');
      }

      dispatch(deleteTask(id));
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Unknown error'));
      throw error;
    }
  }, [dispatch]);

  const refreshTasks = useCallback(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks, filters]);

  return {
    tasks,
    taskCounts,
    loading,
    error,
    createTask,
    updateTask: updateTaskById,
    deleteTask: deleteTaskById,
    refreshTasks,
  };
};
