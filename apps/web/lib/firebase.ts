import { initializeApp, getApps, type FirebaseApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider, type Auth } from 'firebase/auth'

export const isFirebaseConfigured = !!process.env.NEXT_PUBLIC_FIREBASE_API_KEY

let _auth: Auth | undefined
let _googleProvider: GoogleAuthProvider | undefined

if (isFirebaseConfigured) {
  const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  }
  const app: FirebaseApp = getApps().length ? getApps()[0] : initializeApp(firebaseConfig)
  _auth = getAuth(app)
  _googleProvider = new GoogleAuthProvider()
}

// Callers must check isFirebaseConfigured before using these
export const auth = _auth as Auth
export const googleProvider = _googleProvider as GoogleAuthProvider
