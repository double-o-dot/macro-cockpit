// ============================================================
// Slow Bear - Supabase Data Layer
// Wraps auth + CRUD for holdings, watchlist, transactions, settings
// ============================================================
import { supabase, isLoggedIn, getCurrentUser, signIn, signUp, signInWithGoogle, signOut, onAuthStateChange } from './supabase-client.js';

// Re-export auth helpers
export { supabase, isLoggedIn, getCurrentUser, signIn, signUp, signInWithGoogle, signOut, onAuthStateChange };

// ============================================================
// Auth State Manager
// ============================================================
const AUTH = { loggedIn: false, user: null, userId: null, email: null };

export function getAuth() { return AUTH; }

export async function initAuth() {
  try {
    const user = await getCurrentUser();
    if (user) {
      AUTH.loggedIn = true;
      AUTH.user = user;
      AUTH.userId = user.id;
      AUTH.email = user.email;
    }
  } catch (e) { /* not logged in */ }

  onAuthStateChange((event, session) => {
    if (session?.user) {
      AUTH.loggedIn = true;
      AUTH.user = session.user;
      AUTH.userId = session.user.id;
      AUTH.email = session.user.email;
    } else {
      AUTH.loggedIn = false;
      AUTH.user = null;
      AUTH.userId = null;
      AUTH.email = null;
    }
    window.dispatchEvent(new CustomEvent('sb-auth-change', { detail: AUTH }));
  });

  return AUTH;
}

export async function doSignOut() {
  await signOut();
  AUTH.loggedIn = false;
  AUTH.user = null;
  AUTH.userId = null;
  AUTH.email = null;
  window.dispatchEvent(new CustomEvent('sb-auth-change', { detail: AUTH }));
}

// ============================================================
// Holdings CRUD (portfolio)
// ============================================================
export async function loadHoldings() {
  if (!AUTH.userId) return loadLocal('sb_portfolio') || [];
  try {
    const { data, error } = await supabase
      .from('holdings')
      .select('*')
      .eq('user_id', AUTH.userId);
    if (!error && data && data.length > 0) return data;
  } catch (e) { console.warn('Supabase loadHoldings failed:', e); }
  return loadLocal('sb_portfolio') || [];
}

export async function saveHoldings(holdings) {
  // Always save localStorage backup
  saveLocal('sb_portfolio', holdings);

  if (!AUTH.userId) return;
  try {
    const rows = holdings.map(h => ({
      user_id: AUTH.userId,
      ticker: h.ticker,
      name: h.name || h.ticker,
      quantity: h.shares || h.quantity,
      avg_price: h.avgPrice || h.avg_price,
      currency: h.currency || 'USD',
    }));
    await supabase.from('holdings').delete().eq('user_id', AUTH.userId);
    if (rows.length > 0) {
      await supabase.from('holdings').insert(rows);
    }
  } catch (e) { console.warn('Supabase saveHoldings failed:', e); }
}

export async function addHolding(holding) {
  const holdings = await loadHoldings();
  // Normalize
  const item = {
    ticker: holding.ticker,
    name: holding.name || holding.ticker,
    quantity: holding.shares || holding.quantity,
    avg_price: holding.avgPrice || holding.avg_price,
    currency: holding.currency || 'USD',
  };
  // Check duplicate
  const idx = holdings.findIndex(h => h.ticker === item.ticker);
  if (idx >= 0) {
    holdings[idx].quantity = Number(holdings[idx].quantity) + Number(item.quantity);
    holdings[idx].avg_price = item.avg_price;
  } else {
    holdings.push(item);
  }
  await saveHoldings(holdings);

  // Also record transaction
  await addTransaction({
    ticker: item.ticker,
    name: item.name,
    type: 'BUY',
    shares: item.quantity,
    price: item.avg_price,
    total: item.quantity * item.avg_price,
    currency: item.currency,
  });

  return holdings;
}

export async function removeHolding(ticker) {
  let holdings = await loadHoldings();
  const removed = holdings.find(h => h.ticker === ticker);
  holdings = holdings.filter(h => h.ticker !== ticker);
  await saveHoldings(holdings);

  if (removed) {
    await addTransaction({
      ticker: removed.ticker,
      name: removed.name || removed.ticker,
      type: 'SELL',
      shares: removed.quantity,
      price: removed.avg_price,
      total: removed.quantity * removed.avg_price,
      currency: removed.currency || 'USD',
    });
  }
  return holdings;
}

