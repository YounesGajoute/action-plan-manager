import { Configuration } from '@azure/msal-browser';
import { env } from './environment';

export const msalConfig: Configuration = {
  auth: {
    clientId: env.msClientId,
    authority: env.msAuthority,
    redirectUri: env.msRedirectUri,
    knownAuthorities: [env.msAuthority],
  },
  cache: {
    cacheLocation: 'localStorage', // or 'sessionStorage'
    storeAuthStateInCookie: false, // Set to true for IE11 support
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        
        switch (level) {
          case 0: // Error
            console.error(`[MSAL Error] ${message}`);
            break;
          case 1: // Warning
            console.warn(`[MSAL Warning] ${message}`);
            break;
          case 2: // Info
            if (env.isDevelopment) {
              console.info(`[MSAL Info] ${message}`);
            }
            break;
          case 3: // Verbose
            if (env.isDevelopment) {
              console.debug(`[MSAL Debug] ${message}`);
            }
            break;
        }
      },
      logLevel: env.isDevelopment ? 3 : 1, // Verbose in dev, Warning+ in prod
    },
  },
};

export const loginRequest = {
  scopes: ['User.Read', 'Files.ReadWrite.All'],
};

export const graphConfig = {
  graphMeEndpoint: 'https://graph.microsoft.com/v1.0/me',
  graphFilesEndpoint: 'https://graph.microsoft.com/v1.0/me/drive',
};
