// ============================================================
// Supabase Client - ES Module
// ============================================================
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';

const SUPABASE_URL = 'https://ytgbjsdffvfcguehtquv.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_5ZNTcYAvUbZONm7dDTkwPg_IHMUI8A-';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

/**
 * Check if a user is currently logged in
 * @returns {Promise<boolean>}
 */
export async function isLoggedIn() {
  const { data: { session } } = await supabase.auth.getSession();
  return !!session;
}

/**
 * Get the current authenticated user
 * @returns {Promise<object|null>}
 */
export async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

/**
 * Sign in with email and password
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{user: object|null, error: object|null}>}
 */
export async function signIn(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  return { user: data?.user || null, error };
}

/**
 * Sign up with email and password
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{user: object|null, error: object|null}>}
 */
export async function signUp(email, password) {
  const { data, error } = await supabase.auth.signUp({ email, password });
  return { user: data?.user || null, error };
}

/**
 * Sign in with Google OAuth
 * @returns {Promise<{data: object|null, error: object|null}>}
 */
export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin + window.location.pathname
    }
  });
  return { data, error };
}

/**
 * Sign out the current user
 * @returns {Promise<{error: object|null}>}
 */
export async function signOut() {
  const { error } = await supabase.auth.signOut();
  return { error };
}

/**
 * Listen for auth state changes
 * @param {function} callback - (event, session) => void
 * @returns {object} subscription
 */
export function onAuthStateChange(callback) {
  const { data: { subscription } } = supabase.auth.onAuthStateChange(callback);
  return subscription;
}