// ============================================================
// Watchlist CRUD
// ============================================================
export async function loadWatchlist() {
  if (!AUTH.userId) return loadLocal('sb_watchlist') || [];
  try {
    const { data, error } = await supabase
      .from('watchlist')
      .select('*')
      .eq('user_id', AUTH.userId);
    if (!error && data) return data.map(d => d.ticker);
  } catch (e) { console.warn('Supabase loadWatchlist failed:', e); }
  return loadLocal('sb_watchlist') || [];
}

export async function saveWatchlist(tickers) {
  saveLocal('sb_watchlist', tickers);
  if (!AUTH.userId) return;
  try {
    await supabase.from('watchlist').delete().eq('user_id', AUTH.userId);
    if (tickers.length > 0) {
      const rows = tickers.map(t => ({ user_id: AUTH.userId, ticker: t }));
      await supabase.from('watchlist').insert(rows);
    }
  } catch (e) { console.warn('Supabase saveWatchlist failed:', e); }
}

export async function addToWatchlist(ticker) {
  const list = await loadWatchlist();
  if (!list.includes(ticker)) {
    list.push(ticker);
    await saveWatchlist(list);
  }
  return list;
}

export async function removeFromWatchlist(ticker) {
  let list = await loadWatchlist();
  list = list.filter(t => t !== ticker);
  await saveWatchlist(list);
  return list;
}

// ============================================================
// Transactions CRUD
// ============================================================
export async function loadTransactions() {
  if (!AUTH.userId) return loadLocal('sb_transactions') || [];
  try {
    const { data, error } = await supabase
      .from('transactions')
      .select('*')
      .eq('user_id', AUTH.userId)
      .order('created_at', { ascending: false });
    if (!error && data) return data;
  } catch (e) { console.warn('Supabase loadTransactions failed:', e); }
  return loadLocal('sb_transactions') || [];
}

export async function addTransaction(tx) {
  const txs = loadLocal('sb_transactions') || [];
  const record = {
    ticker: tx.ticker,
    name: tx.name || tx.ticker,
    type: tx.type || 'BUY',
    shares: tx.shares,
    price: tx.price,
    total: tx.total || (tx.shares * tx.price),
    currency: tx.currency || 'USD',
    status: 'Completed',
    date: new Date().toISOString(),
  };
  txs.unshift(record);
  saveLocal('sb_transactions', txs);

  if (!AUTH.userId) return;
  try {
    await supabase.from('transactions').insert({
      user_id: AUTH.userId,
      ...record,
    });
  } catch (e) { console.warn('Supabase addTransaction failed:', e); }
}

// ============================================================
// User Settings CRUD
// ============================================================
export async function loadSettings() {
  if (!AUTH.userId) return loadLocal('sb_settings') || defaultSettings();
  try {
    const { data, error } = await supabase
      .from('user_settings')
      .select('*')
      .eq('user_id', AUTH.userId)
      .single();
    if (!error && data) return data;
  } catch (e) { console.warn('Supabase loadSettings failed:', e); }
  return loadLocal('sb_settings') || defaultSettings();
}

export async function saveSettings(settings) {
  saveLocal('sb_settings', settings);
  if (!AUTH.userId) return;
  try {
    await supabase.from('user_settings').upsert({
      user_id: AUTH.userId,
      name: settings.name || 'Investor',
      email: settings.email || '',
      currency: settings.currency || 'USD',
      language: settings.language || 'en',
      alerts: !!settings.alerts,
      portfolio_updates: !!settings.portfolio_updates,
      market_news: !!settings.market_news,
    }, { onConflict: 'user_id' });
  } catch (e) { console.warn('Supabase saveSettings failed:', e); }
}

function defaultSettings() {
  return { name: 'Investor', email: '', currency: 'USD', language: 'en', alerts: false, portfolio_updates: false, market_news: false };
}

// ============================================================
// LocalStorage helpers
// ============================================================
function saveLocal(key, data) {
  try { localStorage.setItem(key, JSON.stringify(data)); } catch (e) {}
}

function loadLocal(key) {
  try { return JSON.parse(localStorage.getItem(key)); } catch (e) { return null; }
}

// ============================================================
// Clear all data
// ============================================================
export async function clearAllData() {
  localStorage.removeItem('sb_portfolio');
  localStorage.removeItem('sb_watchlist');
  localStorage.removeItem('sb_transactions');
  localStorage.removeItem('sb_settings');
  if (!AUTH.userId) return;
  try {
    await Promise.all([
      supabase.from('holdings').delete().eq('user_id', AUTH.userId),
      supabase.from('watchlist').delete().eq('user_id', AUTH.userId),
      supabase.from('transactions').delete().eq('user_id', AUTH.userId),
      supabase.from('user_settings').delete().eq('user_id', AUTH.userId),
    ]);
  } catch (e) { console.warn('Supabase clearAllData failed:', e); }
}
