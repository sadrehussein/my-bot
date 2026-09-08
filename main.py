import telebot
from telebot import types
import sqlite3
import requests

TOKEN = '8997773654:AAHxK2xJbfrbFCSLNF_j9iW9FuLXc5NM46E'
ADMIN_ID = 8284894695
PEEKERR_API_KEY = '4927e7f4eae32a24e9f1e08201796b36'
PEEKERR_API_URL = 'https://peakerr.com/api/v2'

BOT_ASIA_PHONE = '07710084759'
BOT_MASTER_CARD = '1521948248'

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            referred_by INTEGER DEFAULT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS force_channels (
            channel_username TEXT PRIMARY KEY,
            channel_title TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_channels (
            channel_username TEXT PRIMARY KEY,
            channel_title TEXT,
            reward INTEGER DEFAULT 200
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_task_joins (
            user_id INTEGER,
            channel_username TEXT,
            PRIMARY KEY(user_id, channel_username)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS used_vouchers (
            voucher_code TEXT PRIMARY KEY,
            user_id INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            service_type TEXT,
            temp_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id, referrer_id=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance, referred_by FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        ref = referrer_id if (referrer_id and referrer_id != user_id) else None
        cursor.execute('INSERT INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)', (user_id, 0.0, ref))
        conn.commit()
        balance = 0.0
    else:
        balance = row[0]
    conn.close()
    return balance

def set_user_state(user_id, state, service_type=None, temp_data=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO user_states (user_id, state, service_type, temp_data) VALUES (?, ?, ?, ?)', (user_id, state, service_type, temp_data))
    conn.commit()
    conn.close()

def get_user_state(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT state, service_type, temp_data FROM user_states WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else (None, None, None)

def clear_user_state(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def check_force_sub(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT channel_username FROM force_channels')
    channels = cursor.fetchall()
    conn.close()
    
    for ch in channels:
        ch_username = ch[0]
        try:
            member = bot.get_chat_member(ch_username, user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                return False
        except Exception:
            return False
    return True

def send_to_peakerr(service_id, link, quantity):
    data = {
        'key': PEEKERR_API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }
    try:
        response = requests.post(PEEKERR_API_URL, data=data, timeout=15)
        return response.json()
    except Exception as e:
        return {'error': str(e)}

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    show_admin_menu(message.chat.id, message.message_id if hasattr(message, 'message_id') else None)

def show_admin_menu(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قناة إجبارية", callback_data="adm_add_force"),
        types.InlineKeyboardButton("➖ حذف قناة إجبارية", callback_data="adm_del_force"),
        types.InlineKeyboardButton("➕ إضافة قناة تجميع نقاط", callback_data="adm_add_task"),
        types.InlineKeyboardButton("➖ حذف قناة تجميع نقاط", callback_data="adm_del_task"),
        types.InlineKeyboardButton("📊 إحصائيات البوت", callback_data="adm_stats"),
        types.InlineKeyboardButton("🔙 إغلاق لوحة التحكم", callback_data="back_home")
    )
    txt = "🛠 **لوحة تحكم المطور الذكية (تحكم كامل):**"
    if message_id:
        try:
            bot.edit_message_text(txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, txt, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    clear_user_state(user_id)
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except ValueError:
            pass

    balance = get_user(user_id, referrer_id)
    
    if not check_force_sub(user_id):
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT channel_username, channel_title FROM force_channels')
        channels = cursor.fetchall()
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in channels:
            title = ch[1] if ch[1] else ch[0]
            markup.add(types.InlineKeyboardButton(f"اشترك في: {title}", url=f"https://t.me/{ch[0].replace('@','')}"))
        
        markup.add(types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        
        txt = (
            "⚠️ عذراً عزيزي، يجب عليك الاشتراك في قنوات البوت الإجبارية لتتمكن من استخدام البوت!\n\n"
            "يرجى الاشتراك في القنوات أدناه ثم اضغط على زر التحقق:"
        )
        bot.send_message(user_id, txt, reply_markup=markup)
        return

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        ref_id = row[0]
        cursor.execute('UPDATE users SET balance = balance + 500 WHERE user_id = ?', (ref_id,))
        cursor.execute('UPDATE users SET referred_by = NULL WHERE user_id = ?', (user_id,))
        conn.commit()
        try:
            bot.send_message(ref_id, "🎉 مبروك! دخل شخص جديد عبر رابط دعوتك وأتم الاشتراك الإجباري، وتمت إضافة 500 نقطة إلى رصيدك! 💎")
        except Exception:
            pass
    conn.close()

    show_main_menu(user_id, message.chat.id, name, balance)

def show_main_menu(user_id, chat_id, name, balance, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_services = types.InlineKeyboardButton("🚀 تمويل قناتك أو مجموعتك", callback_data="services")
    btn_earn = types.InlineKeyboardButton("💰 تجميع النقاط", callback_data="earn_points")
    btn_charge = types.InlineKeyboardButton("💳 شحن النقاط (آسيا / ماستر)", callback_data="charge_points")
    btn_transfer = types.InlineKeyboardButton("💸 تحويل النقاط", callback_data="transfer_points")
    btn_gift = types.InlineKeyboardButton("🎁 كود هدية", callback_data="gift_code")
    btn_ref = types.InlineKeyboardButton("👥 رابط الدعوة (500 نقطة)", callback_data="referral_link")
    btn_profile = types.InlineKeyboardButton("👤 معلومات حسابك", callback_data="profile")
    btn_orders = types.InlineKeyboardButton("📋 سجل تمويلاتي", callback_data="my_orders")
    
    markup.add(btn_services, btn_earn, btn_charge, btn_transfer, btn_gift, btn_ref, btn_profile, btn_orders)
    
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ لوحة تحكم المطور", callback_data="admin_menu"))

    welcome_text = (
        f"• أهلاً بك عزيزي {name} في بوت التمويل الشامل 🚀\n"
        "• تمويل حقيقي ووهمي لكل المنصات مع نظام تجميع وشحن تلقائي ⭐\n"
        "----------------------------------------\n"
        f"~ أيدي حسابك: {user_id}\n"
        f"~ رصيدك الحالي: {int(balance) if balance.is_integer() else balance} 💎"
    )

    if message_id:
        try:
            bot.edit_message_text(welcome_text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "check_sub":
        if check_force_sub(user_id):
            bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح! أهلاً بك.", show_alert=True)
            balance = get_user(user_id)
            show_main_menu(user_id, call.message.chat.id, call.message.first_name, balance, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ لم تقم بالاشتراك في كافة القنوات المطلوبة بعد!", show_alert=True)

    elif call.data == "profile":
        balance = get_user(user_id)
        text = f"👤 معلومات الحساب:\n\n🆔 الأيدي: {user_id}\n💎 الرصيد: {int(balance) if balance.is_integer() else balance} نقطة"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("رجوع ⬅️", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "referral_link":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            "👥 نظام دعوة الأصدقاء:\n\n"
            "• شارك رابط دعوتك مع أصدقائك، وكل صديق يدخل عبر رابطك ويشترك في القنوات الإجبارية ستحصل أنت على 500 نقطة!\n\n"
            f"🔗 رابط الدعوة الخاص بك:\n{ref_link}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("رجوع ⬅️", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "earn_points":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT channel_username, channel_title, reward FROM task_channels')
        tasks = cursor.fetchall()
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        if not tasks:
            text = "💰 قسم تجميع النقاط:\n\nلا توجد قنوات تجميع مضافة حالياً من المطور. تابعنا لاحقاً!"
        else:
            text = "💰 قسم تجميع النقاط:\n\nاختر قناة واشترك بيها لاكتساب النقاط:"
            for t in tasks:
                ch_user, ch_title, reward = t[0], t[1], t[2]
                title = ch_title if ch_title else ch_user
                markup.add(types.InlineKeyboardButton(f"📢 {title} (+{reward} نقطة)", callback_data=f"join_task_{ch_user}"))
        
        markup.add(types.InlineKeyboardButton("رجوع ⬅️", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("join_task_"):
        ch_user = call.data.replace("join_task_", "")
        try:
            member = bot.get_chat_member(ch_user, user_id)
            if member.status in ['creator', 'administrator', 'member']:
                conn = sqlite3.connect('bot_database.db')
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM user_task_joins WHERE user_id = ? AND channel_username = ?', (user_id, ch_user))
                already = cursor.fetchone()
                
                if already:
                    bot.answer_callback_query(call.id, "⚠️ لقد قمت بجمع نقاط هذه القناة مسبقاً!", show_alert=True)
                else:
                    cursor.execute('SELECT reward FROM task_channels WHERE channel_username = ?', (ch_user,))
                    rw_row = cursor.fetchone()
                    reward = rw_row[0] if rw_row else 200
                    
                    cursor.execute('INSERT INTO user_task_joins (user_id, channel_username) VALUES (?, ?)', (user_id, ch_user))
                    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (reward, user_id))
                    conn.commit()
                    conn.close()
                    bot.answer_callback_query(call.id, f"✅ مبروك! تمت إضافة {reward} نقطة إلى رصيدك.", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ أنت لم تشترك في القناة بعد أو لم يتم رصد اشتراكك!", show_alert=True)
        except Exception:
            bot.answer_callback_query(call.id, "❌ حدث خطأ، تأكد من اشتراكك بالقناة.", show_alert=True)

    # قسم شحن النقاط (حزم متصاعدة من 10k إلى 150k مع أسعار أعلى وأقوى ومقترحة خصيصاً)
    elif call.data == "charge_points":
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # جدول الأسعار المرتفعة والمحدثة بدقة حسب طلبك (تعديل تصاعدي من 10k بـ $8.5 وتصعد بانتظام)
        packages = [
            (10000, 8.5),
            (15000, 13.0),
            (20000, 17.5),
            (25000, 22.0),
            (30000, 26.5),
            (35000, 31.0),
            (40000, 35.5),
            (45000, 40.0),
            (50000, 44.5),
            (55000, 49.0),
            (60000, 53.5),
            (65000, 58.0),
            (70000, 62.5),
            (75000, 67.0),
            (80000, 71.5),
            (85000, 76.0),
            (90000, 80.5),
            (95000, 85.0),
            (100000, 90.0),
            (105000, 95.0),
            (110000, 100.0),
            (115000, 105.0),
            (120000, 110.0),
            (125000, 115.0),
            (130000, 120.0),
            (135000, 125.0),
            (140000, 130.0),
            (145000, 135.0),
            (150000, 140.0)
        ]
        
        for pts, price in packages:
            pts_label = f"{int(pts/1000)}k نقطة"
            markup.add(types.InlineKeyboardButton(f"💎 {pts_label} - (${price})", callback_data=f"buy_pkg_{pts}_{price}"))
            
        markup.add(types.InlineKeyboardButton("رجوع ⬅️", callback_data="back_home"))
        bot.edit_message_text(
            "💳 **قسم شحن النقاط الفوري (آسيا سيل / ماستر كارد):**\n\n"
            f"• رقم آسياسيل للتحويل: `{BOT_ASIA_PHONE}`\n"
            f"• ماستر كارد للتحويل: `{BOT_MASTER_CARD}`\n\n"
            "ℹ️ **ملاحظة:** يتم تسليم النقاط لحسابك **تلقائياً فورياً** بمجرد إرسال كود التحويل أو رقم العملية أدناه!\n\n"
            "اختر الحزمة المطلوبة:",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup
        )

    elif call.data.startswith("buy_pkg_"):
        parts = call.data.split("_")
        pts = parts[2]
        price = parts[3]
        
        set_user_state(user_id, 'waiting_auto_charge_code', None, f"{pts}_{price}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("إلغاء ❌", callback_data="charge_points"))
        
        text = (
            f"📦 **تفاصيل الحزمة المختارة:**\n"
            f"• عدد النقاط: `{int(pts):,}` نقطة 💎\n"
            f"• السعر المطلوب: `${price}` 💵\n\n"
            f"طرق الدفع المتوفرة:\n"
            f"1️⃣ رصيد آسياسيل تحويل على الرقم: `{BOT_ASIA_PHONE}`\n"
            f"2️⃣ تحويل ماستر كارد على الرقم: `{BOT_MASTER_CARD}`\n\n"
            "📩 **أرسل الآن (رقم عملية التحويل أو كود التحويل المكون من أرقام) في رسالة هنا، وسيقوم البوت بإضافتها إلى رصيدك تلقائياً ودون أي انتظار!**"
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "services":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📱 تليجرام", callback_data="plat_telegram"),
            types.InlineKeyboardButton("🎵 تيك توك", callback_data="plat_tiktok"),
            types.InlineKeyboardButton("📸 إنستغرام", callback_data="plat_insta"),
            types.InlineKeyboardButton("📘 فيسبوك", callback_data="plat_fb"),
            types.InlineKeyboardButton("رجوع ⬅️", callback_data="back_home")
        )
        bot.edit_message_text("اختر المنصة المطلوبة للتمويل (الحد الأدنى للرشق 2500 نقطة):", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "plat_telegram":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👥 متابعين تليجرام (وهمي - رخيص)", callback_data="service_tg_subs_fake"),
            types.InlineKeyboardButton("💎 متابعين تليجرام (حقيقي/ثابت - غالي)", callback_data="service_tg_subs_real"),
            types.InlineKeyboardButton("👁️ مشاهدات تليجرام", callback_data="service_tg_views"),
            types.InlineKeyboardButton("رجوع ⬅️", callback_data="services")
        )
        bot.edit_message_text("اختر خدمة تليجرام:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "plat_tiktok":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🎵 متابعين تيك توك (وهمي - رخيص)", callback_data="service_tt_subs_fake"),
            types.InlineKeyboardButton("⭐ متابعين تيك توك (حقيقي/ثابت - غالي)", callback_data="service_tt_subs_real"),
            types.InlineKeyboardButton("❤️ لايكات تيك توك", callback_data="service_tt_likes"),
            types.InlineKeyboardButton("👁️ مشاهدات تيك توك", callback_data="service_tt_views"),
            types.InlineKeyboardButton("رجوع ⬅️", callback_data="services")
        )
        bot.edit_message_text("اختر خدمة تيك توك:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "plat_insta":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📸 متابعين إنستغرام (وهمي - رخيص)", callback_data="service_ig_subs_fake"),
            types.InlineKeyboardButton("🔥 متابعين إنستغرام (حقيقي/ثابت - غالي)", callback_data="service_ig_subs_real"),
            types.InlineKeyboardButton("❤️ لايكات إنستغرام", callback_data="service_ig_likes"),
            types.InlineKeyboardButton("رجوع ⬅️", callback_data="services")
        )
        bot.edit_message_text("اختر خدمة إنستغرام:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "plat_fb":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📘 متابعين فيسبوك (وهمي - رخيص)", callback_data="service_fb_subs_fake"),
            types.InlineKeyboardButton("🌟 متابعين فيسبوك (حقيقي/ثابت - غالي)", callback_data="service_fb_subs_real"),
            types.InlineKeyboardButton("👍 لايكات فيسبوك", callback_data="service_fb_likes"),
            types.InlineKeyboardButton("رجوع ⬅️", callback_data="services")
        )
        bot.edit_message_text("اختر خدمة فيسبوك:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data in [
        "service_tg_subs_fake", "service_tg_subs_real", "service_tg_views",
        "service_tt_subs_fake", "service_tt_subs_real", "service_tt_likes", "service_tt_views",
        "service_ig_subs_fake", "service_ig_subs_real", "service_ig_likes",
        "service_fb_subs_fake", "service_fb_subs_real", "service_fb_likes"
    ]:
        balance = get_user(user_id)
        if balance < 2500:
            bot.answer_ca
