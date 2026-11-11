import sqlite3
import os
from flask import Flask
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==================== تنظیمات ====================
BOT_TOKEN = "9072062584:AAHyr3ZeRD6o0rhGbNbL7JSUCpSJ6i1P3O0"
DB_PATH = os.path.join("instance", "pczone.db")
ADMIN_USERNAME = "@amirimigadze1388"  # آیدی تلگرام خودت

# ==================== وب‌سرور فیک برای رندر ====================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "PC Zone Bot is running!"

def run_web_server():
    web_app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web_server, daemon=True).start()

# ==================== ساخت جدول در صورت نبود ====================
def create_tables_if_not_exist():
    # مسیر دیتابیس روی سرور رندر
    db_file = "/tmp/pczone.db" if os.path.exists("/tmp/pczone.db") else "pczone.db"
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # ساخت جدول محصولات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            price INTEGER,
            old_price INTEGER,
            image TEXT,
            description TEXT,
            stock INTEGER,
            rating REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # چک کردن اینکه آیا محصولی هست یا نه
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        # اگه خالی بود، یه محصول تستی اضافه کن تا جدول ساخته بشه
        cursor.execute("""
            INSERT INTO products (name, category_id, price, old_price, image, description, stock, rating) 
            VALUES ('پردازنده تستی Intel Core i9', 1, 28500000, 31000000, '', 'این یک محصول تستی است. برای دیدن محصولات اصلی، از پنل ادمین سایت استفاده کنید.', 5, 4.9)
        """)
        cursor.execute("""
            INSERT INTO products (name, category_id, price, old_price, image, description, stock, rating) 
            VALUES ('کارت گرافیک تستی RTX 4090', 2, 95000000, 105000000, '', 'این یک محصول تستی است.', 3, 5.0)
        """)
    
    conn.commit()
    conn.close()

# ==================== اتصال به دیتابیس ====================
def get_db():
    # اولویت اول: مسیر سرور رندر (لینوکس)
    if os.path.exists("/tmp/pczone.db"):
        conn = sqlite3.connect("/tmp/pczone.db")
    # اولویت دوم: مسیر لوکال کامپیوتر (پوشه instance)
    elif os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
    # اولویت سوم: مسیر پیش‌فرض
    else:
        conn = sqlite3.connect("pczone.db")
    conn.row_factory = sqlite3.Row
    return conn

