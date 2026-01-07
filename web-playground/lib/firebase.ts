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

// Initialize Firebase (only once)
let app: FirebaseApp;
let auth: Auth;
let analytics: Analytics | null = null;

if (getApps().length === 0) {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
  
  // Initialize analytics only in browser environment
  if (typeof window !== 'undefined') {
    analytics = getAnalytics(app);
  }
} else {
  app = getApps()[0];
  auth = getAuth(app);
}

export { app, auth, analytics };

/**
 * Get the current Firebase ID token for API authentication
 * @returns Promise<string | null> - The ID token or null if not authenticated
 */
export async function getFirebaseToken(): Promise<string | null> {
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
