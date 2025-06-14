import { useState, useCallback, useEffect } from 'react';

interface AnalyticsData {
  dashboardData: {
    weeklyProgress: Array<{
      date: string;
      created: number;
      completed: number;
    }>;
    changes: {
      totalTasks: number;
      completedTasks: number;
      inProgressTasks: number;
      overdueTasks: number;
    };
  } | null;
  loading: boolean;
  error: string | null;
}

export const useAnalytics = () => {
  const [data, setData] = useState<AnalyticsData>({
    dashboardData: null,
    loading: false,
    error: null,
  });

  const fetchAnalytics = useCallback(async () => {
    setData(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const token = localStorage.getItem('msalAccessToken');
      const response = await fetch('/api/analytics/dashboard', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const analyticsData = await response.json();
      setData(prev => ({
        ...prev,
        dashboardData: analyticsData,
        loading: false,
      }));
    } catch (error) {
      setData(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
        loading: false,
      }));
    }
  }, []);

  const refreshAnalytics = useCallback(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return {
    ...data,
    refreshAnalytics,
  };
};