// ===================================================================
// frontend/src/types/index.ts
// ===================================================================
export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  tenantId?: string;
  isAuthenticated: boolean;
}

export interface Task {
  id: string;
  po_number: string;
  action_description: string;
  customer: string;
  requester: string;
  responsible: string;
  category?: string;
  status: string;
  priority: string;
  deadline?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCounts {
  total: number;
  pending: number;
  inProgress: number;
  completed: number;
  overdue: number;
  byCategory: {
    installation: number;
    reparation: number;
    developpement: number;
    livraison: number;
    commercial: number;
  };
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  created_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  per_page: number;
}

export interface FilterOptions {
  status?: string;
  category?: string;
  responsible?: string;
  customer?: string;
  dateRange?: [string, string];
  priority?: string;
}

export interface ChartDataPoint {
  name: string;
  value: number;
  color?: string;
}

export interface TimeSeriesData {
  date: string;
  [key: string]: string | number;
}

export interface SyncStatus {
  isOnlineSyncActive: boolean;
  lastSyncTime: string | null;
  syncInProgress: boolean;
  error: string | null;
}

export interface UserPermissions {
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canView: boolean;
  canManageUsers: boolean;
  canAccessSettings: boolean;
  canExportData: boolean;
}
