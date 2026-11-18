// VITE_FIREBASE_MODE ('emulator' | 'cloud') comes from Docker Compose (root .env FIREBASE_MODE).
// Without it, VITE_USE_EMULATORS=true|false decides, as before (.env.local for `npm run dev`).
export function readAuthConfig(env) {
  const mode = env.VITE_FIREBASE_MODE?.trim();
  const useEmulators = mode ? mode !== 'cloud' : env.VITE_USE_EMULATORS === 'true';
  if (useEmulators && !env.DEV) {
    throw new Error('Emulator authentication is disabled in production. Set VITE_USE_EMULATORS=false and configure the Firebase web app.');
  }
  // Emulators use a "demo-" project, the real Firebase project has its own ID
  const projectId = (useEmulators
    ? env.VITE_FIREBASE_EMULATOR_PROJECT_ID || env.VITE_FIREBASE_PROJECT_ID
    : env.VITE_FIREBASE_PROJECT_ID)?.trim();
  if (!projectId || projectId.startsWith('YOUR_')) {
    throw new Error('Firebase setup is incomplete. Configure VITE_FIREBASE_PROJECT_ID and restart the app.');
  }
  let emulatorUrl;
  if (useEmulators) {
    const url = new URL(env.VITE_AUTH_EMULATOR_URL || 'http://127.0.0.1:9099');
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
      throw new Error('VITE_AUTH_EMULATOR_URL must be an HTTP origin, such as http://127.0.0.1:9099.');
    }
    emulatorUrl = url.origin;
  }
  const config = {
    projectId,
    apiKey: env.VITE_FIREBASE_API_KEY?.trim(),
    authDomain: env.VITE_FIREBASE_AUTH_DOMAIN?.trim(),
    appId: env.VITE_FIREBASE_APP_ID?.trim(),
  };
  if (useEmulators) {
    // placeholders only: the real project's keys are never needed (or sent) in emulator mode
    config.apiKey = 'emulator-only-key';
    config.authDomain = `${projectId}.firebaseapp.com`;
    config.appId = 'emulator-only-app';
  } else if (projectId.startsWith('demo-') || Object.values(config).some(value => !value || value.startsWith('YOUR_'))) {
    throw new Error('Firebase cloud setup is incomplete. Configure the web app API key, auth domain, project ID, and app ID.');
  }
  return {config, emulatorUrl};
}
