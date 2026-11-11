from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Category, Product, Order, OrderItem, Coupon, Wishlist, Review, Notification
import os
import random
import string
import requests
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = "pc-zone-secret-2024"

# ==================== اتصال به دیتابیس ابری Supabase ====================
# علامت @ با %40 جایگزین شده تا آدرس دیتابیس درست کار کنه
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:As13881202%40pc@db.gmakikihtqvlvmkeyxza.supabase.co:5432/postgres"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "برای ادامه باید وارد شوید."

@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))

# ==================== تنظیمات زرین‌پال ====================
MERCHANT_ID = "00000000-0000-0000-0000-000000000000"
SANDBOX = True
ZARINPAL_API = "https://sandbox.zarinpal.com/pg/v4/payment/" if SANDBOX else "https://api.zarinpal.com/pg/v4/payment/"
ZARINPAL_GATEWAY = "https://sandbox.zarinpal.com/pg/StartPay/" if SANDBOX else "https://www.zarinpal.com/pg/StartPay/"

# ==================== عکس‌های پیش‌فرض ====================
IMG_CPU = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='300' height='300' fill='%231a1a2e'/><rect x='75' y='75' width='150' height='150' fill='%237c3aed' rx='15'/><text x='150' y='165' font-size='30' fill='white' text-anchor='middle' font-family='Arial'>CPU</text></svg>"
IMG_GPU = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='300' height='300' fill='%231a1a2e'/><rect x='50' y='80' width='200' height='140' fill='%2310b981' rx='15'/><text x='150' y='165' font-size='30' fill='white' text-anchor='middle' font-family='Arial'>GPU</text></svg>"
IMG_RAM = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='300' height='300' fill='%231a1a2e'/><rect x='40' y='120' width='220' height='60' fill='%2322d3ee' rx='10'/><text x='150' y='160' font-size='30' fill='black' text-anchor='middle' font-family='Arial'>RAM</text></svg>"
IMG_SSD = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='300' height='300' fill='%231a1a2e'/><rect x='90' y='90' width='120' height='120' fill='%23fbbf24' rx='15'/><text x='150' y='165' font-size='30' fill='black' text-anchor='middle' font-family='Arial'>SSD</text></svg>"
IMG_CASE = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='300' height='300' fill='%231a1a2e'/><rect x='80' y='50' width='140' height='200' fill='%23a855f7' rx='15'/><text x='150' y='165' font-size='30' fill='white' text-anchor='middle' font-family='Arial'>CASE</text></svg>"

def init_database():
    db.create_all()
    if User.query.count() == 0:
        admin = User(username="admin", email="admin@pczone.ir", is_admin=True); admin.set_password("admin123"); db.session.add(admin)
        test_user = User(username="ali", email="ali@test.com", phone="09123456789", address="تهران، خیابان ولیعصر"); test_user.set_password("123456"); db.session.add(test_user)
        db.session.commit()
        cats = [("پردازنده", "cpu"), ("کارت گرافیک", "gpu"), ("رم", "ram"), ("حافظه", "storage"), ("مادربرد", "motherboard"), ("منبع تغذیه", "psu"), ("کیس", "case"), ("خنک‌کننده", "cooling"), ("مانیتور", "monitor"), ("لوازم جانبی", "accessories")]
        for name, slug in cats: db.session.add(Category(name=name, slug=slug))
        db.session.commit()
        db.session.add(Coupon(code="PCZONE10", discount_percent=10))
        cpu_cat = Category.query.filter_by(slug="cpu").first(); gpu_cat = Category.query.filter_by(slug="gpu").first(); ram_cat = Category.query.filter_by(slug="ram").first(); storage_cat = Category.query.filter_by(slug="storage").first(); case_cat = Category.query.filter_by(slug="case").first()
        products = [
            Product(name="پردازنده Intel Core i9-13900K", category_id=cpu_cat.id, price=28500000, old_price=31000000, image=IMG_CPU, description="پردازنده ۲۴ هسته‌ای اینتل نسل ۱۳", stock=5, rating=4.9),
            Product(name="پردازنده AMD Ryzen 9 7950X", category_id=cpu_cat.id, price=27000000, old_price=29000000, image=IMG_CPU, description="پردازنده ۱۶ هسته‌ای AMD Zen 4", stock=8, rating=4.8),
            Product(name="کارت گرافیک NVIDIA RTX 4090", category_id=gpu_cat.id, price=95000000, old_price=105000000, image=IMG_GPU, description="۲۴ گیگابایت GDDR6X", stock=3, rating=5.0),
            Product(name="کارت گرافیک RTX 4070 Ti", category_id=gpu_cat.id, price=48000000, old_price=52000000, image=IMG_GPU, description="۱۲ گیگابایت GDDR6X", stock=7, rating=4.7),
            Product(name="رم Corsair Vengeance 32GB DDR5", category_id=ram_cat.id, price=6200000, old_price=7000000, image=IMG_RAM, description="۳۲ گیگابایت DDR5 6000MHz RGB", stock=15, rating=4.6),
            Product(name="SSD Samsung 990 Pro 2TB", category_id=storage_cat.id, price=7800000, old_price=8500000, image=IMG_SSD, description="SSD NVMe Gen4", stock=20, rating=4.9),
            Product(name="کیس گیمینگ NZXT H7 Flow", category_id=case_cat.id, price=4900000, old_price=5500000, image=IMG_CASE, description="کیس میدتاور با جریان هوا عالی", stock=10, rating=4.8),
        ]
        for p in products: db.session.add(p)
        db.session.commit()

