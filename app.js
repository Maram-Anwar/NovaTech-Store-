const BACKEND_ORIGIN = "https://maram10.pythonanywhere.com";

const API = `${BACKEND_ORIGIN}/api`;
const STORAGE = {
  token: "nova_token",
  role: "nova_role",
  name: "nova_name",
  email: "nova_email",
};

const state = {
  token: localStorage.getItem(STORAGE.token) || "",
  role: localStorage.getItem(STORAGE.role) || "",
  name: localStorage.getItem(STORAGE.name) || "",
  email: localStorage.getItem(STORAGE.email) || "",
  products: [],
  allProducts: [],
  categories: [],
  adminUsers: [],
  quickProductId: null,
  featuredIndex: 0,
  cart: null,
  profile: null,
  pendingEmail: "",
};

const $ = (id) => document.getElementById(id);
const money = (n) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(n || 0));
const escapeHtml = (s) => String(s ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));

let backendReady = false;

function showBackendStatus(mode, title, text) {
  const box = $("backendStatus");
  if (!box) return;
  box.classList.remove("checking", "online", "offline");
  box.classList.add(mode);
  $("backendStatusTitle").textContent = title;
  $("backendStatusText").textContent = text;
}

async function checkBackend({ redirectFile = false } = {}) {
  showBackendStatus("checking", "Checking backend...", "Connecting to Nova data storage.");
  try {
    const response = await fetch(`${BACKEND_ORIGIN}/api/health?_=${Date.now()}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || data.status !== "success" || data.storage_ready === false) {
      throw new Error(data.message || "JSON storage is not ready");
    }
    if (String(data.version || "") !== "6.0") {
      throw new Error(`Wrong backend version (${data.version || "unknown"}). Close old Nova server windows and launch START_NOVA_STORE.bat from this folder.`);
    }
    backendReady = true;
    showBackendStatus(
      "online",
      "Secure connection established",
      "Nova Tech Store is ready."
    );
    if (redirectFile && location.protocol === "file:") {
      location.replace(`${BACKEND_ORIGIN}/`);
      return false;
    }
    return true;
  } catch (error) {
    backendReady = false;
    const directFile = location.protocol === "file:";
    showBackendStatus(
      "offline",
      "Backend not running",
      directFile
        ? "Do not open index.html directly. Double-click START_NOVA_STORE.bat, then use the browser window it opens."
        : "Start START_NOVA_STORE.bat and keep the server window open, then press Retry."
    );
    return false;
  }
}

function toast(message, type = "success") {
  const el = $("toast");
  el.textContent = message || "Done";
  el.className = `toast ${type}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.add("hidden"), 3800);
}

function setBusy(button, busy) {
  if (!button) return;
  button.classList.toggle("loading", busy);
  button.disabled = busy;
}

async function withBusy(button, task) {
  setBusy(button, true);
  try {
    return await task();
  } finally {
    setBusy(button, false);
  }
}

function clearSession() {
  state.token = state.role = state.name = state.email = "";
  Object.values(STORAGE).forEach((key) => localStorage.removeItem(key));
}

function goToAuth(tab = "login") {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  $("authView").classList.add("active");
  showAuthTab(tab);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;

  let response;
  try {
    response = await fetch(API + path, { ...options, headers });
  } catch (error) {
    console.error("Nova API network error:", error);
    backendReady = false;
    showBackendStatus("offline", "Backend disconnected", "Run START_NOVA_STORE.bat and keep its window open, then press Retry.");
    throw new Error("Nova backend is not running. Open the store using START_NOVA_STORE.bat, not index.html.");
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = { status: "error", message: "Invalid server response" };
  }

  if (response.status === 401 && state.token && !path.startsWith("/auth/")) {
    clearSession();
    updateShell();
    goToAuth("login");
    toast("Your session expired. Please login again.", "error");
  }

  if (!response.ok) throw new Error(data.message || `HTTP ${response.status}`);
  return data;
}

function saveSession(result) {
  const account = result.user || result.admin || {};
  state.token = result.token || "";
  state.role = result.role || "";
  state.name = account.user_name || "Account";
  state.email = account.email || "";
  localStorage.setItem(STORAGE.token, state.token);
  localStorage.setItem(STORAGE.role, state.role);
  localStorage.setItem(STORAGE.name, state.name);
  localStorage.setItem(STORAGE.email, state.email);
}

function updateShell() {
  const loggedIn = Boolean(state.token && state.role);
  $("mainNav").classList.toggle("hidden", !loggedIn);
  $("accountArea").classList.toggle("hidden", !loggedIn);
  $("storeTicker").classList.toggle("hidden", !loggedIn);
  document.querySelectorAll(".user-only").forEach((el) => el.classList.toggle("hidden", state.role !== "user"));
  document.querySelectorAll(".admin-only").forEach((el) => el.classList.toggle("hidden", state.role !== "admin"));
  $("accountName").textContent = state.name || "Account";
  $("accountRole").textContent = state.role || "";
}

function showView(name) {
  if (!state.token && name !== "auth") return goToAuth("login");
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelectorAll(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === name));
  const view = $(`${name}View`);
  if (!view) return;
  view.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (name === "products") loadProducts();
  if (name === "cart" && state.role === "user") loadCart();
  if (name === "profile" && state.role === "user") loadProfile();
  if (name === "admin" && state.role === "admin") loadAdmin();
}

function showAuthTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.authTab === name));
  document.querySelectorAll("[data-auth-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.authPanel === name));
}

function maskEmail(email) {
  const [name = "", domain = ""] = String(email).split("@");
  if (!domain) return email;
  const visible = name.slice(0, Math.min(2, name.length));
  return `${visible}${"•".repeat(Math.max(3, name.length - visible.length))}@${domain}`;
}

function assetUrl(path) {
  if (!path) return `${BACKEND_ORIGIN}/images/products/product-placeholder.svg`;
  const value = String(path);
  if (/^https?:\/\//i.test(value) || value.startsWith("data:")) return value;
  return `${BACKEND_ORIGIN}/${value.replace(/^\/+/, "")}`;
}

function productImage(product) {
  const images = Array.isArray(product.images) ? product.images : [];
  const main = images.find((img) => img.is_main) || images[0];
  return assetUrl(main?.url || main?.path || "images/products/product-placeholder.svg");
}

function productFallbackImage(product) {
  const images = Array.isArray(product?.images) ? product.images : [];
  const fallback = images.find((img) => img.path && !img.is_main) || images.find((img) => img.path);
  return assetUrl(fallback?.path || "images/products/product-placeholder.svg");
}

function armProductImage(img, product) {
  if (!img) return;
  img.classList.add("product-photo-loading");
  const done = () => img.classList.remove("product-photo-loading");
  const fallback = productFallbackImage(product);
  const useFallback = () => {
    if (img.src !== fallback) img.src = fallback;
    done();
  };
  if (img.complete) {
    if (img.naturalWidth) done();
    else useFallback();
    return;
  }
  img.addEventListener("load", done, { once: true });
  img.addEventListener("error", useFallback, { once: true });
}

// Navigation

document.querySelectorAll("[data-auth-tab]").forEach((button) => button.addEventListener("click", () => showAuthTab(button.dataset.authTab)));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
  if (!state.token) return;
  showView(button.dataset.view);
}));

// Authentication

