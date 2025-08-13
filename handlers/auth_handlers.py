import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from models.expense_tracker import ExpenseTracker

logger = logging.getLogger(__name__)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker: ExpenseTracker):
    """Login command to initiate OAuth"""
    user_id = update.effective_user.id
    
    if expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "✅ Anda sudah login! Gunakan /logout untuk keluar dari akun Google."
        )
        return
    
    # Generate OAuth URL
    auth_url, state = expense_tracker.get_oauth_url(user_id)
    
    if not auth_url:
        await update.message.reply_text(
            "❌ Maaf, terjadi kesalahan saat membuat link login. Silakan coba lagi nanti."
        )
        return
    
    # Store state for verification
    context.user_data['oauth_state'] = state
    
    keyboard = [[InlineKeyboardButton("🔗 Login ke Google", url=auth_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    login_text = """
🔐 *Login ke Google Account*

1. Klik tombol di bawah untuk login ke Google
2. Berikan izin akses ke Google Sheets dan Drive
3. Copy kode yang muncul
4. Kirim kode tersebut ke bot ini

*Catatan:* Bot tidak akan menyimpan password Anda, hanya token akses untuk Google Sheets.
    """
    
    await update.message.reply_text(
        login_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_oauth_code(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker: ExpenseTracker):
    """Handle OAuth authorization code"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"
    code = update.message.text.strip()

    # Check if this looks like an OAuth code
    if not (len(code) > 20 and ('/' in code or '-' in code or '_' in code)):
        return False  # Not an OAuth code

    loading_msg = await update.message.reply_text("⏳ Memverifikasi kode dan membuat Google Sheet...")

    try:
        # Exchange code for credentials
        success = expense_tracker.exchange_code_for_credentials(code, user_id)

        if success:
            # Create user's spreadsheet
            spreadsheet_id = expense_tracker.create_user_spreadsheet(user_id, user_name)

            if spreadsheet_id:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

                success_text = f"""
✅ *Login berhasil dan Google Sheet sudah dibuat!*

🎉 Selamat, {user_name}! Bot sudah terhubung dengan akun Google Anda.

📊 Google Sheet pribadi Anda: [Klik di sini]({sheet_url})

📅 *Fitur worksheet per bulan:*
Bot akan otomatis membuat worksheet baru setiap bulan dengan nama seperti "Januari 2025", "Februari 2025", dst.

🚀 *Mulai mencatat pengeluaran:*
Kirim pesan seperti: `beli sayur 15rb`, `isi bensin 50k`, dll.

Gunakan /help untuk melihat semua fitur!
                """

                keyboard = [
                    [InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)],
                    [InlineKeyboardButton("📋 Lihat Bantuan", callback_data="show_help")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await loading_msg.edit_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await loading_msg.edit_text(
                    "✅ *Login ke Google berhasil*, namun *gagal membuat Google Sheet baru* di Drive Anda.\n\n"
                    "🔄 Silakan coba /logout lalu /login ulang. Jika masalah berlanjut, pastikan akun Google Anda tidak melebihi batas quota Google Drive."
                )
        else:
            await loading_msg.edit_text(
                "❌ Kode tidak valid atau sudah kedaluwarsa.\n\n"
                "Silakan lakukan /login ulang dan pastikan Anda mengirim *kode* (bukan seluruh URL) yang didapat setelah login Google."
            )

    except Exception as e:
        logger.error(f"OAuth error: {e}")
        await loading_msg.edit_text(
            "❌ Terjadi kesalahan saat memproses login.\n\n"
            "Pastikan Anda mengirim *kode* (bukan seluruh URL) yang didapat setelah login Google.\n"
            "Jika masalah berlanjut, silakan coba /logout lalu /login ulang."
        )

    return True  # Indicates this was handled as OAuth code

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker: ExpenseTracker):
    """Logout command"""
    user_id = update.effective_user.id
    
    if str(user_id) in expense_tracker.user_credentials:
        del expense_tracker.user_credentials[str(user_id)]
    if str(user_id) in expense_tracker.user_spreadsheets:
        del expense_tracker.user_spreadsheets[str(user_id)]
    
    expense_tracker.save_user_credentials()
    
    await update.message.reply_text(
        "✅ Anda telah logout dari Google Account. Gunakan /login untuk masuk kembali."
    )
