import { useState, useCallback, useEffect } from 'react';

interface SyncStatus {
  isOnlineSyncActive: boolean;
  lastSyncTime: string | null;
  syncInProgress: boolean;
  error: string | null;
}

export const useSyncStatus = () => {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isOnlineSyncActive: false,
    lastSyncTime: null,
    syncInProgress: false,
    error: null,
  });

  const fetchSyncStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch('/api/sync/status', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSyncStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch sync status:', error);
    }
  }, []);

  const triggerSync = useCallback(async () => {
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch('/api/sync/trigger', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setSyncStatus(prev => ({ ...prev, syncInProgress: true }));
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to trigger sync:', error);
      return false;
    }
  }, []);

  useEffect(() => {
    fetchSyncStatus();
    const interval = setInterval(fetchSyncStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, [fetchSyncStatus]);

  return {
    ...syncStatus,
    triggerSync,
    refresh: fetchSyncStatus,
  };
};