$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  await withBusy(button, async () => {
    try {
      const result = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: $("loginEmail").value.trim(), password: $("loginPassword").value }),
      });
      saveSession(result);
      updateShell();
      toast(result.message);
      showView("products");
      await refreshUserHeader();
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("adminLoginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  await withBusy(button, async () => {
    try {
      const result = await request("/auth/admin-login", {
        method: "POST",
        body: JSON.stringify({ email: $("adminEmail").value.trim(), password: $("adminPassword").value }),
      });
      saveSession(result);
      updateShell();
      toast(result.message);
      showView("admin");
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  const payload = {
    user_name: $("registerUsername").value.trim(),
    email: $("registerEmail").value.trim(),
    password: $("registerPassword").value,
  };

  await withBusy(button, async () => {
    try {
      const result = await request("/auth/register", { method: "POST", body: JSON.stringify(payload) });
      state.pendingEmail = payload.email.toLowerCase();
      $("otpHint").textContent = result.delivery === "server_console"
        ? "Gmail is not configured. Copy the 6-digit code shown in the Nova Python server window. It expires in 10 minutes."
        : `A 6-digit code was sent to ${maskEmail(state.pendingEmail)}. It expires in 10 minutes.`;
      $("otpCode").value = "";
      showAuthTab("otp");
      $("otpCode").focus();
      toast(result.message);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("otpForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  if (!state.pendingEmail) {
    toast("Registration session not found. Please enter your details again.", "error");
    return showAuthTab("register");
  }

  await withBusy(button, async () => {
    try {
      const result = await request("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email: state.pendingEmail, otp: $("otpCode").value.trim() }),
      });
      saveSession(result);
      state.pendingEmail = "";
      updateShell();
      toast(result.message);
      showView("products");
      await refreshUserHeader();
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("resendOtpBtn").addEventListener("click", async (event) => {
  if (!state.pendingEmail) {
    toast("Enter your registration details first.", "error");
    return showAuthTab("register");
  }
  await withBusy(event.currentTarget, async () => {
    try {
      const result = await request("/auth/resend-otp", { method: "POST", body: JSON.stringify({ email: state.pendingEmail }) });
      $("otpCode").value = "";
      toast(result.message);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("backToRegisterBtn").addEventListener("click", () => showAuthTab("register"));

$("logoutBtn").addEventListener("click", async () => {
  try {
    await request("/auth/logout", { method: "POST", body: "{}" });
  } catch {
    // Local state is still cleared if the server cannot respond.
  }
  clearSession();
  updateShell();
  goToAuth("login");
  toast("Logged out successfully");
});

// Products

async function refreshUserHeader() {
  if (state.role !== "user") return;
  try {
    const [wallet, cart] = await Promise.all([request("/wallet"), request("/cart")]);
    $("headerBalance").textContent = money(wallet.balance);
    $("walletPill").classList.remove("hidden");
    $("cartBadge").textContent = (cart.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  } catch {
    // Request handles auth expiry.
  }
}

function productSearchText(product) {
  return [product.name, product.category, product.brand, product.description, product.badge]
    .map((value) => String(value || "").toLowerCase()).join(" ");
}

function renderCategoryControls() {
  const categories = state.categories;
  const select = $("categoryFilter");
  const current = select.value;
  select.innerHTML = '<option value="">All categories</option>' + categories
    .map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
  select.value = categories.includes(current) ? current : "";

  const active = select.value;
  const counts = Object.fromEntries(categories.map((category) => [category, state.allProducts.filter((p) => p.category === category).length]));
  $("categoryChips").innerHTML = [
    `<button class="category-chip ${active === "" ? "active" : ""}" data-category-chip=""><span>All</span><b>${state.allProducts.length}</b></button>`,
    ...categories.map((category) => `<button class="category-chip ${active === category ? "active" : ""}" data-category-chip="${escapeHtml(category)}"><span>${escapeHtml(category)}</span><b>${counts[category] || 0}</b></button>`),
  ].join("");

  $("categoryChips").querySelectorAll("[data-category-chip]").forEach((button) => button.addEventListener("click", () => {
    $("categoryFilter").value = button.dataset.categoryChip;
    applyCatalogFilters();
  }));
}

function pickFeaturedProducts() {
  return [...state.allProducts]
    .filter((p) => Number(p.quantity || 0) > 0)
    .sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0) || Number(b.quantity || 0) - Number(a.quantity || 0))
    .slice(0, 8);
}

function renderFeatured() {
  const featured = pickFeaturedProducts();
  if (!featured.length) return;
  state.featuredIndex = state.featuredIndex % featured.length;
  const product = featured[state.featuredIndex];
  $("featuredBadge").textContent = String(product.badge || "FEATURED").toUpperCase();
  $("featuredName").textContent = product.name || "Nova product";
  $("featuredDescription").textContent = product.description || "Explore this Nova Tech Store pick.";
  $("featuredPrice").textContent = money(product.price);
  $("featuredImage").src = productImage(product);
  $("featuredImage").alt = product.name || "Featured product";
  armProductImage($("featuredImage"), product);
  $("featuredViewBtn").dataset.quickView = product.id;
  $("featuredSpotlight").classList.remove("spotlight-swap");
  requestAnimationFrame(() => $("featuredSpotlight").classList.add("spotlight-swap"));
}

function applyCatalogFilters() {
  const q = $("productSearch").value.trim().toLowerCase();
  const category = $("categoryFilter").value;
  const inStock = $("inStockOnly").checked;
  const sort = $("sortProducts").value;

  let products = state.allProducts.filter((product) => {
    if (q && !productSearchText(product).includes(q)) return false;
    if (category && product.category !== category) return false;
    if (inStock && Number(product.quantity || 0) <= 0) return false;
    return true;
  });

  const sorters = {
    "price-asc": (a, b) => Number(a.price) - Number(b.price),
    "price-desc": (a, b) => Number(b.price) - Number(a.price),
    "rating-desc": (a, b) => Number(b.rating || 0) - Number(a.rating || 0),
    "stock-desc": (a, b) => Number(b.quantity || 0) - Number(a.quantity || 0),
    "name-asc": (a, b) => String(a.name).localeCompare(String(b.name)),
    featured: (a, b) => Number(b.rating || 0) - Number(a.rating || 0) || Number(b.quantity || 0) - Number(a.quantity || 0),
  };
  products.sort(sorters[sort] || sorters.featured);
  state.products = products;
  renderCategoryControls();
  renderProducts();
}

function renderCatalogMetrics() {
  $("catalogCount").textContent = state.products.length;
  $("categoryCount").textContent = state.categories.length;
  $("stockCount").textContent = state.allProducts.reduce((sum, p) => sum + Number(p.quantity || 0), 0);
  $("resultsLabel").textContent = `Showing ${state.products.length} of ${state.allProducts.length} products`;
}

function renderProducts() {
  const grid = $("productsGrid");
  const empty = $("productsEmpty");
  renderCatalogMetrics();

  if (!state.products.length) {
    grid.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }

  empty.classList.add("hidden");
  grid.innerHTML = state.products.map((product, index) => {
    const stock = Number(product.quantity || 0);
    const rating = Number(product.rating || 0);
    const canAdd = state.role === "user" && stock > 0;
    const meter = Math.max(4, Math.min(100, stock * 6));
    return `
      <article class="product-card card" style="animation-delay:${Math.min(index * 35, 260)}ms">
        <div class="product-image" data-quick-view="${product.id}">
          <span class="product-chip">${escapeHtml(product.category || "Tech")}</span>
          <span class="product-badge">${escapeHtml(product.badge || "Nova")}</span>
          <img src="${escapeHtml(productImage(product))}" alt="${escapeHtml(product.name || "Product")}" loading="lazy" decoding="async" data-product-photo="${product.id}">
          <button class="quick-view-btn" data-quick-view="${product.id}" type="button">Quick view ↗</button>
        </div>
        <div class="product-body">
          <div class="product-meta"><span>${escapeHtml(product.brand || "Nova")}</span><span class="rating-star">★ ${rating.toFixed(1)}</span></div>
          <h3>${escapeHtml(product.name)}</h3>
          <p class="product-description">${escapeHtml(product.description || "Nova Tech Store product")}</p>
          <div class="card-stock"><span><i style="width:${meter}%"></i></span><small>${stock ? `${stock} available` : "Sold out"}</small></div>
          <div class="product-bottom">
            <div><div class="price">${money(product.price)}</div><span class="stock ${stock ? "" : "out"}">${stock ? "Ready to ship" : "Out of stock"}</span></div>
            ${state.role === "user" ? `<button class="btn btn-primary" data-add-cart="${product.id}" ${canAdd ? "" : "disabled"}>${stock ? "Add to cart" : "Unavailable"}</button>` : `<button class="btn btn-ghost" data-quick-view="${product.id}">Details</button>`}
          </div>
        </div>
      </article>`;
  }).join("");

  grid.querySelectorAll("[data-product-photo]").forEach((img) => {
    const product = state.allProducts.find((item) => Number(item.id) === Number(img.dataset.productPhoto));
    armProductImage(img, product);
  });

  grid.querySelectorAll("[data-add-cart]").forEach((button) => button.addEventListener("click", (event) => {
    event.stopPropagation();
    addToCart(Number(button.dataset.addCart), button, 1);
  }));
  grid.querySelectorAll("[data-quick-view]").forEach((element) => element.addEventListener("click", (event) => {
    event.stopPropagation();
    openQuickView(Number(element.dataset.quickView));
  }));
}

async function loadProducts() {
  $("productsGrid").classList.add("catalog-loading");
  try {
    const data = await request("/products");
    state.allProducts = data.products || [];
    state.categories = [...new Set(state.allProducts.map((p) => String(p.category || "").trim()).filter(Boolean))].sort();
    renderFeatured();
    applyCatalogFilters();
    await refreshUserHeader();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    $("productsGrid").classList.remove("catalog-loading");
  }
}

async function addToCart(productId, button, quantity = 1) {
  await withBusy(button, async () => {
    try {
      const data = await request("/cart", { method: "POST", body: JSON.stringify({ product_id: productId, quantity }) });
      toast(data.message);
      await refreshUserHeader();
    } catch (error) {
      toast(error.message, "error");
    }
  });
}

function openQuickView(productId) {
  const product = state.allProducts.find((item) => Number(item.id) === Number(productId));
  if (!product) return;
  state.quickProductId = product.id;
  const stock = Number(product.quantity || 0);
  const rating = Number(product.rating || 0);
  $("quickImage").src = productImage(product);
  $("quickImage").alt = product.name || "Product";
  armProductImage($("quickImage"), product);
  $("quickBadge").textContent = String(product.badge || "Nova").toUpperCase();
  $("quickCategory").textContent = product.category || "Technology";
  $("quickName").textContent = product.name || "Product";
  $("quickRating").textContent = rating.toFixed(1);
  $("quickStars").textContent = "★★★★★";
  $("quickBrand").textContent = product.brand || "Nova";
  $("quickDescription").textContent = product.description || "Nova Tech Store product.";
  $("quickStock").textContent = stock ? `${stock} units available` : "Out of stock";
  $("quickStockMeter").style.width = `${Math.max(stock ? 5 : 0, Math.min(100, stock * 6))}%`;
  $("quickPrice").textContent = money(product.price);
  $("quickQuantity").value = 1;
  $("quickQuantity").max = Math.max(1, stock);
  $("quickAddBtn").disabled = !stock || state.role !== "user";
  $("quickAddBtn").textContent = stock ? "Add to cart" : "Currently unavailable";
  $("quickViewModal").classList.remove("hidden");
}

function closeQuickView() {
  $("quickViewModal").classList.add("hidden");
  state.quickProductId = null;
}

$("featuredViewBtn").addEventListener("click", () => openQuickView(Number($("featuredViewBtn").dataset.quickView)));
$("productSearch").addEventListener("input", debounce(applyCatalogFilters, 140));
$("categoryFilter").addEventListener("change", applyCatalogFilters);
$("sortProducts").addEventListener("change", applyCatalogFilters);
$("inStockOnly").addEventListener("change", applyCatalogFilters);
$("refreshProductsBtn").addEventListener("click", (event) => withBusy(event.currentTarget, loadProducts));
document.querySelectorAll("[data-close-quick]").forEach((el) => el.addEventListener("click", closeQuickView));
$("quickMinus").addEventListener("click", () => $("quickQuantity").value = Math.max(1, Number($("quickQuantity").value || 1) - 1));
$("quickPlus").addEventListener("click", () => {
  const max = Number($("quickQuantity").max || 99);
  $("quickQuantity").value = Math.min(max, Number($("quickQuantity").value || 1) + 1);
});
$("quickAddBtn").addEventListener("click", async (event) => {
  if (!state.quickProductId) return;
  const quantity = Math.max(1, Number($("quickQuantity").value || 1));
  await addToCart(state.quickProductId, event.currentTarget, quantity);
  closeQuickView();
});

setInterval(() => {
  if (!$("productsView").classList.contains("active") || !state.allProducts.length) return;
  const featured = pickFeaturedProducts();
  if (featured.length < 2) return;
  state.featuredIndex = (state.featuredIndex + 1) % featured.length;
  renderFeatured();
}, 7000);

// Cart

function renderCart() {
  const cart = state.cart || { items: [], total: 0 };
  const items = cart.items || [];
  const wrap = $("cartItems");
  $("summaryCount").textContent = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  $("cartTotal").textContent = money(cart.total);

  if (!items.length) {
    wrap.innerHTML = '<div class="empty-state"><div class="empty-icon">＋</div><h3>Your cart is empty</h3><p>Add products from the store to continue.</p></div>';
  } else {
    wrap.innerHTML = items.map((item) => `
      <article class="cart-item card">
        <div class="cart-thumb"><img src="${escapeHtml(assetUrl(item.main_image_url || "images/products/product-placeholder.svg"))}" alt="${escapeHtml(item.name || "Product")}"></div>
        <div class="cart-copy"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.category)} · ${money(item.price)} each · ${money(item.subtotal)} subtotal</p></div>
        <div class="cart-actions">
          <input class="qty" data-cart-qty="${item.product_id}" type="number" min="1" value="${item.quantity}" aria-label="Quantity for ${escapeHtml(item.name)}">
          <button class="btn btn-ghost btn-sm danger-text" data-remove-cart="${item.product_id}">Remove</button>
        </div>
      </article>`).join("");
  }

  wrap.querySelectorAll("[data-cart-qty]").forEach((input) => input.addEventListener("change", () => updateCartQty(Number(input.dataset.cartQty), Number(input.value))));
  wrap.querySelectorAll("[data-remove-cart]").forEach((button) => button.addEventListener("click", () => removeCartItem(Number(button.dataset.removeCart), button)));
  $("checkoutBtn").disabled = items.length === 0;
  $("clearCartBtn").disabled = items.length === 0;
}

async function loadCart() {
  try {
    const [cart, wallet] = await Promise.all([request("/cart"), request("/wallet")]);
    state.cart = cart;
    $("cartBalance").textContent = money(wallet.balance);
    $("headerBalance").textContent = money(wallet.balance);
    renderCart();
    $("cartBadge").textContent = (cart.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  } catch (error) {
    toast(error.message, "error");
  }
}

async function updateCartQty(productId, quantity) {
  try {
    const data = await request(`/cart/${productId}`, { method: "PATCH", body: JSON.stringify({ quantity }) });
    toast(data.message);
    await loadCart();
  } catch (error) {
    toast(error.message, "error");
    await loadCart();
  }
}

async function removeCartItem(productId, button) {
  await withBusy(button, async () => {
    try {
      const data = await request(`/cart/${productId}`, { method: "DELETE", body: "{}" });
      toast(data.message);
      await loadCart();
    } catch (error) {
      toast(error.message, "error");
    }
  });
}

$("clearCartBtn").addEventListener("click", async (event) => {
  if (!confirm("Clear your entire cart?")) return;
  await withBusy(event.currentTarget, async () => {
    try {
      const data = await request("/cart", { method: "DELETE", body: "{}" });
      toast(data.message);
      await loadCart();
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("checkoutBtn").addEventListener("click", async (event) => {
  if (!confirm("Complete checkout and deduct the order total from your wallet?")) return;
  await withBusy(event.currentTarget, async () => {
    try {
      const data = await request("/checkout", { method: "POST", body: "{}" });
      toast(`${data.message} · ${money(data.total)}`);
      await Promise.all([loadCart(), loadProducts()]);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

// Profile

async function loadProfile() {
  try {
    const profile = await request("/me");
    state.profile = profile;
    const name = profile["Account Name"] || state.name;
    $("profileName").textContent = name;
    $("profileEmail").textContent = profile.Email || state.email;
    $("profileBalance").textContent = money(profile.Balance);
    $("profileAvatar").textContent = (name || "N")[0].toUpperCase();
  } catch (error) {
    toast(error.message, "error");
  }
}

$("usernameForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await withBusy(event.submitter, async () => {
    try {
      const data = await request("/profile/username", { method: "PATCH", body: JSON.stringify({ new_name: $("newUsername").value.trim() }) });
      state.name = data.user_name;
      localStorage.setItem(STORAGE.name, state.name);
      $("accountName").textContent = state.name;
      $("newUsername").value = "";
      toast(data.message);
      await loadProfile();
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("passwordForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await withBusy(event.submitter, async () => {
    try {
      const data = await request("/profile/password", {
        method: "PATCH",
        body: JSON.stringify({ old_password: $("oldPassword").value, new_password: $("newPassword").value }),
      });
      event.target.reset();
      toast(data.message);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("deleteAccountForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!confirm("Delete your Nova Tech Store account permanently?")) return;
  await withBusy(event.submitter, async () => {
    try {
      const data = await request("/profile", { method: "DELETE", body: JSON.stringify({ password: $("deletePassword").value }) });
      clearSession();
      updateShell();
      goToAuth("login");
      toast(data.message);
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

// Admin

function renderStats(stats = {}) {
  const items = [
    ["Products", stats.total_products ?? 0],
    ["Categories", stats.categories ?? state.categories.length ?? 0],
    ["Units in stock", stats.total_items ?? 0],
    ["Inventory value", money(stats.inventory_value)],
    ["Customers", stats.total_users ?? 0],
    ["Avg. rating", `★ ${Number(stats.average_rating || 0).toFixed(1)}`],
  ];
  $("statsGrid").innerHTML = items.map(([label, value]) => `<div class="stat-card"><span>${label}</span><strong>${value}</strong></div>`).join("");
}

function renderAdminInsights() {
  const products = state.allProducts;
  const low = products.filter((p) => Number(p.quantity || 0) <= 5).sort((a, b) => Number(a.quantity) - Number(b.quantity)).slice(0, 5);
  const categoryCounts = {};
  products.forEach((p) => categoryCounts[p.category] = (categoryCounts[p.category] || 0) + 1);
  const topCategories = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  $("adminInsights").innerHTML = `
    <article class="card insight-card"><div><p class="eyebrow">LOW STOCK WATCH</p><h3>${low.length ? `${low.length} products need attention` : "Inventory healthy"}</h3></div><div class="insight-tags">${low.map((p) => `<span>${escapeHtml(p.name)} · ${p.quantity}</span>`).join("") || "<span>No low-stock products</span>"}</div></article>
    <article class="card insight-card"><div><p class="eyebrow">CATEGORY MIX</p><h3>${Object.keys(categoryCounts).length} active categories</h3></div><div class="insight-tags">${topCategories.map(([name, count]) => `<span>${escapeHtml(name)} · ${count}</span>`).join("")}</div></article>`;
}

function renderAdminProducts(products = state.allProducts) {
  const q = $("adminProductSearch").value.trim().toLowerCase();
  const filtered = q ? products.filter((p) => productSearchText(p).includes(q)) : products;
  $("adminProductsBody").innerHTML = filtered.map((product) => `
    <tr>
      <td>#${product.id}</td>
      <td><div class="admin-product-cell"><img class="admin-thumb" src="${escapeHtml(productImage(product))}" alt="${escapeHtml(product.name)}" loading="lazy" decoding="async" data-admin-photo="${product.id}"><div><strong>${escapeHtml(product.name)}</strong><small>${escapeHtml(product.brand || "Nova")}</small></div></div></td>
      <td>${escapeHtml(product.category)}</td><td>${money(product.price)}</td><td>★ ${Number(product.rating || 0).toFixed(1)}</td><td>${product.quantity}</td>
      <td><div class="table-actions"><button class="btn btn-ghost btn-sm" data-edit-product="${product.id}">Edit</button><button class="btn btn-ghost btn-sm danger-text" data-delete-product="${product.id}">Delete</button></div></td>
    </tr>`).join("") || '<tr><td colspan="7">No matching products.</td></tr>';

  $("adminProductsBody").querySelectorAll("[data-admin-photo]").forEach((img) => {
    const product = state.allProducts.find((item) => Number(item.id) === Number(img.dataset.adminPhoto));
    armProductImage(img, product);
  });
  $("adminProductsBody").querySelectorAll("[data-edit-product]").forEach((button) => button.addEventListener("click", () => openEditProduct(Number(button.dataset.editProduct))));
  $("adminProductsBody").querySelectorAll("[data-delete-product]").forEach((button) => button.addEventListener("click", () => deleteProduct(Number(button.dataset.deleteProduct), button)));
}

function renderAdminUsers(users = state.adminUsers) {
  const q = $("adminUserSearch").value.trim().toLowerCase();
  const filtered = q ? users.filter((u) => `${u.user_name} ${u.email}`.toLowerCase().includes(q)) : users;
  $("adminUsersBody").innerHTML = filtered.map((user) => `<tr><td><strong>${escapeHtml(user.user_name)}</strong></td><td>${escapeHtml(user.email)}</td><td>${money(user.balance)}</td><td><button class="btn btn-ghost btn-sm" data-charge-user="${escapeHtml(user.user_name)}">Add balance</button></td></tr>`).join("") || '<tr><td colspan="4">No matching users.</td></tr>';
  $("adminUsersBody").querySelectorAll("[data-charge-user]").forEach((button) => button.addEventListener("click", () => {
    $("balanceUsername").value = button.dataset.chargeUser;
    $("balanceAmount").focus();
    $("balanceAmount").scrollIntoView({ behavior: "smooth", block: "center" });
  }));
}

async function loadAdmin() {
  try {
    const [stats, products, users] = await Promise.all([request("/admin/stats"), request("/products"), request("/admin/users")]);
    state.allProducts = products.products || [];
    state.products = state.allProducts;
    state.categories = [...new Set(state.allProducts.map((p) => p.category).filter(Boolean))].sort();
    state.adminUsers = users.users || [];
    renderStats(stats.statistics);
    renderAdminInsights();
    renderAdminProducts();
    renderAdminUsers();
  } catch (error) {
    toast(error.message, "error");
  }
}

function fileToImage(file) {
  return new Promise((resolve, reject) => {
    if (!file) return resolve(null);
    if (file.size > 8 * 1024 * 1024) return reject(new Error("Image must be 8 MB or smaller"));
    const reader = new FileReader();
    reader.onload = () => resolve({ name: file.name, data_url: reader.result });
    reader.onerror = () => reject(new Error("Could not read image"));
    reader.readAsDataURL(file);
  });
}

$("addProductForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await withBusy(event.submitter, async () => {
    try {
      const image = await fileToImage($("addImage").files[0]);
      const payload = {
        name: $("addName").value.trim(), category: $("addCategory").value.trim(), brand: $("addBrand").value.trim(),
        badge: $("addBadge").value.trim(), description: $("addDescription").value.trim(), rating: Number($("addRating").value || 4.5),
        price: Number($("addPrice").value), quantity: Number($("addQuantity").value), image,
      };
      const data = await request("/admin/products", { method: "POST", body: JSON.stringify(payload) });
      event.target.reset();
      $("addBrand").value = "Nova"; $("addBadge").value = "New"; $("addRating").value = "4.5";
      toast(data.message);
      await loadAdmin();
    } catch (error) { toast(error.message, "error"); }
  });
});

$("addBalanceForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await withBusy(event.submitter, async () => {
    try {
      const data = await request("/admin/wallet/add", { method: "POST", body: JSON.stringify({ user_name: $("balanceUsername").value.trim(), amount: Number($("balanceAmount").value) }) });
      event.target.reset();
      toast(`${data.message} · New balance ${money(data.balance)}`);
      await loadAdmin();
    } catch (error) { toast(error.message, "error"); }
  });
});

$("adminRefreshBtn").addEventListener("click", (event) => withBusy(event.currentTarget, loadAdmin));
$("adminProductSearch").addEventListener("input", debounce(() => renderAdminProducts(), 120));
$("adminUserSearch").addEventListener("input", debounce(() => renderAdminUsers(), 120));

function openEditProduct(id) {
  const product = state.allProducts.find((item) => item.id === id);
  if (!product) return;
  $("editProductId").value = product.id;
  $("editName").value = product.name;
  $("editCategory").value = product.category;
  $("editBrand").value = product.brand || "Nova";
  $("editBadge").value = product.badge || "";
  $("editPrice").value = product.price;
  $("editQuantity").value = product.quantity;
  $("editRating").value = product.rating ?? 4.5;
  $("editDescription").value = product.description || "";
  $("editTitle").textContent = product.name;
  $("editImage").value = "";
  $("editModal").classList.remove("hidden");
}

function closeEdit() { $("editModal").classList.add("hidden"); }
document.querySelectorAll("[data-close-modal]").forEach((element) => element.addEventListener("click", closeEdit));
document.addEventListener("keydown", (event) => { if (event.key === "Escape") { closeEdit(); closeQuickView(); } });

$("editProductForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = Number($("editProductId").value);
  await withBusy(event.submitter, async () => {
    try {
      const payload = {
        name: $("editName").value.trim(), category: $("editCategory").value.trim(), brand: $("editBrand").value.trim(),
        badge: $("editBadge").value.trim(), description: $("editDescription").value.trim(), rating: Number($("editRating").value || 0),
        price: Number($("editPrice").value), quantity: Number($("editQuantity").value),
      };
      const data = await request(`/admin/products/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      const file = $("editImage").files[0];
      if (file) {
        const image = await fileToImage(file);
        await request(`/admin/products/${id}/main-image`, { method: "POST", body: JSON.stringify({ image }) });
      }
      closeEdit(); toast(data.message); await loadAdmin();
    } catch (error) { toast(error.message, "error"); }
  });
});

async function deleteProduct(id, button) {
  if (!confirm(`Delete product #${id}?`)) return;
  await withBusy(button, async () => {
    try { const data = await request(`/admin/products/${id}`, { method: "DELETE", body: "{}" }); toast(data.message); await loadAdmin(); }
    catch (error) { toast(error.message, "error"); }
  });
}

function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

$("retryBackendBtn")?.addEventListener("click", async (event) => {
  await withBusy(event.currentTarget, async () => {
    const ok = await checkBackend({ redirectFile: true });
    if (ok) toast("Backend connected to Nova data successfully");
  });
});

async function boot() {
  ["store_token", "store_role", "store_name", "store_email"].forEach((key) => localStorage.removeItem(key));
  updateShell();
  const connected = await checkBackend({ redirectFile: true });
  if (!connected) {
    goToAuth("login");
    return;
  }
  if (!state.token || !state.role) {
    goToAuth("login");
    return;
  }

  if (state.role === "admin") {
    showView("admin");
  } else if (state.role === "user") {
    showView("products");
    await refreshUserHeader();
  } else {
    clearSession();
    updateShell();
    goToAuth("login");
  }
}

boot();
