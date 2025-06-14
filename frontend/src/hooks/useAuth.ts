import { useEffect, useCallback } from 'react';
import { useIsAuthenticated, useMsal, useAccount } from '@azure/msal-react';
import { useAppDispatch, useAppSelector } from './redux';
import { setUser, clearUser, setLoading, setError } from '../store/slices/authSlice';
import { useGetMeQuery } from '../store/api/authApi';

export const useAuth = () => {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, loading, error } = useAppSelector((state) => state.auth);
  
  // MSAL hooks
  const isAuthenticatedMsal = useIsAuthenticated();
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});

  // API hook to get user details
  const {
    data: userData,
    isLoading: userLoading,
    error: userError,
    refetch: refetchUser,
  } = useGetMeQuery(undefined, {
    skip: !isAuthenticatedMsal,
  });

  // Initialize authentication state
  useEffect(() => {
    const initializeAuth = async () => {
      if (isAuthenticatedMsal && account) {
        dispatch(setLoading(true));
        
        try {
          // Set basic user info from MSAL
          const basicUser = {
            id: account.localAccountId || account.homeAccountId,
            email: account.username,
            name: account.name || account.username,
            roles: ['user'], // Default role
            isAuthenticated: true,
          };

          dispatch(setUser(basicUser));

          // Get access token for API calls
          const response = await instance.acquireTokenSilent({
            scopes: ['User.Read', 'Files.ReadWrite.All'],
            account: account,
          });

          // Store token for API calls
          localStorage.setItem('msalAccessToken', response.accessToken);

          // Fetch additional user data from backend
          if (userData) {
            dispatch(setUser({
              ...basicUser,
              ...userData,
              isAuthenticated: true,
            }));
          }

        } catch (error) {
          console.error('Authentication initialization error:', error);
          dispatch(setError('Failed to initialize authentication'));
        } finally {
          dispatch(setLoading(false));
        }
      } else {
        dispatch(clearUser());
        localStorage.removeItem('msalAccessToken');
      }
    };

    initializeAuth();
  }, [isAuthenticatedMsal, account, userData, dispatch, instance]);

  // Login function
  const login = useCallback(async () => {
    try {
      await instance.loginRedirect({
        scopes: ['User.Read', 'Files.ReadWrite.All'],
      });
    } catch (error) {
      console.error('Login error:', error);
      dispatch(setError('Login failed'));
    }
  }, [instance, dispatch]);

  // Logout function
  const logout = useCallback(async () => {
    try {
      dispatch(clearUser());
      localStorage.removeItem('msalAccessToken');
      
      await instance.logoutRedirect({
        postLogoutRedirectUri: '/login',
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
  }, [instance, dispatch]);

  // Refresh user data
  const refreshUser = useCallback(() => {
    refetchUser();
  }, [refetchUser]);

  // Get access token
  const getAccessToken = useCallback(async () => {
    if (!account) return null;

    try {
      const response = await instance.acquireTokenSilent({
        scopes: ['User.Read', 'Files.ReadWrite.All'],
        account: account,
      });
      
      localStorage.setItem('msalAccessToken', response.accessToken);
      return response.accessToken;
    } catch (error) {
      console.error('Token acquisition error:', error);
      return null;
    }
  }, [instance, account]);

  // Check if user has specific role
  const hasRole = useCallback((role: string) => {
    return user?.roles?.includes(role) || false;
  }, [user?.roles]);

  // Check if user has any of the specified roles
  const hasAnyRole = useCallback((roles: string[]) => {
    return roles.some(role => hasRole(role));
  }, [hasRole]);

  return {
    // State
    user,
    isAuthenticated: isAuthenticated || isAuthenticatedMsal,
    loading: loading || userLoading,
    error: error || userError,
    
    // Actions
    login,
    logout,
    refreshUser,
    getAccessToken,
    
    // Utilities
    hasRole,
    hasAnyRole,
  };
};