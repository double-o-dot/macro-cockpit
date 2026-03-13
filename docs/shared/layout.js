// ============================================================
// Layout Shell - Initializes nav, auth, and page structure
// ============================================================
import { supabase, isLoggedIn, getCurrentUser, signIn, signUp, signOut, onAuthStateChange } from './supabase-client.js';
import { initNav, updateNavAuth } from './nav.js';

// Global auth state
const AUTH = {
  loggedIn: false,
  email: null,
  user: null
};

/**
 * Initialize the layout: nav, auth listeners
 */
export async function initLayout() {
  // Check current auth state
  try {
    const user = await getCurrentUser();
    if (user) {
      AUTH.loggedIn = true;
      AUTH.email = user.email;
      AUTH.user = user;
    }
  } catch (e) {
    // Not logged in or error
  }

  // Render navigation
  initNav({ loggedIn: AUTH.loggedIn, email: AUTH.email });

  // Setup global auth handlers for nav buttons
  window.__navSignOut = async () => {
    await signOut();
    AUTH.loggedIn = false;
    AUTH.email = null;
    AUTH.user = null;
    updateNavAuth({ loggedIn: false, email: null });
    // Notify page
    window.dispatchEvent(new CustomEvent('auth-change', { detail: AUTH }));
  };

  window.__navGoLogin = () => {
    // If on a page with auth form, show it; otherwise redirect to portfolio
    const authForm = document.getElementById('auth-section');
    if (authForm) {
      authForm.scrollIntoView({ behavior: 'smooth' });
    } else {
      window.location.href = 'portfolio.html';
    }
  };

  // Listen for auth state changes from Supabase
  onAuthStateChange((event, session) => {
    if (session?.user) {
      AUTH.loggedIn = true;
      AUTH.email = session.user.email;
      AUTH.user = session.user;
    } else {
      AUTH.loggedIn = false;
      AUTH.email = null;
      AUTH.user = null;
    }
    updateNavAuth({ loggedIn: AUTH.loggedIn, email: AUTH.email });
    window.dispatchEvent(new CustomEvent('auth-change', { detail: AUTH }));
  });

  return AUTH;
}

/**
 * Get current auth state synchronously
 */
export function getAuth() {
  return AUTH;
}

/**
 * Handle sign-in from an auth form
 */
export async function handleSignIn(email, password) {
  const { user, error } = await signIn(email, password);
  if (error) return { error };
  AUTH.loggedIn = true;
  AUTH.email = user?.email;
  AUTH.user = user;
  updateNavAuth({ loggedIn: true, email: AUTH.email });
  window.dispatchEvent(new CustomEvent('auth-change', { detail: AUTH }));
  return { user };
}

/**
 * Handle sign-up from an auth form
 */
export async function handleSignUp(email, password) {
  const { user, error } = await signUp(email, password);
  if (error) return { error };
  return { user, message: '가입 완료! 이메일을 확인해주세요.' };
}

/**
 * Render auth form (for protected pages)
 * Returns an HTML string
 */
export function renderAuthForm() {
  return `
    <div id="auth-section">
      <div class="auth-card" x-data="authForm()">
        <div class="logo-circle" style="width:48px;height:48px;border-radius:50%;background:#D97757;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;">
          <span style="color:#fff;font-size:20px;font-weight:700;">M</span>
        </div>
        <h2 x-text="isSignUp ? '회원가입' : '로그인'"></h2>
        <p x-text="isSignUp ? '새 계정을 만들어주세요' : '계정에 로그인하세요'"></p>
        <div class="auth-error" x-text="errorMsg"></div>
        <div x-show="successMsg" style="font-size:12px;color:#34C759;margin-bottom:12px;" x-text="successMsg"></div>
        <form @submit.prevent="submit()">
          <input class="auth-input" type="email" placeholder="이메일" x-model="email" required>
          <input class="auth-input" type="password" placeholder="비밀번호 (6자 이상)" x-model="password" required minlength="6">
          <button class="auth-btn" type="submit" :disabled="loading">
            <span x-show="!loading" x-text="isSignUp ? '가입하기' : '로그인'"></span>
            <span x-show="loading">처리 중...</span>
          </button>
        </form>
        <div class="auth-toggle">
          <span x-show="!isSignUp">계정이 없으신가요? <a @click="isSignUp=true; errorMsg=''; successMsg=''">회원가입</a></span>
          <span x-show="isSignUp">이미 계정이 있으신가요? <a @click="isSignUp=false; errorMsg=''; successMsg=''">로그인</a></span>
        </div>
      </div>
    </div>`;
}

// Export for use in pages
export { signIn, signUp, signOut, isLoggedIn, getCurrentUser };
