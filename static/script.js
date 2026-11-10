// ==================== سبد خرید ====================
async function updateCartCount() {
    try {
        const res = await fetch("/api/cart");
        const data = await res.json();
        const el = document.getElementById("cartCount");
        if (el) el.textContent = data.count || 0;
    } catch (err) { console.error(err); }
}

async function addToCart(pid) {
    try {
        const res = await fetch(`/api/cart/add/${pid}`, { method: "POST" });
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("text/html")) {
            showToast("برای خرید ابتدا وارد شوید", true);
            setTimeout(() => window.location.href = "/register", 1200);
            return;
        }
        const data = await res.json();
        if (data.success) {
            const el = document.getElementById("cartCount");
            if (el) el.textContent = data.count;
            showToast("✓ به سبد خرید اضافه شد");
        }
    } catch (err) { console.error(err); }
}

function showToast(msg, isError = false) {
    const t = document.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.style.background = isError ? "#ef4444" : "#10b981";
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2500);
}

async function renderCartPage() {
    const res = await fetch("/api/cart");
    const data = await res.json();
    const container = document.getElementById("cartItems");
    const footer = document.getElementById("cartFooter");
    if (!container) return;
    if (!data.items || data.items.length === 0) {
        container.innerHTML = `<div class="empty">سبد خرید شما خالی است 🛒</div>`;
        if (footer) footer.style.display = "none";
        return;
    }
    container.innerHTML = data.items.map(item => `
        <div class="cart-item">
            <img src="${item.image}" style="object-fit:cover;">
            <div>
                <div class="name">${item.name}</div>
                <div class="item-price">${item.subtotal.toLocaleString()} تومان</div>
            </div>
            <div class="qty-controls">
                <button onclick="changeQty(${item.id}, ${item.qty + 1})">+</button>
                <span>${item.qty}</span>
                <button onclick="changeQty(${item.id}, ${item.qty - 1})">-</button>
            </div>
            <button class="remove-btn" onclick="removeItem(${item.id})">🗑️</button>
        </div>
    `).join("");
    if (document.getElementById("cartTotal")) document.getElementById("cartTotal").textContent = data.total.toLocaleString();
    if (footer) footer.style.display = "block";
}

async function changeQty(pid, qty) {
    await fetch(`/api/cart/update/${pid}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ qty: qty })
    });
    renderCartPage();
    updateCartCount();
}

async function removeItem(pid) {
    await fetch(`/api/cart/remove/${pid}`, { method: "POST" });
    renderCartPage();
    updateCartCount();
    showToast("محصول حذف شد");
}

// ==================== علاقه‌مندی‌ها (Wishlist) ====================
async function toggleWishlist(pid, btn) {
    try {
        const res = await fetch(`/api/wishlist/toggle/${pid}`, { method: "POST" });
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("text/html")) {
            showToast("برای افزودن به علاقه‌مندی‌ها ابتدا ثبت‌نام کنید", true);
            setTimeout(() => window.location.href = "/register", 1200);
            return;
        }
        const data = await res.json();
        if (data.success) {
            if (data.action === "added") {
                btn.classList.add("active");
                showToast("❤️ به علاقه‌مندی‌ها اضافه شد");
            } else {
                btn.classList.remove("active");
                showToast("از علاقه‌مندی‌ها حذف شد");
            }
        }
    } catch (err) { console.error(err); }
}

// ==================== مقایسه محصولات ====================
function addToCompare(pid) {
    let compare = JSON.parse(localStorage.getItem('compare') || '[]');
    if (!compare.includes(pid)) {
        if (compare.length >= 2) compare.shift();
        compare.push(pid);
        localStorage.setItem('compare', JSON.stringify(compare));
        showToast("✓ محصول برای مقایسه اضافه شد (" + compare.length + "/2)");
        if (compare.length === 2) {
            setTimeout(() => {
                window.location.href = "/compare?ids=" + compare.join(",");
            }, 1000);
        }
    } else {
        showToast("این محصول قبلاً به مقایسه اضافه شده");
    }
}

// ==================== جستجوی زنده ====================
document.addEventListener("DOMContentLoaded", () => {
    updateCartCount();
    if (document.getElementById("cartItems")) renderCartPage();

    const searchInput = document.querySelector(".search-box input");
    if (searchInput) {
        const resultsBox = document.createElement("div");
        resultsBox.className = "live-search-results";
        searchInput.parentElement.appendChild(resultsBox);

        let timer;
        searchInput.addEventListener("input", (e) => {
            clearTimeout(timer);
            const query = e.target.value.trim();
            if (query.length < 2) {
                resultsBox.style.display = "none";
                return;
            }
            timer = setTimeout(async () => {
                try {
                    const res = await fetch(`/?q=${encodeURIComponent(query)}`);
                    const html = await res.text();
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, "text/html");
                    const products = doc.querySelectorAll(".product-card");
                    
                    if (products.length === 0) {
                        resultsBox.innerHTML = '<div style="padding:15px;text-align:center;color:#9ca3af;">محصولی یافت نشد</div>';
                    } else {
                        let itemsHtml = "";
                        products.forEach((p, index) => {
                            if (index >= 6) return;
                            const link = p.querySelector("h3 a");
                            const img = p.querySelector("img");
                            const price = p.querySelector(".price");
                            if (link) {
                                itemsHtml += `
                                    <a href="${link.getAttribute('href')}" class="live-search-item">
                                        <img src="${img ? img.src : ''}">
                                        <div class="ls-info">
                                            <span class="ls-name">${link.textContent}</span>
                                            <span class="ls-price">${price ? price.textContent : ''}</span>
                                        </div>
                                    </a>
                                `;
                            }
                        });
                        resultsBox.innerHTML = itemsHtml;
                    }
                    resultsBox.style.display = "block";
                } catch (err) { console.error(err); }
            }, 300);
        });

        document.addEventListener("click", (e) => {
            if (!searchInput.parentElement.contains(e.target)) {
                resultsBox.style.display = "none";
            }
        });
    }
});