@app.route("/")
def index():
    category_slug = request.args.get("category", "all"); search = request.args.get("q", ""); sort = request.args.get("sort", "default")
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    in_stock = request.args.get("in_stock")
    
    q = Product.query
    if category_slug != "all":
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat: q = q.filter_by(category_id=cat.id)
    if search: q = q.filter(Product.name.contains(search))
    if min_price is not None: q = q.filter(Product.price >= min_price)
    if max_price is not None: q = q.filter(Product.price <= max_price)
    if in_stock == "1": q = q.filter(Product.stock > 0)

    if sort == "price_asc": q = q.order_by(Product.price.asc())
    elif sort == "price_desc": q = q.order_by(Product.price.desc())
    elif sort == "rating": q = q.order_by(Product.rating.desc())
    
    special_offers = Product.query.filter(Product.old_price != None, Product.old_price > Product.price).order_by((Product.old_price - Product.price).desc()).limit(4).all()
    
    return render_template("index.html", products=q.all(), categories=Category.query.all(), 
                           current_category=category_slug, search=search, sort=sort, 
                           special_offers=special_offers, min_price=min_price, 
                           max_price=max_price, in_stock=in_stock)

@app.route("/product/<int:pid>")
def product_detail(pid):
    p = Product.query.get_or_404(pid)
    related = Product.query.filter_by(category_id=p.category_id).filter(Product.id != p.id).limit(4).all()
    reviews = Review.query.filter_by(product_id=pid).order_by(Review.created_at.desc()).all()
    return render_template("product.html", product=p, related=related, reviews=reviews)

