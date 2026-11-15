import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth, connectAuthEmulator } from 'firebase/auth';
import { readAuthConfig } from './authConfig.js';

let auth = null;
let authConfigurationError = '';
try {
  const {config, emulatorUrl} = readAuthConfig(import.meta.env);
  const app = getApps().length ? getApp() : initializeApp(config);
  auth = getAuth(app);
  // Connect synchronously, before any listener or sign-in request, including HMR.
  if (emulatorUrl && !auth.emulatorConfig) {
    connectAuthEmulator(auth, emulatorUrl);
  }
} catch (error) {
  auth = null;
  authConfigurationError = error.message || 'Firebase could not be initialized. Check the web app configuration.';
}

export {auth, authConfigurationError};
