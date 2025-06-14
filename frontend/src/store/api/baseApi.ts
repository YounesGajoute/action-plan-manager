import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { RootState } from '../index';

// Base query with auth token injection
const baseQuery = fetchBaseQuery({
  baseUrl: process.env.REACT_APP_API_URL!,
  prepareHeaders: (headers, { getState }) => {
    // Get token from localStorage (MSAL handles this)
    const token = localStorage.getItem('msalAccessToken');
    
    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }
    
    headers.set('content-type', 'application/json');
    return headers;
  },
});

// Base query with retry logic
const baseQueryWithRetry = async (args: any, api: any, extraOptions: any) => {
  let result = await baseQuery(args, api, extraOptions);

  // Handle 401 errors (token expiry)
  if (result.error && result.error.status === 401) {
    // Try to refresh token or redirect to login
    console.warn('Token expired, redirecting to login');
    localStorage.removeItem('msalAccessToken');
    window.location.href = '/login';
  }

  return result;
};

export const api = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithRetry,
  tagTypes: ['Task', 'User', 'Analytics', 'Notification', 'Sync'],
  endpoints: () => ({}),
});