@app.route("/compare")
def compare_page():
    ids = request.args.get("ids", "")
    ids_list = [int(i) for i in ids.split(",") if i.isdigit()]
    products = Product.query.filter(Product.id.in_(ids_list)).all() if ids_list else []
    return render_template("compare.html", products=products)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("پیام شما با موفقیت ثبت شد. به زودی با شما تماس می‌گیریم.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip(); email = request.form.get("email", "").strip(); password = request.form.get("password", "")
        if not username or not email or len(password) < 6:
            flash("همه فیلدها را پر کنید (رمز حداقل ۶ کاراکتر)", "error"); return redirect(url_for("register"))
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("نام کاربری یا ایمیل قبلاً ثبت شده", "error"); return redirect(url_for("register"))
        u = User(username=username, email=email); u.set_password(password); db.session.add(u); db.session.commit(); login_user(u)
        flash("خوش آمدید!", "success"); return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip(); password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True); return redirect(url_for("index"))
        flash("نام کاربری یا رمز عبور اشتباه است", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("index"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.phone = request.form.get("phone", "").strip(); current_user.address = request.form.get("address", "").strip()
        db.session.commit(); flash("پروفایل بروزرسانی شد", "success"); return redirect(url_for("profile"))
    return render_template("profile.html")

@app.route("/api/cart")
def get_cart():
    cart = session.get("cart", {}); items = []; total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            items.append({"id": p.id, "name": p.name, "price": p.price, "image": p.image, "qty": qty, "subtotal": p.price * qty}); total += p.price * qty
    return jsonify({"items": items, "total": total, "count": sum(cart.values())})

@app.route("/api/cart/add/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    cart = session.get("cart", {}); cart[str(pid)] = cart.get(str(pid), 0) + 1; session["cart"] = cart
    return jsonify({"success": True, "count": sum(cart.values())})

@app.route("/api/cart/remove/<int:pid>", methods=["POST"])
def remove_from_cart(pid):
    cart = session.get("cart", {}); cart.pop(str(pid), None); session["cart"] = cart
    return jsonify({"success": True, "count": sum(cart.values())})

@app.route("/api/cart/update/<int:pid>", methods=["POST"])
def update_cart(pid):
    qty = int(request.json.get("qty", 1)); cart = session.get("cart", {})
    if qty <= 0: cart.pop(str(pid), None)
    else: cart[str(pid)] = qty
    session["cart"] = cart
    return jsonify({"success": True, "count": sum(cart.values())})

@app.route("/api/apply-coupon", methods=["POST"])
def apply_coupon():
    code = request.json.get("code", "").strip().upper(); coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    if coupon: return jsonify({"success": True, "discount": coupon.discount_percent})
    return jsonify({"success": False, "message": "کد تخفیف نامعتبر است"})

@app.route("/cart")
def cart_page(): return render_template("cart.html")

@app.route("/api/wishlist/toggle/<int:pid>", methods=["POST"])
@login_required
def toggle_wishlist(pid):
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=pid).first()
    if existing:
        db.session.delete(existing); db.session.commit()
        return jsonify({"success": True, "action": "removed"})
    else:
        new_item = Wishlist(user_id=current_user.id, product_id=pid); db.session.add(new_item); db.session.commit()
        return jsonify({"success": True, "action": "added"})

@app.route("/wishlist")
@login_required
def wishlist_page():
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    return render_template("wishlist.html", items=items)

@app.route("/api/review/add/<int:pid>", methods=["POST"])
@login_required
def add_review(pid):
    rating = int(request.json.get("rating", 5))
    comment = request.json.get("comment", "").strip()
    existing = Review.query.filter_by(user_id=current_user.id, product_id=pid).first()
    if existing:
        existing.rating = rating; existing.comment = comment; db.session.commit()
        return jsonify({"success": True, "message": "نظر شما بروزرسانی شد"})
    new_review = Review(user_id=current_user.id, product_id=pid, rating=rating, comment=comment)
    db.session.add(new_review); db.session.commit()
    return jsonify({"success": True, "message": "نظر شما ثبت شد"})

@app.route("/api/notifications")
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({
        "notifications": [{"id": n.id, "message": n.message, "link": n.link, "is_read": n.is_read, "date": n.created_at.strftime('%Y/%m/%d %H:%M')} for n in notifications],
        "unread_count": unread_count
    })

@app.route("/api/notifications/read/<int:nid>", methods=["POST"])
@login_required
def mark_notification_read(nid):
    n = Notification.query.get_or_404(nid)
    if n.user_id == current_user.id:
        n.is_read = True; db.session.commit()
    return jsonify({"success": True})

@app.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit(); return jsonify({"success": True})

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart: return redirect(url_for("cart_page"))
    if request.method == "POST":
        address = request.form.get("address", "").strip(); phone = request.form.get("phone", "").strip(); coupon_code = request.form.get("coupon_code", "").strip().upper()
        if not address or not phone:
            flash("آدرس و شماره تماس الزامی است", "error"); return redirect(url_for("checkout"))
        total = sum(Product.query.get(int(pid)).price * qty for pid, qty in cart.items() if Product.query.get(int(pid)))
        discount_amount = 0
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
            if coupon:
                discount_amount = int(total * coupon.discount_percent / 100); total -= discount_amount
        order = Order(user_id=current_user.id, total=total, address=address, phone=phone, status="pending", coupon_code=coupon_code if coupon_code else None, discount_amount=discount_amount)
        db.session.add(order); db.session.flush()
        for pid, qty in cart.items():
            p = Product.query.get(int(pid))
            if p:
                db.session.add(OrderItem(order_id=order.id, product_id=p.id, quantity=qty, price=p.price)); p.stock -= qty
        db.session.commit()
        callback_url = url_for("verify_payment", order_id=order.id, _external=True)
        payload = {"merchant_id": MERCHANT_ID, "amount": total, "callback_url": callback_url, "description": f"سفارش #{order.id}"}
        try:
            resp = requests.post(ZARINPAL_API + "request.json", json=payload, timeout=10)
            result = resp.json()
            if result.get("data", {}).get("code") == 100:
                authority = result["data"]["authority"]; order.payment_authority = authority; db.session.commit()
                return redirect(ZARINPAL_GATEWAY + authority)
            else:
                error_msg = result.get("errors", {}).get("message", "خطای نامشخص")
                flash(f"خطا در اتصال به درگاه: {error_msg}", "error"); return redirect(url_for("cart_page"))
        except Exception as e:
            flash(f"خطا در ارتباط با درگاه: {str(e)}", "error"); return redirect(url_for("cart_page"))
    return render_template("checkout.html")

@app.route("/verify/<int:order_id>")
@login_required
def verify_payment(order_id):
    order = Order.query.get_or_404(order_id)
    authority = request.args.get("Authority"); status = request.args.get("Status")
    if status != "OK":
        order.status = "cancelled"; db.session.commit(); flash("پرداخت لغو شد.", "error"); return redirect(url_for("cart_page"))
    payload = {"merchant_id": MERCHANT_ID, "amount": order.total, "authority": authority}
    try:
        resp = requests.post(ZARINPAL_API + "verify.json", json=payload, timeout=10)
        result = resp.json()
        if result.get("data", {}).get("code") == 100:
            order.status = "paid"; order.payment_ref = str(result["data"]["ref_id"]); db.session.commit(); session["cart"] = {}
            notif = Notification(user_id=current_user.id, message=f"سفارش #{order.id} با موفقیت پرداخت شد. مبلغ: {order.total:,} تومان", link=f"/my-orders")
            db.session.add(notif); db.session.commit()
            flash("پرداخت با موفقیت انجام شد!", "success"); return redirect(url_for("order_success", oid=order.id))
        elif result.get("data", {}).get("code") == 101:
            order.status = "paid"; db.session.commit(); session["cart"] = {}; return redirect(url_for("order_success", oid=order.id))
        else:
            order.status = "failed"; db.session.commit(); flash("تایید پرداخت ناموفق بود.", "error"); return redirect(url_for("cart_page"))
    except Exception as e:
        flash(f"خطا در تایید پرداخت: {str(e)}", "error"); return redirect(url_for("cart_page"))

@app.route("/order/success/<int:oid>")
@login_required
def order_success(oid):
    order = Order.query.get_or_404(oid)
    if order.user_id != current_user.id: return redirect(url_for("index"))
    return render_template("order_success.html", order=order)

@app.route("/order/invoice/<int:oid>")
@login_required
def order_invoice(oid):
    order = Order.query.get_or_404(oid)
    if order.user_id != current_user.id: return redirect(url_for("index"))
    return render_template("invoice.html", order=order)

@app.route("/my-orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("my_orders.html", orders=orders)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("دسترسی غیرمجاز", "error"); return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    stats = {"users": User.query.count(), "products": Product.query.count(), "orders": Order.query.count(), "revenue": db.session.query(db.func.sum(Order.total)).filter(Order.status == "paid").scalar() or 0}
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    sales_labels = []; sales_data = []
    for i in range(6, -1, -1):
        day = datetime.now() - timedelta(days=i)
        sales_labels.append(day.strftime("%m/%d"))
        day_total = db.session.query(db.func.sum(Order.total)).filter(db.func.date(Order.created_at) == day.date(), Order.status == "paid").scalar() or 0
        sales_data.append(day_total)
    top_products_query = db.session.query(Product.name, db.func.sum(OrderItem.quantity).label('total_sold')).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id).filter(Order.status == "paid").group_by(Product.id).order_by(db.func.sum(OrderItem.quantity).desc()).limit(5).all()
    top_labels = [p[0] for p in top_products_query]; top_data = [p[1] for p in top_products_query]
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders, sales_labels=sales_labels, sales_data=sales_data, top_labels=top_labels, top_data=top_data)

@app.route("/admin/products")
@login_required
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all(); categories = Category.query.all()
    return render_template("admin/products.html", products=products, categories=categories)

@app.route("/admin/products/add", methods=["POST"])
@login_required
@admin_required
def admin_add_product():
    name = request.form.get("name"); cat_id = int(request.form.get("category_id")); price = int(request.form.get("price"))
    old_price = request.form.get("old_price"); stock = int(request.form.get("stock", 0)); description = request.form.get("description", "")
    image_file = request.files.get("image_file"); image_url = request.form.get("image_url", "").strip(); final_image = IMG_CPU
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename); filename = f"{random.randint(1000, 9999)}_{filename}"
        image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename)); final_image = f"/static/uploads/{filename}"
    elif image_url: final_image = image_url
    p = Product(name=name, category_id=cat_id, price=price, old_price=int(old_price) if old_price else None, stock=stock, image=final_image, description=description)
    db.session.add(p); db.session.commit(); flash("محصول اضافه شد ✓", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/delete/<int:pid>", methods=["POST"])
@login_required
@admin_required
def admin_delete_product(pid):
    p = Product.query.get_or_404(pid); db.session.delete(p); db.session.commit(); flash("محصول حذف شد", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/edit/<int:pid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(pid):
    p = Product.query.get_or_404(pid)
    if request.method == "POST":
        p.name = request.form.get("name"); p.category_id = int(request.form.get("category_id")); p.price = int(request.form.get("price"))
        old_price = request.form.get("old_price"); p.old_price = int(old_price) if old_price else None
        p.stock = int(request.form.get("stock", 0)); p.description = request.form.get("description", "")
        image_file = request.files.get("image_file"); image_url = request.form.get("image_url", "").strip()
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename); filename = f"{random.randint(1000, 9999)}_{filename}"
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename)); p.image = f"/static/uploads/{filename}"
        elif image_url: p.image = image_url
        db.session.commit(); flash("محصول ویرایش شد ✓", "success"); return redirect(url_for("admin_products"))
    categories = Category.query.all()
    return render_template("admin/edit_product.html", product=p, categories=categories)