# ==================== توابع ربات ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"سلام {user_name} عزیز! 👋\n"
        "به ربات فروشگاه **PC Zone** خوش آمدید. 🖥️\n\n"
        "از منوی زیر استفاده کنید:"
    )
    keyboard = [
        [InlineKeyboardButton("🛍️ مشاهده محصولات", callback_data="show_products")],
        [InlineKeyboardButton("🛒 سبد خرید من", callback_data="my_cart")],
        [InlineKeyboardButton("🔍 جستجوی محصول", callback_data="search_prompt")],
        [InlineKeyboardButton("📞 ارتباط با پشتیبانی", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("ℹ️ درباره ما", callback_data="about_us")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM products LIMIT 10")
        products = cursor.fetchall()
        conn.close()

        if not products:
            msg = "در حال حاضر هیچ محصولی در فروشگاه موجود نیست. 😕"
            if query: await query.edit_message_text(msg)
            else: await update.message.reply_text(msg)
            return

        keyboard = []
        for p in products:
            btn_text = f"{p['name']} - {p['price']:,} تومان"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"product_{p['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg_text = "📦 لطفاً یکی از محصولات را انتخاب کنید:"
        if query: await query.edit_message_text(msg_text, reply_markup=reply_markup)
        else: await update.message.reply_text(msg_text, reply_markup=reply_markup)

    except Exception as e:
        error_msg = f"خطا در دریافت محصولات: {str(e)}"
        if query: await query.edit_message_text(error_msg)
        else: await update.message.reply_text(error_msg)

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[1])

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        conn.close()

        if not product:
            await query.edit_message_text("محصول یافت نشد.")
            return

        text = (
            f"🔹 **{product['name']}**\n\n"
            f"💰 قیمت: {product['price']:,} تومان\n"
            f"📦 موجودی: {product['stock']} عدد\n"
            f"📝 توضیحات: {product['description']}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"addcart_{product['id']}")],
            [InlineKeyboardButton("🌐 خرید از سایت", url="https://pczone-ice3.onrender.com")],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="show_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await query.edit_message_text(f"خطا در دریافت جزئیات: {str(e)}")

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split("_")[1])
    
    if 'cart' not in context.user_data:
        context.user_data['cart'] = {}
    
    cart = context.user_data['cart']
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    
    await query.answer(f"✓ به سبد اضافه شد (تعداد: {cart[str(product_id)]})", show_alert=True)

async def my_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    cart = context.user_data.get('cart', {})
    
    if not cart:
        msg = "🛒 سبد خرید شما خالی است."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        if query: await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else: await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        text = "🛒 **سبد خرید شما:**\n\n"
        total_price = 0
        
        for pid, qty in cart.items():
            cursor.execute("SELECT name, price FROM products WHERE id = ?", (int(pid),))
            p = cursor.fetchone()
            if p:
                subtotal = p['price'] * qty
                total_price += subtotal
                text += f"▪️ {p['name']} (x{qty}) = {subtotal:,} تومان\n"
        
        conn.close()
        text += f"\n💰 **جمع کل:** {total_price:,} تومان"
        
        keyboard = [
            [InlineKeyboardButton("🌐 تکمیل خرید در سایت", url="https://pczone-ice3.onrender.com/cart")],
            [InlineKeyboardButton("🗑️ خالی کردن سبد", callback_data="clear_cart")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query: await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else: await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await query.edit_message_text(f"خطا در نمایش سبد: {str(e)}")

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("سبد خالی شد!", show_alert=True)
    context.user_data['cart'] = {}
    await main_menu(update, context)

async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 لطفاً نام محصول مورد نظر خود را بنویسید و بفرستید:")
    context.user_data['searching'] = True

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('searching'):
        return
    
    search_query = update.message.text
    context.user_data['searching'] = False
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM products WHERE name LIKE ? LIMIT 5", (f"%{search_query}%",))
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            await update.message.reply_text(f"❌ محصولی با نام «{search_query}» پیدا نشد.")
            return
        
        keyboard = []
        for p in products:
            btn_text = f"{p['name']} - {p['price']:,} تومان"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"product_{p['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(f"🔍 نتایج جستجو برای «{search_query}»:", reply_markup=reply_markup)
        
    except Exception as e:
        await update.message.reply_text(f"خطا در جستجو: {str(e)}")

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "🖥️ **درباره PC Zone**\n\n"
        "ما یک فروشگاه آنلاین تخصصی در زمینه قطعات کامپیوتر هستیم.\n"
        "ضمانت اصالت کالا، ارسال سریع و پشتیبانی ۲۴/۷ از افتخارات ماست.\n\n"
        "🌐 وب‌سایت ما: https://pczone-ice3.onrender.com"
    )
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🛍️ مشاهده محصولات", callback_data="show_products")],
        [InlineKeyboardButton("🛒 سبد خرید من", callback_data="my_cart")],
        [InlineKeyboardButton("🔍 جستجوی محصول", callback_data="search_prompt")],
        [InlineKeyboardButton("📞 ارتباط با پشتیبانی", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("ℹ️ درباره ما", callback_data="about_us")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "به منوی اصلی خوش آمدید. یک گزینه را انتخاب کنید:"
    
    if query: await query.edit_message_text(msg, reply_markup=reply_markup)
    else: await update.message.reply_text(msg, reply_markup=reply_markup)

# ==================== اجرای ربات ====================
def main():
    print("🤖 ربات در حال روشن شدن است...")
    
    # ساخت جدول‌ها در زمان اجرا
    create_tables_if_not_exist()
    
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", main_menu))

    application.add_handler(CallbackQueryHandler(show_products, pattern="^show_products$"))
    application.add_handler(CallbackQueryHandler(product_detail, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(add_to_cart, pattern="^addcart_"))
    application.add_handler(CallbackQueryHandler(my_cart, pattern="^my_cart$"))
    application.add_handler(CallbackQueryHandler(clear_cart, pattern="^clear_cart$"))
    application.add_handler(CallbackQueryHandler(search_prompt, pattern="^search_prompt$"))
    application.add_handler(CallbackQueryHandler(about_us, pattern="^about_us$"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    print("✅ ربات با موفقیت روشن شد! حالا به تلگرام برو و به ربات پیام بده.")
    application.run_polling()

if __name__ == "__main__":
    main()
