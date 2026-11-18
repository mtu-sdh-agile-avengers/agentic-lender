
import { signInWithEmailAndPassword, signOut, onAuthStateChanged, sendPasswordResetEmail } from 'firebase/auth';
import { auth, authConfigurationError } from './firebase.js';

function requireAuth() {
    if (!auth) throw new Error(authConfigurationError);
    return auth;
}

export function observeSession(onChange, onError) {
    return onAuthStateChanged(requireAuth(), onChange, onError);
}

export function logoutUser() {
    return signOut(requireAuth());
}

export function resetPassword(email) {
    return sendPasswordResetEmail(requireAuth(), email.trim());
}

// forceRefresh=true fetches a new token, e.g. after AL-Core changed the user's role claim
export async function getCurrentIdToken(forceRefresh = false) {
    const user = requireAuth().currentUser;
    if (!user) throw Object.assign(new Error('Sign-in required'), {code:'auth/no-current-user'});
    return user.getIdToken(forceRefresh);
}

export async function signIn(email, password) {
    const result = await signInWithEmailAndPassword(
        requireAuth(),
        email.trim(),
        password
    );

    const token = await result.user.getIdToken();

    return {
        user: result.user,
        token
    };
}
