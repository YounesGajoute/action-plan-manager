import React from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { PublicClientApplication } from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { fr } from 'date-fns/locale';

import App from './App';
import { store } from './store';
import { theme } from './theme';
import { msalConfig } from './config/authConfig';
import reportWebVitals from './reportWebVitals';

import './styles/globals.css';

// MSAL instance
const msalInstance = new PublicClientApplication(msalConfig);

// Initialize MSAL instance
msalInstance.initialize().then(() => {
  // Handle redirect promise
  msalInstance.handleRedirectPromise().then((response) => {
    if (response !== null) {
      msalInstance.setActiveAccount(response.account);
    } else {
      // Fallback: set active account from cache
      const currentAccounts = msalInstance.getAllAccounts();
      if (currentAccounts.length === 1) {
        msalInstance.setActiveAccount(currentAccounts[0]);
      }
    }
  });
});

const container = document.getElementById('root');
if (!container) throw new Error('Failed to find the root element');

const root = createRoot(container);

root.render(
  <React.StrictMode>
    <MsalProvider instance={msalInstance}>
      <Provider store={store}>
        <BrowserRouter>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={fr}>
              <App />
            </LocalizationProvider>
          </ThemeProvider>
        </BrowserRouter>
      </Provider>
    </MsalProvider>
  </React.StrictMode>
);

// Performance measurement
reportWebVitals(console.log);