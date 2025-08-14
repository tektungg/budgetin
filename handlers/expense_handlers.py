import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.text_utils import extract_amount, classify_category, get_description
from utils.date_utils import format_tanggal_indo, get_month_worksheet_name, get_jakarta_now
from handlers.auth_handlers import handle_oauth_code, handle_balance_setup

logger = logging.getLogger(__name__)

async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Handle expense input from messages"""
    text = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"

    # Try to handle as OAuth code first (let user login tanpa harus /login ulang)
    if await handle_oauth_code(update, context, expense_tracker):
        return
    
    # Try to handle balance setup
    if await handle_balance_setup(update, context, expense_tracker):
        return
    
    # Try to handle add balance
    if await handle_add_balance(update, context, expense_tracker):
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
    
    # Check if user has set balance
    if not expense_tracker.has_balance_set(user_id):
        await update.message.reply_text(
            "💰 *Anda perlu mengatur saldo awal terlebih dahulu.*\n\n"
            "Silakan masukkan saldo awal Anda:\n\n"
            "💡 *Contoh:*\n"
            "• `1000000` (untuk Rp 1.000.000)\n"
            "• `500ribu` atau `500rb`\n"  
            "• `2juta`\n\n"
            "Kirim angka saja atau dengan format yang didukung.",
            parse_mode='Markdown'
        )
        context.user_data['needs_balance_setup'] = True
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
        current_balance = expense_tracker.get_user_balance(user_id)

        response = f"""
✅ *Pengeluaran berhasil dicatat!*

💰 *Jumlah:* Rp {amount:,}
📝 *Keterangan:* {description}
📂 *Kategori:* {category}
📅 *Tanggal:* {tanggal_indo}
📊 *Worksheet:* {month_name}

💳 *Sisa Saldo:* Rp {current_balance:,}

✨ Tersimpan ke Google Sheet pribadi Anda!
        """

        # Get user's spreadsheet URL
        spreadsheet_id = expense_tracker.user_spreadsheets.get(str(user_id))
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

        keyboard = [
            [InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)],
            [InlineKeyboardButton("💰 Isi Saldo", callback_data="add_balance")],
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
    
    if query.data == "add_balance":
        if not expense_tracker.is_user_authenticated(user_id):
            await query.message.reply_text(
                "❌ Anda perlu login terlebih dahulu. Gunakan /login"
            )
            return
            
        context.user_data['adding_balance'] = True
        await query.message.reply_text(
            "💰 *Isi Saldo*\n\n"
            "Masukkan jumlah saldo yang ingin Anda tambahkan:\n\n"
            "💡 *Contoh:*\n"
            "• `100000` (untuk menambah Rp 100.000)\n"
            "• `500ribu` atau `500rb`\n"
            "• `1juta`\n\n"
            "Kirim angka saja atau dengan format yang didukung.",
            parse_mode='Markdown'
        )
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

async def handle_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_tracker):
    """Handle adding balance"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if this is for adding balance
    if not context.user_data.get('adding_balance', False):
        return False  # Not handling balance addition
    
    try:
        # Parse balance amount
        amount = int(text.replace('.', '').replace(',', '').replace('rb', '000').replace('ribu', '000').replace('juta', '000000').replace('k', '000'))
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Jumlah tidak boleh nol atau negatif. Silakan masukkan angka yang benar."
            )
            return True
        
        # Add balance
        new_balance = expense_tracker.add_balance(user_id, amount)
        
        # Clear flag
        context.user_data['adding_balance'] = False
        
        response = f"""
✅ *Saldo berhasil ditambahkan!*

💰 *Ditambahkan:* Rp {amount:,}
💳 *Saldo baru:* Rp {new_balance:,}

🎉 Saldo Anda telah diperbarui!
        """
        
        keyboard = [
            [InlineKeyboardButton("📈 Lihat Ringkasan", callback_data="show_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return True
        
    except ValueError:
        await update.message.reply_text(
            "❌ Format jumlah tidak valid.\n\n"
            "💡 *Contoh format yang benar:*\n"
            "• `100000` (untuk Rp 100.000)\n"
            "• `500ribu` atau `500rb`\n"
            "• `1juta`\n\n"
            "Silakan coba lagi dengan angka saja atau format yang didukung.",
            parse_mode='Markdown'
        )
        return True
