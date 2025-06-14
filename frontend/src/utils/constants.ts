// ===================================================================
// frontend/src/utils/constants.ts
// ===================================================================
export const APP_CONFIG = {
  NAME: 'Action Plan Management System',
  VERSION: '1.0.0',
  DESCRIPTION: 'Système de gestion des plans d\'action TechMac',
} as const;

export const API_ENDPOINTS = {
  AUTH: '/auth',
  TASKS: '/api/tasks',
  USERS: '/api/users',
  ANALYTICS: '/api/analytics',
  NOTIFICATIONS: '/api/notifications',
  SYNC: '/api/sync',
  FILES: '/api/files',
} as const;

export const TASK_STATUSES = {
  PENDING: 'En Attente',
  IN_PROGRESS: 'En Cours',
  COMPLETED: 'Terminé',
  CANCELLED: 'Annulé',
  ON_HOLD: 'En Pause',
} as const;

export const TASK_PRIORITIES = {
  LOW: 'Faible',
  MEDIUM: 'Moyen',
  HIGH: 'Élevé',
  URGENT: 'Urgent',
} as const;

export const TASK_CATEGORIES = {
  INSTALLATION: 'Installation',
  REPARATION: 'Réparation',
  DEVELOPPEMENT: 'Développement',
  LIVRAISON: 'Livraison',
  COMMERCIAL: 'Commercial',
} as const;

export const USER_ROLES = {
  ADMIN: 'admin',
  MANAGER: 'manager',
  USER: 'user',
  READ_ONLY: 'read-only',
} as const;

export const NOTIFICATION_TYPES = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
} as const;

export const DATE_FORMATS = {
  DISPLAY: 'dd/MM/yyyy',
  DISPLAY_WITH_TIME: 'dd/MM/yyyy HH:mm',
  API: 'yyyy-MM-dd',
  ISO: 'yyyy-MM-dd\'T\'HH:mm:ss.SSSxxx',
} as const;

export const CHART_COLORS = {
  PRIMARY: '#1976d2',
  SECONDARY: '#dc004e',
  SUCCESS: '#2e7d32',
  WARNING: '#ed6c02',
  ERROR: '#d32f2f',
  INFO: '#0288d1',
  GREY: '#757575',
} as const;

export const PAGINATION_DEFAULTS = {
  PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [5, 10, 25, 50],
} as const;

export const STORAGE_KEYS = {
  AUTH_TOKEN: 'msalAccessToken',
  DARK_MODE: 'darkMode',
  SIDEBAR_STATE: 'sidebarOpen',
  USER_PREFERENCES: 'userPreferences',
} as const;

export const VALIDATION_RULES = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^(\+212|0)[5-7]\d{8}$/,
  PO_NUMBER: /^[A-Z0-9-]+$/,
} as const;

export const FILE_TYPES = {
  EXCEL: '.xlsx,.xls',
  CSV: '.csv',
  PDF: '.pdf',
  IMAGES: '.jpg,.jpeg,.png,.gif',
  DOCUMENTS: '.doc,.docx,.pdf,.txt',
} as const;

export const SYNC_INTERVALS = {
  NEVER: 0,
  MINUTES_5: 5 * 60 * 1000,
  MINUTES_15: 15 * 60 * 1000,
  MINUTES_30: 30 * 60 * 1000,
  HOUR_1: 60 * 60 * 1000,
} as const;