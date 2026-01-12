/**
 * Firebase Authentication Context
 * Manages authentication state across the application
 */

'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  User,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
} from 'firebase/auth';
import { auth } from './firebase';
import { api } from './api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  genesisUser?: any | null;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [genesisUser, setGenesisUser] = useState<any | null>(null);

  useEffect(() => {
    // Listen to auth state changes
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      
      if (firebaseUser) {
        // Get Firebase ID token
        const idToken = await firebaseUser.getIdToken();
        
        // Store token for Genesis API
        localStorage.setItem('genesis_firebase_token', idToken);
        localStorage.setItem('genesis_user_email', firebaseUser.email || '');
        // Backwards compatibility for other components
        localStorage.setItem('user_email', firebaseUser.email || '');
        // Fetch Genesis user details (role, etc.)
        try {
          const res = await api.getCurrentUser();
          setGenesisUser(res);
        } catch (e) {
          // ignore
        }
        
        // Optional: You can exchange the Firebase token with your backend
        // to get a Genesis-specific JWT token
        try {
          // Uncomment and implement this endpoint in your backend if needed
          // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/firebase`, {
          //   method: 'POST',
          //   headers: { 'Content-Type': 'application/json' },
          //   body: JSON.stringify({ firebaseToken: idToken }),
          // });
          // const data = await response.json();
          // api.setToken(data.access_token);
        } catch (error) {
          console.error('Error exchanging Firebase token:', error);
        }
      } else {
        // Clear stored tokens
        localStorage.removeItem('genesis_firebase_token');
        localStorage.removeItem('genesis_user_email');
        localStorage.removeItem('user_email');
        api.clearToken();
      }
      
      setLoading(false);
    });

    // Cleanup subscription
    return () => unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
      // Auth state change handler will manage the rest
    } catch (error: any) {
      console.error('Error signing in with Google:', error);
      throw new Error(error.message || 'Failed to sign in with Google');
    }
  };

  const signInWithEmail = async (email: string, password: string) => {
    try {
      await signInWithEmailAndPassword(auth, email, password);
      // Auth state change handler will manage the rest
    } catch (error: any) {
      console.error('Error signing in with email:', error);
      throw new Error(error.message || 'Failed to sign in');
    }
  };

  const signUpWithEmail = async (email: string, password: string) => {
    try {
      await createUserWithEmailAndPassword(auth, email, password);
      // Auth state change handler will manage the rest
    } catch (error: any) {
      console.error('Error signing up:', error);
      throw new Error(error.message || 'Failed to create account');
    }
  };

  const signOut = async () => {
    try {
      await firebaseSignOut(auth);
    } catch (error: any) {
      console.error('Error signing out:', error);
      throw new Error(error.message || 'Failed to sign out');
    }
  };

  const value = {
    user,
    loading,
    genesisUser,
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
