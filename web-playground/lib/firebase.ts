/**
 * Firebase Configuration and Initialization
 */

import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';
import { getAnalytics, Analytics } from 'firebase/analytics';

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

/**
 * True when enough Firebase config is present to initialise the SDK.
 * Requires at least an API key and a project id.
 */
export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId
);

// Initialize Firebase (only once), and ONLY when it is actually configured.
//
// Firebase is optional: a self-hosted deployment can use the built-in JWT /
// API-key authentication instead. Initialising the SDK with an empty API key
// throws `auth/invalid-api-key`, and because Next.js prerenders pages at build
// time that error would fail the entire production build. So configuration is
// checked first and initialisation is wrapped defensively.
let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let analytics: Analytics | null = null;

if (isFirebaseConfigured) {
  try {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
    auth = getAuth(app);

    // Analytics is browser-only.
    if (typeof window !== 'undefined') {
      analytics = getAnalytics(app);
    }
  } catch (error) {
    // Optional auth must never break the build or the app shell.
    console.error('[firebase] initialisation failed; Firebase auth disabled:', error);
    app = null;
    auth = null;
    analytics = null;
  }
} else if (typeof window !== 'undefined') {
  console.info(
    '[firebase] NEXT_PUBLIC_FIREBASE_* not configured - Firebase auth is disabled. ' +
      'The app will use the built-in JWT / API-key authentication instead.'
  );
}

export { app, auth, analytics };

/**
 * Get the current Firebase ID token for API authentication
 * @returns Promise<string | null> - The ID token, or null when Firebase is
 *          disabled or the user is not signed in.
 */
export async function getFirebaseToken(): Promise<string | null> {
  if (!auth) {
    return null;
  }
  try {
    const currentUser = auth.currentUser;
    if (!currentUser) {
      return null;
    }
    // Force refresh to ensure token is valid
    const token = await currentUser.getIdToken(true);
    return token;
  } catch (error) {
    console.error('Error getting Firebase token:', error);
    return null;
  }
}
