import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Box, CircularProgress } from '@mui/material';
import { Toaster } from 'react-hot-toast';
import { ErrorBoundary } from 'react-error-boundary';

import { useAppDispatch, useAppSelector } from './hooks/redux';
import { setUser, clearUser } from './store/slices/authSlice';
import { useWebSocket } from './hooks/useWebSocket';

// Layout Components
import Layout from './components/Layout';
import LoginPage from './components/auth/LoginPage';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Page Components
import Dashboard from './components/Dashboard/Dashboard';
import TasksPage from './pages/TasksPage';
import AnalyticsPage from './pages/AnalyticsPage';
import UsersPage from './pages/UsersPage';
import SettingsPage from './pages/SettingsPage';
import ProfilePage from './pages/ProfilePage';
import NotFoundPage from './pages/NotFoundPage';

// Error Fallback Component
const ErrorFallback: React.FC<{ error: Error; resetErrorBoundary: () => void }> = ({
  error,
  resetErrorBoundary,
}) => (
  <Box
    display="flex"
    flexDirection="column"
    alignItems="center"
    justifyContent="center"
    minHeight="100vh"
    p={3}
  >
    <Typography variant="h4" color="error" gutterBottom>
      Quelque chose s'est mal passé
    </Typography>
    <Typography variant="body1" color="text.secondary" paragraph>
      {error.message}
    </Typography>
    <Button variant="contained" onClick={resetErrorBoundary}>
      Réessayer
    </Button>
  </Box>
);

// Styles
import './App.css';

const App: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const isAuthenticatedMsal = useIsAuthenticated();
  const { accounts, instance } = useMsal();
  
  // Initialize WebSocket connection for authenticated users
  useWebSocket(isAuthenticated || isAuthenticatedMsal);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        if (isAuthenticatedMsal && accounts.length > 0) {
          const account = accounts[0];
          
          // Set user in Redux store
          dispatch(setUser({
            id: account.localAccountId || account.homeAccountId,
            email: account.username,
            name: account.name || account.username,
            roles: ['user'], // Default role, will be updated from backend
            tenantId: account.tenantId,
            isAuthenticated: true
          }));

          // Get additional user info from Microsoft Graph
          try {
            const response = await instance.acquireTokenSilent({
              scopes: ['User.Read'],
              account: account
            });

            // Store access token for API calls
            localStorage.setItem('msalAccessToken', response.accessToken);
            
          } catch (error) {
            console.warn('Failed to acquire token silently:', error);
          }
        } else {
          dispatch(clearUser());
        }
      } catch (error) {
        console.error('Authentication initialization error:', error);
        dispatch(clearUser());
      }
    };

    initializeAuth();
  }, [isAuthenticatedMsal, accounts, instance, dispatch]);

  // Show loading spinner during initialization
  if (isAuthenticatedMsal === undefined) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        height="100vh"
        bgcolor="background.default"
      >
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      {/* Global Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
            fontSize: '14px',
            fontFamily: 'Roboto, sans-serif',
          },
          success: {
            style: {
              background: '#4caf50',
            },
          },
          error: {
            style: {
              background: '#f44336',
            },
          },
        }}
      />

      <Routes>
        {/* Public Routes */}
        <Route 
          path="/login" 
          element={
            isAuthenticatedMsal ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage />
            )
          } 
        />

        {/* Protected Routes */}
        <Route 
          path="/*" 
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  {/* Default redirect to dashboard */}
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  
                  {/* Main Application Routes */}
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/tasks/*" element={<TasksPage />} />
                  <Route path="/analytics" element={<AnalyticsPage />} />
                  <Route path="/users" element={<UsersPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  
                  {/* 404 Page */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          } 
        />
      </Routes>
    </ErrorBoundary>
  );
};

export default App;
