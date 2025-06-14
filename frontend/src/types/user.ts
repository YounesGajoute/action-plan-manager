export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  tenantId?: string;
  department?: string;
  position?: string;
  phone?: string;
  location?: string;
  avatar?: string;
  isAuthenticated: boolean;
  lastLogin?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface UserProfile extends User {
  preferences: {
    language: string;
    timezone: string;
    notifications: {
      email: boolean;
      browser: boolean;
      telegram: boolean;
    };
    theme: 'light' | 'dark' | 'auto';
  };
}

export interface UserPermissions {
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canView: boolean;
  canManageUsers: boolean;
  canAccessSettings: boolean;
  canExportData: boolean;
  canImportData: boolean;
  canManageSync: boolean;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  roles: string[];
  department?: string;
  position?: string;
  phone?: string;
}

export interface UpdateUserRequest extends Partial<CreateUserRequest> {
  id: string;
}

export interface UserStats {
  totalUsers: number;
  activeUsers: number;
  newUsersThisMonth: number;
  usersByRole: Record<string, number>;
  usersByDepartment: Record<string, number>;
}