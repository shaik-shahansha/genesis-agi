# Firebase Authentication Setup

This web playground uses Firebase Authentication for user management with support for:
- Google Sign-In
- Email/Password authentication

## Configuration

### Environment Variables

All Firebase configuration is stored in `.env.local` (not committed to git). Make sure to set up your Firebase project and add these variables:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_auth_domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_storage_bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=your_measurement_id
```

See `.env.local.example` for a template.

## Firebase Console Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `genesis-agi-ed357`
3. Navigate to **Authentication** → **Sign-in method**
4. Enable the following providers:
   - **Google** - For one-click Google sign-in
   - **Email/Password** - For traditional email/password authentication

## How It Works

### Authentication Flow

1. **User visits `/login`** - Shows login page with Google and Email/Password options
2. **User signs in** - Firebase handles authentication
3. **Auth state changes** - `AuthContext` detects the signed-in user
4. **Email stored** - User's email from Firebase is automatically stored in `localStorage`
5. **Redirect to dashboard** - User is redirected to main application

### Email Handling

The email is automatically captured from the Firebase user object:
- For Google Sign-In: Email from Google account
- For Email/Password: Email provided during sign-up

The email is stored in:
- `localStorage.getItem('genesis_user_email')` - For use across the application
- `localStorage.getItem('genesis_firebase_token')` - Firebase ID token

### Files Overview

- **`lib/firebase.ts`** - Firebase initialization and configuration
- **`lib/auth-context.tsx`** - Authentication context provider with hooks
- **`app/login/page.tsx`** - Login page with Google and Email/Password forms
- **`app/layout.tsx`** - Root layout wrapped with `AuthProvider`

## Usage in Components

```typescript
import { useAuth } from '@/lib/auth-context';

function MyComponent() {
  const { user, loading, signOut } = useAuth();
  
  if (loading) return <div>Loading...</div>;
  
  if (!user) {
    // User not logged in
    return <div>Please log in</div>;
  }
  
  return (
    <div>
      <p>Welcome, {user.email}!</p>
      <button onClick={signOut}>Sign Out</button>
    </div>
  );
}
```

## Security Notes

- Never commit `.env.local` to version control
- Firebase API keys are safe to expose in frontend code (they're restricted by Firebase security rules)
- Always configure Firebase security rules properly in the Firebase Console
- The ID token is refreshed automatically by Firebase

## Development

To run the playground:

```bash
cd web-playground
npm install
npm run dev
```

Visit `http://localhost:3000/login` to test authentication.
