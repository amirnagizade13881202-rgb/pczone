import os
import psycopg2
from flask import Flask
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==================== تنظیمات ====================
BOT_TOKEN = "8900132541:AAGvmG-C177mw2jErsE7MSAcAA1af4DpUfE"
ADMIN_USERNAME = "@amirimigadze1388"
DB_URI = "postgresql://postgres.gmakikihtqvlvmkeyxza:As13881202%40pc@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# ==================== وب‌سرور فیک برای رندر ====================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "PC Zone Bot is running!"

def run_web_server():
    web_app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web_server, daemon=True).start()

# ==================== ساخت خودکار جدول ====================
def create_tables_if_not_exist():
    try:
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()
        # ساخت جدول محصولات در صورت نبود
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                category_id INTEGER,
                price INTEGER,
                old_price INTEGER,
                image VARCHAR(500),
                description TEXT,
                stock INTEGER,
                rating REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ جدول محصولات بررسی/ساخته شد.")
    except Exception as e:
        print(f"خطا در ساخت جدول: {e}")

# فراخوانی هنگام اجرا
create_tables_if_not_exist()

# ==================== اتصال به دیتابیس ====================
def get_db():
    conn = psycopg2.connect(DB_URI)
    conn.autocommit = True
    return conn

# ==================== توابع ربات ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = f"سلام {user_name} عزیز! 👋\nبه ربات فروشگاه **PC Zone** خوش آمدید. 🖥️\n\nاز منوی زیر استفاده کنید:"
    keyboard = [
        [InlineKeyboardButton("🛍️ مشاهده محصولات", callback_data="show_products")],
        [InlineKeyboardButton("🛒 سبد خرید من", callback_data="my_cart")],
        [InlineKeyboardButton("🔍 جستجوی محصول", callback_data="search_prompt")],
        [InlineKeyboardButton("📞 ارتباط با پشتیبانی", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("ℹ️ درباره ما", callback_data="about_us")]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM products LIMIT 10")
        products = cursor.fetchall()
        cursor.close(); conn.close()
        
        if not products:
            msg = "در حال حاضر هیچ محصولی در فروشگاه موجود نیست. 😕"
            if query: await query.edit_message_text(msg)
            else: await update.message.reply_text(msg)
            return

        keyboard = [[InlineKeyboardButton(f"{p[1]} - {p[2]:,} تومان", callback_data=f"product_{p[0]}")] for p in products]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main_menu")])
        
        msg_text = "📦 لطفاً یکی از محصولات را انتخاب کنید:"
        if query: await query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else: await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        error_msg = f"خطا: {str(e)}"
        if query: await query.edit_message_text(error_msg)
        else: await update.message.reply_text(error_msg)

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split("_")[1])
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, stock, description FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        cursor.close(); conn.close()
        if not product:
            await query.edit_message_text("محصول یافت نشد.")
            return
        text = f"🔹 **{product[0]}**\n\n💰 قیمت: {product[1]:,} تومان\n📦 موجودی: {product[2]} عدد\n📝 توضیحات: {product[3]}\n"
        keyboard = [
            [InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"addcart_{product_id}")],
            [InlineKeyboardButton("🌐 خرید از سایت", url="https://pczone-ice3.onrender.com")],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="show_products")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"خطا: {str(e)}")

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split("_")[1])
    if 'cart' not in context.user_data: context.user_data['cart'] = {}
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
            cursor.execute("SELECT name, price FROM products WHERE id = %s", (int(pid),))
            p = cursor.fetchone()
            if p:
                subtotal = p[1] * qty; total_price += subtotal
                text += f"▪️ {p[0]} (x{qty}) = {subtotal:,} تومان\n"
        cursor.close(); conn.close()
        text += f"\n💰 **جمع کل:** {total_price:,} تومان"
        keyboard = [
            [InlineKeyboardButton("🌐 تکمیل خرید در سایت", url="https://pczone-ice3.onrender.com/cart")],
            [InlineKeyboardButton("🗑️ خالی کردن سبد", callback_data="clear_cart")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        if query: await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"خطا: {str(e)}")

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
    if not context.user_data.get('searching'): return
    search_query = update.message.text
    context.user_data['searching'] = False
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM products WHERE name ILIKE %s LIMIT 5", (f"%{search_query}%",))
        products = cursor.fetchall()
        cursor.close(); conn.close()
        if not products:
            await update.message.reply_text(f"❌ محصولی با نام «{search_query}» پیدا نشد.")
            return
        keyboard = [[InlineKeyboardButton(f"{p[1]} - {p[2]:,} تومان", callback_data=f"product_{p[0]}")] for p in products]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
        await update.message.reply_text(f"🔍 نتایج جستجو برای «{search_query}»:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}")

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🖥️ **درباره PC Zone**\n\nما یک فروشگاه آنلاین تخصصی در زمینه قطعات کامپیوتر هستیم.\nضمانت اصالت کالا، ارسال سریع و پشتیبانی ۲۴/۷ از افتخارات ماست.\n\n🌐 وب‌سایت ما: https://pczone-ice3.onrender.com"
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
    msg = "به منوی اصلی خوش آمدید. یک گزینه را انتخاب کنید:"
    if query: await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== اجرای ربات ====================
def main():
    print("🤖 ربات در حال روشن شدن است...")
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
    print("✅ ربات با موفقیت روشن شد!")
    application.run_polling()

if __name__ == "__main__":
    main()
