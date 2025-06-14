interface EnvironmentConfig {
  apiUrl: string;
  wsUrl: string;
  msClientId: string;
  msTenantId: string;
  msAuthority: string;
  msRedirectUri: string;
  enableMsAuth: boolean;
  enableOneDriveSync: boolean;
  isDevelopment: boolean;
  isProduction: boolean;
  debug: boolean;
  version: string;
}

// Validate required environment variables
const requiredEnvVars = [
  'REACT_APP_API_URL',
  'REACT_APP_WS_URL',
  'REACT_APP_MS_CLIENT_ID',
  'REACT_APP_MS_TENANT_ID',
  'REACT_APP_MS_AUTHORITY',
  'REACT_APP_MS_REDIRECT_URI',
];

const missingVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingVars.length > 0 && process.env.NODE_ENV === 'production') {
  console.error(
    `Missing required environment variables: ${missingVars.join(', ')}\n` +
    'Please check your .env file and ensure all required variables are set.'
  );
}

// Provide defaults for development
const getEnvVar = (key: string, defaultValue: string = '') => {
  return process.env[key] || defaultValue;
};

export const env: EnvironmentConfig = {
  apiUrl: getEnvVar('REACT_APP_API_URL', 'http://localhost:5000'),
  wsUrl: getEnvVar('REACT_APP_WS_URL', 'ws://localhost:5000'),
  msClientId: getEnvVar('REACT_APP_MS_CLIENT_ID'),
  msTenantId: getEnvVar('REACT_APP_MS_TENANT_ID'),
  msAuthority: getEnvVar('REACT_APP_MS_AUTHORITY'),
  msRedirectUri: getEnvVar('REACT_APP_MS_REDIRECT_URI', 'http://localhost:3000/auth/callback'),
  enableMsAuth: getEnvVar('REACT_APP_ENABLE_MS_AUTH', 'true') === 'true',
  enableOneDriveSync: getEnvVar('REACT_APP_ENABLE_ONEDRIVE_SYNC', 'true') === 'true',
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
  debug: getEnvVar('REACT_APP_DEBUG', 'false') === 'true',
  version: getEnvVar('REACT_APP_VERSION', '1.0.0'),
};

// Validate URLs in production
if (env.isProduction && env.debug) {
  const productionValidation = [
    { name: 'API URL', value: env.apiUrl, shouldNotContain: 'localhost' },
    { name: 'WebSocket URL', value: env.wsUrl, shouldNotContain: 'localhost' },
    { name: 'Redirect URI', value: env.msRedirectUri, shouldNotContain: 'localhost' },
  ];

  const productionErrors = productionValidation
    .filter(({ value, shouldNotContain }) => value.includes(shouldNotContain))
    .map(({ name }) => name);

  if (productionErrors.length > 0) {
    console.warn(
      `Production build warning: ${productionErrors.join(', ')} ` +
      'contain localhost URLs. This may cause issues in production.'
    );
  }
}

export default env;