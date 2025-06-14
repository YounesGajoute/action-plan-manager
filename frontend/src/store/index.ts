import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import uiSlice from './slices/uiSlice';
import tasksSlice from './slices/tasksSlice';
import notificationsSlice from './slices/notificationsSlice';
import { api } from './api/baseApi'; // Import the base API

export const store = configureStore({
  reducer: {
    auth: authSlice,
    ui: uiSlice,
    tasks: tasksSlice,
    notifications: notificationsSlice,
    // Use the base API reducer which includes all injected endpoints
    [api.reducerPath]: api.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }).concat(
      // Add the API middleware
      api.middleware
    ),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;