import logging
import threading
import queue
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

    # First attempt with 5-second timeout using threading
    success = False
    message = ""
    smart_insights = {}
    
    try:
        import threading
        import queue
        
        def run_operation():
            """Run expense operation in separate thread"""
            try:
                result = expense_tracker.add_expense_with_smart_features(user_id, amount, description, category)
                result_queue.put(('success', result))
            except Exception as e:
                result_queue.put(('error', str(e)))
        
        # Create queue for thread communication
        result_queue = queue.Queue()
        
        # Start operation in separate thread
        operation_thread = threading.Thread(target=run_operation)
        operation_thread.daemon = True
        operation_thread.start()
        
        # Wait for result with 5-second timeout
        operation_thread.join(timeout=5.0)
        
        if operation_thread.is_alive():
            # Thread is still running - timeout occurred
            raise TimeoutError("Operation timed out after 5 seconds")
        
        # Get result from queue
        if not result_queue.empty():
            result_type, result_data = result_queue.get()
            if result_type == 'success':
                success, message, smart_insights = result_data
            else:
                raise Exception(result_data)
        else:
            raise Exception("No result received from operation")
        
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
💳 *Saldo tersisa:* Rp {current_balance:,}
📊 *Worksheet:* {month_name}
"""

            # Add smart insights to response
            alerts = []
            
            # Budget Alert
            if smart_insights.get('budget_alert'):
                budget_alert = smart_insights['budget_alert']
                alerts.append(f"\n{budget_alert['message']}")
            
            # Anomaly Detection
            if smart_insights.get('anomaly_detection'):
                anomaly_report = smart_insights['anomaly_detection']
                for anomaly in anomaly_report['anomalies']:
                    if anomaly.get('message'):
                        alerts.append(f"\n{anomaly['message']}")
            
            # Spending Velocity Alert
            if smart_insights.get('spending_velocity_alert'):
                velocity_alert = smart_insights['spending_velocity_alert']
                alerts.append(f"\n{velocity_alert['message']}")
            
            # Weekend Alert
            if smart_insights.get('weekend_alert'):
                weekend_alert = smart_insights['weekend_alert']
                alerts.append(f"\n{weekend_alert['message']}")
            
            # Add alerts to response
            if alerts:
                response += "\n⚠️ *Smart Alerts:*"
                for alert in alerts[:2]:  # Limit to 2 alerts to avoid too long message
                    response += alert
            
            # Create interactive buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 Ringkasan Bulan", callback_data="summary_month"),
                    InlineKeyboardButton("💰 Lihat Saldo", callback_data="check_balance")
                ],
                [
                    InlineKeyboardButton("📈 Budget Status", callback_data=f"budget_status_{category.replace(' ', '_')}"),
                    InlineKeyboardButton("🔍 Insights", callback_data="view_insights")
                ]
            ]
            
            # Add budget suggestion if no budget set for this category
            budget_status = expense_tracker.get_budget_status_for_category(user_id, category)
            if budget_status.get('status') == 'no_budget':
                keyboard.append([InlineKeyboardButton("💡 Set Budget", callback_data=f"suggest_budget_{category.replace(' ', '_')}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)

            await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await loading_msg.edit_text(
                f"❌ Gagal menyimpan: {message}\n\n"
                "Pastikan Anda sudah login dan Google Sheet Anda dapat diakses."
            )
    
    except TimeoutError:
        logger.warning(f"First attempt timed out after 5s for user {user_id}")
        
        # Retry message
        await loading_msg.edit_text(
            "⏳ *Proses lebih lama dari biasanya...*\n\n"
            "Sedang mencoba ulang (percobaan 2/2)...",
            parse_mode='Markdown'
        )
        
        # Second attempt with 5-second timeout using same threading approach
        try:
            def run_retry_operation():
                """Run retry operation in separate thread"""
                try:
                    result = expense_tracker.add_expense_with_smart_features(user_id, amount, description, category)
                    retry_queue.put(('success', result))
                except Exception as e:
                    retry_queue.put(('error', str(e)))
            
            # Create queue for retry thread communication
            retry_queue = queue.Queue()
            
            # Start retry operation in separate thread
            retry_thread = threading.Thread(target=run_retry_operation)
            retry_thread.daemon = True
            retry_thread.start()
            
            # Wait for result with 5-second timeout
            retry_thread.join(timeout=5.0)
            
            if retry_thread.is_alive():
                # Second attempt also timed out
                raise TimeoutError("Second attempt also timed out after 5 seconds")
            
            # Get result from retry queue
            if not retry_queue.empty():
                result_type, result_data = retry_queue.get()
                if result_type == 'success':
                    success, message, smart_insights = result_data
                else:
                    raise Exception(result_data)
            else:
                raise Exception("No result received from retry operation")
            
            if success:
                # Same success handling as above
                now = get_jakarta_now()
                tanggal_indo = format_tanggal_indo(now.strftime('%Y-%m-%d'))
                month_name = get_month_worksheet_name(now.year, now.month)
                current_balance = expense_tracker.get_user_balance(user_id)

                response = f"""
