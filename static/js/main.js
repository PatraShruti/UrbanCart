// ── API helper ────────────────────────────────────────────────────────────────
async function api(path, opts = {}) {
  const { method = 'GET', body } = opts;
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Something went wrong');
  return data;
}

// ── Toast notification ────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.style.cssText = `
      position:fixed;bottom:28px;right:24px;
      padding:13px 22px;border-radius:12px;
      font-family:'Roboto',sans-serif;font-weight:bold;font-size:0.92em;
      display:none;z-index:9999;
      box-shadow:0 6px 24px rgba(0,0,0,0.4);max-width:320px;
      animation:toastIn .3s ease;
    `;
    const style = document.createElement('style');
    style.textContent = '@keyframes toastIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}';
    document.head.appendChild(style);
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.background = type === 'error' ? '#ef4444' : type === 'info' ? '#0ea5a4' : '#facc15';
  t.style.color      = type === 'error' || type === 'info' ? 'white' : '#000';
  t.style.display    = 'block';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.style.display = 'none', 3200);
}

// ── Cart badge ────────────────────────────────────────────────────────────────
async function refreshCartBadge() {
  try {
    const cart  = await api('/api/cart');
    const count = cart.reduce((s, i) => s + (i.qty || 1), 0);
    document.querySelectorAll('.cart-count-badge').forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? 'inline' : 'none';
    });
    return count;
  } catch { return 0; }
}

// ── Add to cart (shared across pages) ────────────────────────────────────────
async function addToCart(productId, btnEl) {
  if (btnEl) { btnEl.disabled = true; btnEl.innerHTML = '...'; }
  try {
    const res = await api('/api/cart/add', { method: 'POST', body: { product_id: productId } });
    showToast(res.message, 'success');
    refreshCartBadge();
    if (btnEl) {
      btnEl.textContent = 'Go to Cart ✓';
      btnEl.style.background = '#8b5cf6';
      btnEl.style.color = 'white';
      const orig = btnEl.onclick;
      btnEl.onclick = () => window.location.href = '/cart';
      btnEl.disabled = false;
      setTimeout(() => {
        btnEl.textContent = 'Add to Cart';
        btnEl.style.background = '';
        btnEl.style.color = '';
        btnEl.onclick = orig;
      }, 2500);
    }
  } catch (e) {
    showToast(e.message, 'error');
    if (e.message.includes('login')) setTimeout(() => window.location.href = '/login', 1500);
    if (btnEl) { btnEl.textContent = 'Add to Cart'; btnEl.disabled = false; }
  }
}

// ── Wishlist toggle ───────────────────────────────────────────────────────────
async function toggleWishlist(productId, btnEl) {
  try {
    const res = await api('/api/wishlist/toggle', { method: 'POST', body: { product_id: productId } });
    showToast(res.message, res.added ? 'success' : 'info');
    if (btnEl) {
      btnEl.textContent = res.added ? '❤️' : '🤍';
      btnEl.classList.toggle('wishlisted', res.added);
    }
  } catch (e) {
    showToast(e.message, 'error');
    if (e.message.includes('login')) setTimeout(() => window.location.href = '/login', 1500);
  }
}

// ── Nav: show Hi username + logout if logged in ───────────────────────────────
async function renderNavUser() {
  try {
    const me  = await api('/api/me');
    const nav = document.querySelector('nav');
    if (!nav) return;
    // remove existing login link if present
    nav.querySelectorAll('a[href="/login"], .nav-user-slot').forEach(el => el.remove());
    if (me.logged_in) {
      nav.innerHTML += `
        <span class="nav-user-slot" style="color:#facc15;font-weight:bold;">Hi, ${me.username}</span>
        <a href="/wishlist" class="nav-user-slot">Wishlist</a>
        <a href="/orders"   class="nav-user-slot">Orders</a>
        <a href="/profile"  class="nav-user-slot">Profile</a>
        <a href="/logout"   class="nav-user-slot">Logout</a>`;
    } else {
      nav.innerHTML += `<a href="/login" class="nav-user-slot">Login</a>`;
    }
  } catch {}
}

// ── Init on every page ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  refreshCartBadge();
  renderNavUser();
  document.querySelectorAll('.year').forEach(el => el.textContent = new Date().getFullYear());

  // Global search (if search bar exists on page)
  const si = document.getElementById('global-search');
  if (si) {
    si.addEventListener('keydown', e => {
      if (e.key === 'Enter' && si.value.trim())
        window.location.href = `/search?q=${encodeURIComponent(si.value.trim())}`;
    });
  }
});