@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)

@app.route("/admin/orders/<int:oid>/status", methods=["POST"])
@login_required
@admin_required
def admin_change_status(oid):
    order = Order.query.get_or_404(oid)
    new_status = request.form.get("status"); order.status = new_status; db.session.commit()
    status_text = {"shipped": "ارسال شد", "delivered": "تحویل داده شد", "paid": "پرداخت شد", "cancelled": "لغو شد"}.get(new_status, new_status)
    notif = Notification(user_id=order.user_id, message=f"وضعیت سفارش #{order.id} تغییر کرد: {status_text}", link=f"/my-orders")
    db.session.add(notif); db.session.commit()
    flash("وضعیت بروزرسانی شد و اعلان برای کاربر ارسال شد", "success")
    return redirect(url_for("admin_orders"))

@app.route("/admin/coupons", methods=["GET", "POST"])
@login_required
@admin_required
def admin_coupons():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper(); discount = int(request.form.get("discount_percent", 0))
        if code and discount > 0:
            if not Coupon.query.filter_by(code=code).first():
                db.session.add(Coupon(code=code, discount_percent=discount)); db.session.commit(); flash("کد تخفیف اضافه شد ✓", "success")
            else: flash("این کد از قبل وجود دارد", "error")
        return redirect(url_for("admin_coupons"))
    coupons = Coupon.query.all()
    return render_template("admin/coupons.html", coupons=coupons)

@app.route("/admin/coupons/delete/<int:cid>", methods=["POST"])
@login_required
@admin_required
def admin_delete_coupon(cid):
    c = Coupon.query.get_or_404(cid); db.session.delete(c); db.session.commit(); flash("کد حذف شد", "success")
    return redirect(url_for("admin_coupons"))

@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)

@app.route("/admin/users/delete/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(uid):
    u = User.query.get_or_404(uid)
    if u.is_admin: flash("نمی‌توانید ادمین را حذف کنید", "error")
    else: db.session.delete(u); db.session.commit(); flash("کاربر حذف شد", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/reviews")
@login_required
@admin_required
def admin_reviews():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=reviews)

@app.route("/admin/reviews/delete/<int:rid>", methods=["POST"])
@login_required
@admin_required
def admin_delete_review(rid):
    r = Review.query.get_or_404(rid); db.session.delete(r); db.session.commit(); flash("نظر حذف شد", "success")
    return redirect(url_for("admin_reviews"))

# ==================== اجرای اولیه دیتابیس ====================
with app.app_context():
    init_database()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🖥️  PC Zone فروشگاه در حال اجراست")
    print("🌐 http://localhost:5000")
    print("👤 ادمین: admin / admin123")
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)