✅ *Pengeluaran berhasil dicatat!* (percobaan ke-2)

💰 *Jumlah:* Rp {amount:,}
📝 *Keterangan:* {description}
📂 *Kategori:* {category}
📅 *Tanggal:* {tanggal_indo}
💳 *Saldo tersisa:* Rp {current_balance:,}
📊 *Worksheet:* {month_name}
"""
                
                # Simple success message without complex features to avoid more timeouts
                await loading_msg.edit_text(response, parse_mode='Markdown')
            else:
                await loading_msg.edit_text(
                    f"❌ Gagal menyimpan setelah 2 percobaan: {message}\n\n"
                    "Pastikan Anda sudah login dan Google Sheet Anda dapat diakses."
                )
        
        except TimeoutError:
            logger.error(f"Second attempt also timed out after 5s for user {user_id}")
            await loading_msg.edit_text(
                "❌ *Operasi gagal setelah 2 percobaan (masing-masing 5 detik)*\n\n"
                "🔧 *Yang bisa Anda lakukan:*\n"
                "• Tunggu 1-2 menit lalu coba lagi\n"
                "• Pastikan koneksi internet stabil\n"
                "• Cek apakah data sudah tersimpan dengan /ringkasan\n\n"
                "⚙️ *Kemungkinan penyebab:*\n"
                "• Google API sedang lambat\n"
                "• Koneksi internet tidak stabil\n"
                "• Spreadsheet Anda sedang sibuk\n\n"
                "💡 Data mungkin sudah tersimpan meskipun ada timeout.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in second attempt: {e}")
            await loading_msg.edit_text(
                "❌ Terjadi kesalahan pada percobaan kedua.\n\n"
                "Silakan coba lagi dalam beberapa menit.",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Error in expense handling: {e}")
        error_str = str(e).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            await loading_msg.edit_text(
                "⏰ *Operasi timeout*\n\n"
                "Pencatatan pengeluaran memakan waktu terlalu lama.\n\n"
                "💡 *Yang bisa Anda lakukan:*\n"
                "• Cek apakah data sudah tersimpan dengan /ringkasan\n"
                "• Tunggu 1-2 menit lalu coba lagi\n"
                "• Pastikan koneksi internet stabil\n\n"
                "⚙️ Data mungkin sudah tersimpan meskipun ada timeout.",
                parse_mode='Markdown'
            )
        elif "quota" in error_str or "rate" in error_str:
            await loading_msg.edit_text(
                "⚠️ *Google API sedang sibuk*\n\n"
                "Terlalu banyak permintaan dalam waktu singkat.\n"
                "Silakan tunggu 2-3 menit lalu coba lagi.",
                parse_mode='Markdown'
            )
        elif "network" in error_str or "connection" in error_str:
            await loading_msg.edit_text(
                "🌐 *Masalah koneksi*\n\n"
                "Terjadi masalah koneksi jaringan.\n"
                "Pastikan internet stabil dan coba lagi.",
                parse_mode='Markdown'
            )
        else:
            await loading_msg.edit_text(
                "❌ Terjadi kesalahan saat memproses pengeluaran.\n\n"
                "Silakan coba lagi. Jika masalah berlanjut, gunakan /help.",
                parse_mode='Markdown'
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
