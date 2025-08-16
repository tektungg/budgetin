from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Start command handler"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"
    
    if expense_tracker.is_user_authenticated(user_id):
        if not expense_tracker.has_balance_set(user_id):
            # User authenticated but no balance set
            welcome_text = f"""
🤖 *Selamat datang kembali, {user_name}!*

Bot Budgetin Anda sudah terhubung dengan Google, tapi Anda belum mengatur saldo awal.

💰 *Set saldo awal terlebih dahulu:*
Kirim pesan berupa angka saldo Anda, contoh:
• `1000000` (untuk Rp 1.000.000)
• `500ribu` atau `500rb`
• `2juta`

📊 Setelah mengatur saldo, Anda bisa mulai mencatat pengeluaran dan saldo akan otomatis ter-tracking!
            """
        else:
            current_balance = expense_tracker.get_user_balance(user_id)
            welcome_text = f"""
🤖 *Selamat datang kembali, {user_name}!*

Bot Budgetin Anda sudah siap digunakan!

💳 *Saldo saat ini:* Rp {current_balance:,}

📝 *Cara mencatat pengeluaran:*
Kirim pesan dengan format bebas, contoh:
• "beli beras 50rb"
• "makan siang 25000"  
• "bensin motor 30k"

📊 *Perintah tersedia:*
• /ringkasan - Lihat ringkasan bulan ini
• /sheet - Buka Google Sheet Anda
• /logout - Keluar dari akun Google
• /help - Bantuan lengkap

🆕 *FITUR BARU - Smart Features:*
• /budget - Budget planning per kategori
• /insights - Spending analytics & insights
• /alerts - Smart alerts sistem

✨ Data Anda tersimpan otomatis di Google Sheet pribadi dengan worksheet terpisah per bulan!
            """
    else:
        welcome_text = f"""
🤖 *Selamat datang di Budgetin Bot, {user_name}!*

Bot ini akan membantu Anda mencatat pengeluaran secara otomatis ke Google Sheet pribadi Anda.

🔐 *Untuk memulai, Anda perlu login ke Google:*
Gunakan perintah /login untuk menghubungkan akun Google Anda

✨ *Fitur unggulan:*
• 📊 Google Sheet pribadi di Drive Anda
• 📅 Worksheet terpisah per bulan  
• 🤖 Deteksi otomatis jumlah dan kategori
• 📱 Interface interaktif dengan tombol
• 📈 Ringkasan bulanan otomatis

Ketik /login untuk memulai!
        """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
📋 *Bantuan Budgetin Bot*

🔐 *Autentikasi:*
• /login - Login ke Google Account
• /logout - Keluar dari akun Google  
• /sheet - Buka Google Sheet Anda

� *Fitur Saldo:*
• Set saldo awal setelah login pertama kali
• /saldo - Lihat saldo saat ini dan isi saldo
• Saldo otomatis berkurang setiap pengeluaran
• Tampil di ringkasan dan Google Sheet

�📝 *Cara mencatat pengeluaran:*
Kirim pesan dengan format bebas yang mengandung jumlah uang:
• "beli sayur 15rb"
• "isi bensin 50000" 
• "bayar listrik 200k"
• "makan di warteg 12ribu"

💰 *Format jumlah yang didukung:*
• 50rb, 50 rb, 50ribu, 50k
• 1.5juta, 2juta
• 50000 (angka biasa)
• 50.000 (dengan titik)

🏷️ *Kategori otomatis:*
• Daily Needs (makan, belanja, grocery)
• Transportation (bensin, ojek, grab)  
• Utilities (listrik, air, internet)
• Health (obat, dokter, RS)
• Urgent (darurat, mendadak)
• Entertainment (nonton, game, cafe)

📊 *Fitur laporan:*
• /ringkasan - Ringkasan bulan ini dengan saldo
• /balance - Kelola saldo Anda
• /kategori - Lihat semua kategori

✨ *Keunggulan:*
• Google Sheet pribadi di Drive Anda
• Worksheet terpisah per bulan otomatis
• Tracking saldo otomatis di setiap transaksi
• Data aman dan terkontrol penuh oleh Anda
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Summary command handler"""
    user_id = update.effective_user.id
    
    if not expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "❌ Anda belum login. Gunakan /login terlebih dahulu."
        )
        return
    
    loading_msg = await update.message.reply_text("⏳ Mengambil ringkasan...")
    
    summary = expense_tracker.get_monthly_summary(user_id)
    await loading_msg.edit_text(summary, parse_mode='Markdown')

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Categories command handler"""
    cat_text = """
📂 *Kategori Pengeluaran Otomatis:*

🥘 *Daily Needs*
makan, minum, beras, sayur, buah, grocery, belanja

🚗 *Transportation*
bensin, ojek, grab, gojek, taxi, parkir, tol

⚡ *Utilities*
listrik, air, internet, pulsa, token

🏥 *Health*  
obat, dokter, rumah sakit, vitamin

🚨 *Urgent*
darurat, urgent, mendadak, emergency

🎮 *Entertainment*
nonton, game, musik, cafe, restaurant, film

Bot akan mendeteksi kategori secara otomatis berdasarkan kata kunci dalam keterangan Anda.
    """
    await update.message.reply_text(cat_text, parse_mode='Markdown')

async def sheet(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Open user's Google Sheet"""
    user_id = update.effective_user.id
    
    if not expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "❌ Anda belum login. Gunakan /login terlebih dahulu."
        )
        return
    
    spreadsheet_id = expense_tracker.user_spreadsheets.get(str(user_id))
    if spreadsheet_id:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        keyboard = [[InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 *Google Sheet Anda*\n\nKlik tombol di bawah untuk membuka:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ Google Sheet tidak ditemukan. Silakan /logout dan /login ulang."
        )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Balance command handler"""
    user_id = update.effective_user.id
    
    if not expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "❌ Anda belum login. Gunakan /login terlebih dahulu."
        )
        return
    
    if not expense_tracker.has_balance_set(user_id):
        await update.message.reply_text(
            "💰 Anda belum mengatur saldo. Silakan kirim angka saldo Anda untuk memulai."
        )
        return
    
    current_balance = expense_tracker.get_user_balance(user_id)
    
    response = f"""
💳 *Saldo Anda Saat Ini*

💰 Rp {current_balance:,}

💡 *Tips:*
• Gunakan tombol "Isi Saldo" untuk menambah saldo
• Saldo otomatis berkurang setiap pencatatan pengeluaran
• Lihat history saldo lengkap di Google Sheet Anda
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Isi Saldo", callback_data="add_balance")],
        [InlineKeyboardButton("📊 Buka Google Sheet", 
         url=f"https://docs.google.com/spreadsheets/d/{expense_tracker.user_spreadsheets.get(str(user_id))}/edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        response,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
