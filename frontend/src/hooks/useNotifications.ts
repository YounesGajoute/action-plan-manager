import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import {
  setNotifications,
  addNotification,
  markAsRead,
  markAllAsRead,
} from '../store/slices/notificationsSlice';

export const useNotifications = () => {
  const dispatch = useAppDispatch();
  const { notifications, unreadCount, loading } = useAppSelector(
    (state) => state.notifications
  );

  const fetchNotifications = useCallback(async () => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch('/api/notifications', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch notifications');
      }

      const data = await response.json();
      dispatch(setNotifications(data.notifications || []));
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  }, [dispatch]);

  const markNotificationAsRead = useCallback(async (id: string) => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      await fetch(`/api/notifications/${id}/read`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      dispatch(markAsRead(id));
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  }, [dispatch]);

  const markAllNotificationsAsRead = useCallback(async () => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      await fetch('/api/notifications/read-all', {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      dispatch(markAllAsRead());
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  }, [dispatch]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  return {
    notifications,
    unreadCount,
    loading,
    markAsRead: markNotificationAsRead,
    markAllAsRead: markAllNotificationsAsRead,
    refresh: fetchNotifications,
  };
};