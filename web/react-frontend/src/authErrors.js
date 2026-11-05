export function authErrorMessage(error) {
  switch (error?.code) {
    case 'auth/invalid-credential':
    case 'auth/user-not-found':
    case 'auth/wrong-password': return 'The email or password is incorrect. Please try again.';
    case 'auth/invalid-email': return 'Enter a valid email address.';
    case 'auth/user-disabled': return 'This account is disabled. Contact your administrator.';
    case 'auth/too-many-requests': return 'Too many attempts. Please wait before trying again.';
    case 'auth/network-request-failed': return 'Unable to connect to sign-in. Check your connection and try again.';
    case 'auth/operation-not-allowed': return 'Email and password sign-in is not enabled. Contact your administrator.';
    case 'auth/invalid-api-key':
    case 'auth/app-not-authorized':
    case 'auth/unauthorized-domain': return 'Sign-in is not configured for this app. Contact your administrator.';
    case 'auth/user-token-expired':
    case 'auth/invalid-user-token':
    case 'auth/no-current-user': return 'Your session has expired. Please sign in again.';
    default: return 'The request could not be completed. Please try again.';
  }
}
