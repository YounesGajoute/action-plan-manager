import { api } from './baseApi';
import { Task, TaskCounts } from '../../types/task';

export interface TasksResponse {
  tasks: Task[];
  counts: TaskCounts;
  total: number;
  page: number;
  pages: number;
}

export interface TaskFilters {
  status?: string;
  category?: string;
  responsible?: string;
  customer?: string;
  priority?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
  page?: number;
  limit?: number;
}

export const tasksApi = api.injectEndpoints({
  endpoints: (builder) => ({
    // Get all tasks with filters
    getTasks: builder.query<TasksResponse, TaskFilters | void>({
      query: (filters = {}) => ({
        url: '/tasks',
        params: filters,
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.tasks.map(({ id }) => ({ type: 'Task' as const, id })),
              { type: 'Task', id: 'LIST' },
            ]
          : [{ type: 'Task', id: 'LIST' }],
    }),

    // Get single task
    getTask: builder.query<Task, string>({
      query: (id) => `/tasks/${id}`,
      providesTags: (result, error, id) => [{ type: 'Task', id }],
    }),

    // Create new task
    createTask: builder.mutation<Task, Partial<Task>>({
      query: (task) => ({
        url: '/tasks',
        method: 'POST',
        body: task,
      }),
      invalidatesTags: [{ type: 'Task', id: 'LIST' }],
    }),

    // Update task
    updateTask: builder.mutation<Task, { id: string; data: Partial<Task> }>({
      query: ({ id, data }) => ({
        url: `/tasks/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    // Delete task
    deleteTask: builder.mutation<void, string>({
      query: (id) => ({
        url: `/tasks/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    // Bulk import tasks from Excel
    importTasks: builder.mutation<{ imported: number; errors: string[] }, FormData>({
      query: (formData) => ({
        url: '/tasks/import',
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: [{ type: 'Task', id: 'LIST' }],
    }),

    // Export tasks to Excel
    exportTasks: builder.mutation<Blob, TaskFilters | void>({
      query: (filters = {}) => ({
        url: '/tasks/export',
        method: 'POST',
        body: filters,
        responseHandler: (response) => response.blob(),
      }),
    }),

    // Get dashboard analytics
    getDashboardAnalytics: builder.query<any, void>({
      query: () => '/tasks/analytics/dashboard',
      providesTags: ['Analytics'],
    }),
  }),
});

export const {
  useGetTasksQuery,
  useGetTaskQuery,
  useCreateTaskMutation,
  useUpdateTaskMutation,
  useDeleteTaskMutation,
  useImportTasksMutation,
  useExportTasksMutation,
  useGetDashboardAnalyticsQuery,
} = tasksApi;