import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.text_utils import extract_amount, classify_category, get_description
from utils.date_utils import format_tanggal_indo, get_month_worksheet_name, get_jakarta_now
from handlers.auth_handlers import handle_oauth_code

logger = logging.getLogger(__name__)

async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Handle expense input from messages"""
    text = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"

    # Try to handle as OAuth code first (let user login tanpa harus /login ulang)
    if await handle_oauth_code(update, context, expense_tracker):
        return

    # Check if user is authenticated
    if not expense_tracker.is_user_authenticated(user_id):
        keyboard = [[InlineKeyboardButton("🔗 Login ke Google", callback_data="start_login")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔐 Anda perlu login ke Google terlebih dahulu untuk mencatat pengeluaran.\n\n"
            "Klik tombol di bawah atau gunakan /login.\n\n"
            "*Tips:* Setelah login Google, *hanya kirim kode* (bukan seluruh URL) ke bot.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return

    # Extract amount from message
    amount, start_pos, end_pos = extract_amount(text)

    if amount is None:
        await update.message.reply_text(
            "❌ Tidak dapat mendeteksi jumlah uang.\n\n"
            "💡 *Contoh format yang benar:*\n"
            "• `beli beras 50rb`\n"
            "• `makan siang 25000`\n"
            "• `bensin motor 30k`\n"
            "• `bayar listrik 200.000`\n\n"
            "*Tips:* Gunakan angka atau satuan seperti 'rb', 'k', 'ribu', atau 'juta'.",
            parse_mode='Markdown'
        )
        return

    if amount <= 0:
        await update.message.reply_text("❌ Jumlah uang tidak boleh nol atau negatif.")
        return

    # Get description and classify category
    description = get_description(text, start_pos, end_pos)
    category = classify_category(description)

    # Show loading message
    loading_msg = await update.message.reply_text("⏳ Menyimpan ke Google Sheet...")

    # Add to spreadsheet
    success, message = expense_tracker.add_expense(user_id, amount, description, category)

    if success:
        # Get current date in Indonesian format
        now = get_jakarta_now()
        tanggal_indo = format_tanggal_indo(now.strftime('%Y-%m-%d'))
        month_name = get_month_worksheet_name(now.year, now.month)

        response = f"""
✅ *Pengeluaran berhasil dicatat!*

💰 *Jumlah:* Rp {amount:,}
📝 *Keterangan:* {description}
📂 *Kategori:* {category}
📅 *Tanggal:* {tanggal_indo}
📊 *Worksheet:* {month_name}

✨ Tersimpan ke Google Sheet pribadi Anda!
        """

        # Get user's spreadsheet URL
        spreadsheet_id = expense_tracker.user_spreadsheets.get(str(user_id))
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

        keyboard = [
            [InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)],
            [InlineKeyboardButton("📈 Lihat Ringkasan", callback_data="show_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await loading_msg.edit_text(
            f"❌ Gagal menyimpan: {message}\n\n"
            "Pastikan Anda sudah login dan Google Sheet Anda dapat diakses."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "start_login":
        # Import here to avoid circular import
        from handlers.auth_handlers import login
        await login(query, context, expense_tracker)
        return
    
    if query.data == "show_summary":
        if not expense_tracker.is_user_authenticated(user_id):
            await query.message.reply_text(
                "❌ Anda perlu login terlebih dahulu. Gunakan /login"
            )
            return
            
        loading_message = await query.message.reply_text("⏳ Mengambil ringkasan...")
        
        try:
            summary = expense_tracker.get_monthly_summary(user_id)
            await loading_message.edit_text(summary, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            await loading_message.edit_text("❌ Gagal mengambil ringkasan.")
    
    elif query.data == "show_help":
        from handlers.command_handlers import help_command
        await help_command(query, context)
