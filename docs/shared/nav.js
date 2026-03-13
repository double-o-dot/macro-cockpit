// ============================================================
// Common Navigation - Renders topnav (Desktop) + bottom nav (Mobile)
// ============================================================

const NAV_ITEMS = [
  {
    id: 'insights',
    label: '인사이트',
    href: 'index.html',
    icon: `<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`
  },
  {
    id: 'prices',
    label: '주식가격',
    href: 'prices.html',
    icon: `<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`
  },
  {
    id: 'portfolio',
    label: '포트폴리오',
    href: 'portfolio.html',
    icon: `<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/><path d="M9 12l2 2 4-4"/></svg>`
  },
  {
    id: 'macro',
    label: '매크로',
    href: 'macro.html',
    icon: `<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/></svg>`
  }
];

/**
 * Detect current page ID based on the URL filename
 */
function getCurrentPageId() {
  const path = window.location.pathname;
  const filename = path.split('/').pop() || 'index.html';
  if (filename === '' || filename === 'index.html') return 'insights';
  if (filename === 'prices.html') return 'prices';
  if (filename === 'portfolio.html') return 'portfolio';
  if (filename === 'macro.html') return 'macro';
  return 'insights';
}

/**
 * Render Desktop Top Navigation Bar
 */
function renderTopNav(authState) {
  const currentPage = getCurrentPageId();
  const nav = document.createElement('nav');
  nav.className = 'topnav';
  nav.id = 'topnav';

  // Logo
  const logoHTML = `
    <a href="index.html" class="topnav-logo">
      <div class="logo-circle"><span>M</span></div>
      <span class="logo-text">Macro Cockpit</span>
    </a>`;

  // Menu items
  const menuHTML = NAV_ITEMS.map(item => {
    const active = item.id === currentPage ? ' active' : '';
    return `<a href="${item.href}" class="${active}" data-nav="${item.id}">
      ${item.icon}
      ${item.label}
    </a>`;
  }).join('');

  // Auth button
  const authHTML = authState.loggedIn
    ? `<button class="btn-logout" onclick="window.__navSignOut()">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
        ${authState.email ? authState.email.split('@')[0] : '로그아웃'}
       </button>`
    : `<button class="btn-login" onclick="window.__navGoLogin()">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/></svg>
        로그인
       </button>`;

  nav.innerHTML = `
    ${logoHTML}
    <div class="topnav-menu">${menuHTML}</div>
    <div class="topnav-auth">${authHTML}</div>`;

  return nav;
}

/**
 * Render Mobile Bottom Navigation Bar
 */
function renderBottomNav() {
  const currentPage = getCurrentPageId();
  const nav = document.createElement('nav');
  nav.className = 'bnav';
  nav.id = 'bottom-nav';

  nav.innerHTML = NAV_ITEMS.map(item => {
    const active = item.id === currentPage ? ' active' : '';
    return `<a href="${item.href}" class="${active}" data-nav="${item.id}">
      ${item.icon}
      ${item.label}
      <div class="dot"></div>
    </a>`;
  }).join('');

  return nav;
}

/**
 * Initialize navigation - call from layout.js
 * @param {object} authState - { loggedIn: boolean, email: string|null }
 */
export function initNav(authState = { loggedIn: false, email: null }) {
  // Desktop top nav
  const topNav = renderTopNav(authState);
  document.body.prepend(topNav);

  // Mobile bottom nav
  const bottomNav = renderBottomNav();
  document.body.appendChild(bottomNav);
}

/**
 * Update auth state in nav (e.g., after login/logout)
 */
export function updateNavAuth(authState) {
  const oldTop = document.getElementById('topnav');
  if (oldTop) {
    const newTop = renderTopNav(authState);
    oldTop.replaceWith(newTop);
  }
}

export { getCurrentPageId, NAV_ITEMS };
