export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
  timestamp: string;
}

export interface ApiError {
  success: false;
  error: string;
  details?: string;
  code?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  perPage: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface FilterParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  search?: string;
}

export interface TaskFilterParams extends FilterParams {
  status?: string;
  category?: string;
  responsible?: string;
  customer?: string;
  priority?: string;
  dateFrom?: string;
  dateTo?: string;
  overdue?: boolean;
}

export interface AnalyticsParams {
  startDate?: string;
  endDate?: string;
  groupBy?: 'day' | 'week' | 'month';
  categories?: string[];
  responsible?: string[];
}

export interface ImportResponse {
  imported: number;
  errors: string[];
  warnings: string[];
  skipped: number;
  duplicates: number;
}

export interface ExportRequest {
  format: 'excel' | 'csv' | 'pdf';
  filters?: TaskFilterParams;
  columns?: string[];
  includeNotes?: boolean;
}

export interface SyncStatusResponse {
  isOnlineSyncActive: boolean;
  lastSyncTime: string | null;
  syncInProgress: boolean;
  error: string | null;
  nextSyncTime?: string;
  syncHistory: Array<{
    timestamp: string;
    status: 'success' | 'error';
    message?: string;
    itemsProcessed?: number;
  }>;
}

export interface NotificationResponse {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  createdAt: string;
  updatedAt: string;
  userId: string;
  metadata?: Record<string, any>;
}

export interface WebSocketMessage {
  type: 'task_created' | 'task_updated' | 'task_deleted' | 'notification' | 'sync_status';
  payload: any;
  timestamp: string;
  userId?: string;
}
