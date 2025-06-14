import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAppDispatch } from './redux';
import { addNotification } from '../store/slices/notificationsSlice';
import { updateTask, addTask } from '../store/slices/tasksSlice';
import toast from 'react-hot-toast';

export const useWebSocket = (isAuthenticated: boolean) => {
  const dispatch = useAppDispatch();
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    // Initialize WebSocket connection
    const token = localStorage.getItem('msalAccessToken');
    socketRef.current = io(process.env.REACT_APP_WS_URL || 'ws://localhost:5000', {
      auth: {
        token,
      },
      transports: ['websocket'],
    });

    const socket = socketRef.current;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    // Task event handlers
    socket.on('task_created', (task) => {
      dispatch(addTask(task));
      toast.success('Nouvelle tâche créée');
    });

    socket.on('task_updated', (task) => {
      dispatch(updateTask(task));
      toast.info('Tâche mise à jour');
    });

    socket.on('task_completed', (task) => {
      dispatch(updateTask(task));
      toast.success(`Tâche "${task.action_description}" terminée`);
    });

    // Notification event handlers
    socket.on('notification', (notification) => {
      dispatch(addNotification(notification));
      toast(notification.message, {
        icon: notification.type === 'success' ? '✅' : 
              notification.type === 'warning' ? '⚠️' : 
              notification.type === 'error' ? '❌' : 'ℹ️',
      });
    });

    // Sync event handlers
    socket.on('sync_started', () => {
      toast.loading('Synchronisation en cours...', { id: 'sync' });
    });

    socket.on('sync_completed', () => {
      toast.success('Synchronisation terminée', { id: 'sync' });
    });

    socket.on('sync_error', (error) => {
      toast.error(`Erreur de synchronisation: ${error.message}`, { id: 'sync' });
    });

    // Cleanup on unmount
    return () => {
      socket.disconnect();
    };
  }, [isAuthenticated, dispatch]);

  return socketRef.current;
};