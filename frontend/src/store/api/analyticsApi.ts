import { api } from './baseApi';

export interface DashboardAnalytics {
  taskCounts: {
    total: number;
    completed: number;
    inProgress: number;
    pending: number;
    overdue: number;
  };
  categoryDistribution: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
  weeklyProgress: Array<{
    date: string;
    created: number;
    completed: number;
  }>;
  teamPerformance: Array<{
    responsible: string;
    completed: number;
    pending: number;
    completionRate: number;
  }>;
  changes: {
    totalTasks: number;
    completedTasks: number;
    inProgressTasks: number;
    overdueTasks: number;
  };
}

export interface PerformanceMetrics {
  averageCompletionTime: number;
  onTimeDeliveryRate: number;
  overdueTasks: number;
  productivityTrend: Array<{
    period: string;
    productivity: number;
  }>;
}

export interface ReportRequest {
  startDate: string;
  endDate: string;
  format: 'pdf' | 'excel' | 'csv';
  includeCharts: boolean;
  categories?: string[];
  responsible?: string[];
}

export const analyticsApi = api.injectEndpoints({
  endpoints: (builder) => ({
    // Get dashboard analytics
    getDashboardAnalytics: builder.query<DashboardAnalytics, void>({
      query: () => '/analytics/dashboard',
      providesTags: ['Analytics'],
    }),

    // Get performance metrics
    getPerformanceMetrics: builder.query<PerformanceMetrics, { period?: string }>({
      query: (params) => ({
        url: '/analytics/performance',
        params,
      }),
      providesTags: ['Analytics'],
    }),

    // Get category analytics
    getCategoryAnalytics: builder.query<any, { category: string; period?: string }>({
      query: (params) => ({
        url: '/analytics/categories',
        params,
      }),
      providesTags: ['Analytics'],
    }),

    // Get team analytics
    getTeamAnalytics: builder.query<any, { team?: string; period?: string }>({
      query: (params) => ({
        url: '/analytics/team',
        params,
      }),
      providesTags: ['Analytics'],
    }),

    // Generate report
    generateReport: builder.mutation<Blob, ReportRequest>({
      query: (reportData) => ({
        url: '/analytics/reports/generate',
        method: 'POST',
        body: reportData,
        responseHandler: (response) => response.blob(),
      }),
    }),

    // Get trending tasks
    getTrendingTasks: builder.query<any, { period?: string; limit?: number }>({
      query: (params) => ({
        url: '/analytics/trending',
        params,
      }),
      providesTags: ['Analytics'],
    }),
  }),
});

export const {
  useGetDashboardAnalyticsQuery,
  useGetPerformanceMetricsQuery,
  useGetCategoryAnalyticsQuery,
  useGetTeamAnalyticsQuery,
  useGenerateReportMutation,
  useGetTrendingTasksQuery,
} = analyticsApi;
