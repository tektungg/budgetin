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

    # Quick save operation - focus only on saving to Google Sheets
    success = False
    message = ""
    
    try:
        import threading
        import queue
        
        def run_quick_save():
            """Run quick expense save (without heavy smart features)"""
            try:
                # Use basic add_expense for speed
                result = expense_tracker.add_expense(user_id, amount, description, category)
                result_queue.put(('success', result))
            except Exception as e:
                result_queue.put(('error', str(e)))
        
        # Create queue for thread communication
        result_queue = queue.Queue()
        
        # Start operation in separate thread
        operation_thread = threading.Thread(target=run_quick_save)
        operation_thread.daemon = True
        operation_thread.start()
        
        # Wait for result with quick timeout (optimized for speed)
        from config import Config
        operation_thread.join(timeout=Config.EXPENSE_SAVE_TIMEOUT)
        
        if operation_thread.is_alive():
            # Thread is still running - timeout occurred
            raise TimeoutError(f"Quick save operation timed out after {Config.EXPENSE_SAVE_TIMEOUT} seconds")
        
        # Get result from queue
        if not result_queue.empty():
            result_type, result_data = result_queue.get()
            if result_type == 'success':
                success, message = result_data
            else:
                raise Exception(result_data)
        else:
            raise Exception("No result received from quick save operation")
        
        if success:
            # Get current date in Indonesian format for immediate response
            now = get_jakarta_now()
            tanggal_indo = format_tanggal_indo(now.strftime('%Y-%m-%d'))
            month_name = get_month_worksheet_name(now.year, now.month)
            current_balance = expense_tracker.get_user_balance(user_id)

            # Basic success response without smart features
            response = f"""
✅ *Pengeluaran berhasil dicatat!*

💰 *Jumlah:* Rp {amount:,}
📝 *Keterangan:* {description}
📂 *Kategori:* {category}
📅 *Tanggal:* {tanggal_indo}
💳 *Saldo tersisa:* Rp {current_balance:,}
📊 *Worksheet:* {month_name}
"""
            
            # Get quick smart insights (only budget and weekend alerts)
            try:
                quick_insights = expense_tracker.get_quick_smart_insights(user_id, amount, description, category)
                
                # Add quick alerts to response
                alerts = []
                if quick_insights.get('budget_alert'):
                    budget_alert = quick_insights['budget_alert']
                    alerts.append(f"\n{budget_alert['message']}")
                
                if quick_insights.get('weekend_alert'):
                    weekend_alert = quick_insights['weekend_alert']
                    alerts.append(f"\n{weekend_alert['message']}")
                
                if alerts:
                    response += "\n⚠️ *Smart Alerts:*"
                    for alert in alerts:
                        response += alert
                        
            except Exception as insights_error:
                logger.warning(f"Failed to get quick insights: {insights_error}")
            
            # Create basic interactive buttons
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
            try:
                budget_status = expense_tracker.get_budget_status_for_category(user_id, category)
                if budget_status.get('status') == 'no_budget':
                    keyboard.append([InlineKeyboardButton("💡 Set Budget", callback_data=f"suggest_budget_{category.replace(' ', '_')}")])
            except Exception:
                pass  # Skip if budget check fails
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await loading_msg.edit_text(
                f"❌ Gagal menyimpan: {message}\n\n"
                "Pastikan Anda sudah login dan Google Sheet Anda dapat diakses."
            )
    
    except TimeoutError:
        logger.warning(f"Quick save timed out after {Config.EXPENSE_SAVE_TIMEOUT}s for user {user_id}")
        
        # Retry message - still try to save but with simpler approach
        await loading_msg.edit_text(
            "⏳ *Proses lebih lama dari biasanya...*\n\n"
            "Sedang mencoba ulang...",
            parse_mode='Markdown'
        )
        
        # Second attempt with even simpler approach - just save the expense
        try:
            def run_simple_retry():
                """Run very simple retry operation"""
                try:
                    result = expense_tracker.add_expense(user_id, amount, description, category)
                    retry_queue.put(('success', result))
                except Exception as e:
                    retry_queue.put(('error', str(e)))
            
            # Create queue for retry thread communication
            retry_queue = queue.Queue()
            
            # Start retry operation in separate thread
            retry_thread = threading.Thread(target=run_simple_retry)
            retry_thread.daemon = True
            retry_thread.start()
            
            # Wait for result with retry timeout
            retry_thread.join(timeout=Config.EXPENSE_RETRY_TIMEOUT)
            
            if retry_thread.is_alive():
                # Second attempt also timed out
                raise TimeoutError(f"Second attempt also timed out after {Config.EXPENSE_RETRY_TIMEOUT} seconds")
            
            # Get result from retry queue
            if not retry_queue.empty():
                result_type, result_data = retry_queue.get()
                if result_type == 'success':
                    success, message = result_data
                else:
                    raise Exception(result_data)
            else:
                raise Exception("No result received from retry operation")
            
            if success:
                # Simple success handling for retry
                now = get_jakarta_now()
                tanggal_indo = format_tanggal_indo(now.strftime('%Y-%m-%d'))
                current_balance = expense_tracker.get_user_balance(user_id)

                response = f"""
✅ *Pengeluaran berhasil dicatat!* (percobaan ke-2)

💰 *Jumlah:* Rp {amount:,}
📝 *Keterangan:* {description}
📂 *Kategori:* {category}
📅 *Tanggal:* {tanggal_indo}
💳 *Saldo tersisa:* Rp {current_balance:,}
"""
                
                await loading_msg.edit_text(response, parse_mode='Markdown')
            else:
                await loading_msg.edit_text(
                    f"❌ Gagal menyimpan setelah 2 percobaan: {message}\n\n"
                    "Pastikan Anda sudah login dan Google Sheet Anda dapat diakses."
                )
        
        except TimeoutError:
            logger.error(f"Second attempt also timed out after {Config.EXPENSE_RETRY_TIMEOUT}s for user {user_id}")
            await loading_msg.edit_text(
                f"❌ *Operasi gagal setelah 2 percobaan (masing-masing {Config.EXPENSE_RETRY_TIMEOUT} detik)*\n\n"
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
    
    if query.data == "show_summary" or query.data == "summary_month":
        if not expense_tracker.is_user_authenticated(user_id):
            await query.message.reply_text(
                "❌ Anda perlu login terlebih dahulu. Gunakan /login"
            )
            return
            
        loading_message = await query.message.reply_text("⏳ Mengambil ringkasan...")
        
        try:
            summary = expense_tracker.get_monthly_summary(user_id)
            
            # Add button to open Google Sheet
            keyboard = []
            spreadsheet_id = expense_tracker.user_spreadsheets.get(str(user_id))
            if spreadsheet_id:
                keyboard.append([
                    InlineKeyboardButton("📊 Buka Google Sheet", 
                                       url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await loading_message.edit_text(summary, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in summary callback: {e}")
            await loading_message.edit_text("❌ Gagal mengambil ringkasan.")
        return
    
    if query.data == "check_balance":
        if not expense_tracker.is_user_authenticated(user_id):
            await query.message.reply_text(
                "❌ Anda perlu login terlebih dahulu. Gunakan /login"
            )
            return
            
        if not expense_tracker.has_balance_set(user_id):
            await query.message.reply_text(
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
        
        await query.message.reply_text(
            response,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    if query.data == "view_insights":
        # Get full smart insights for the latest expense
        loading_message = await query.edit_message_text("⏳ Menganalisis data pengeluaran...")
        
        try:
            # Get user's recent expenses to provide insights
            user_expenses = expense_tracker.get_user_expenses_data(user_id, days_back=30)
            
            if not user_expenses:
                await loading_message.edit_text(
                    "❌ Tidak ada data pengeluaran untuk dianalisis."
                )
                return
            
            # Get the latest expense for analysis
            latest_expense = user_expenses[-1]
            
            # Get smart insights without adding another expense
            smart_insights = expense_tracker.get_smart_insights_for_expense(
                str(user_id), 
                int(latest_expense.get('amount', 0)),
                latest_expense.get('description', ''),
                latest_expense.get('category', '')
            )
            
            if not smart_insights or not any(smart_insights.values()):
                await loading_message.edit_text(
                    "📊 *Smart Insights*\n\n"
                    "Tidak ada peringatan atau insight khusus untuk pengeluaran terbaru Anda.\n\n"
                    "✅ Pola pengeluaran Anda terlihat normal!",
                    parse_mode='Markdown'
                )
                return
            
            # Build insights response
            insights_response = "📊 *Smart Insights - Analisis Lengkap*\n\n"
            insights_found = False
            
            # Budget Alert
            if smart_insights.get('budget_alert'):
                budget_alert = smart_insights['budget_alert']
                insights_response += f"💰 *Budget Alert:*\n{budget_alert['message']}\n\n"
                insights_found = True
            
            # Anomaly Detection
            if smart_insights.get('anomaly_detection'):
                anomaly_report = smart_insights['anomaly_detection']
                if anomaly_report.get('has_anomalies'):
                    insights_response += "🔍 *Anomaly Detection:*\n"
                    for anomaly in anomaly_report['anomalies'][:3]:  # Limit to 3 anomalies
                        if anomaly.get('message'):
                            insights_response += f"• {anomaly['message']}\n"
                    insights_response += "\n"
                    insights_found = True
            
            # Spending Velocity Alert
            if smart_insights.get('spending_velocity_alert'):
                velocity_alert = smart_insights['spending_velocity_alert']
                insights_response += f"⚡ *Spending Velocity:*\n{velocity_alert['message']}\n\n"
                insights_found = True
            
            # Weekend Alert
            if smart_insights.get('weekend_alert'):
                weekend_alert = smart_insights['weekend_alert']
                insights_response += f"📅 *Weekend Alert:*\n{weekend_alert['message']}\n\n"
                insights_found = True
            
            if not insights_found:
                insights_response += "✅ Tidak ada peringatan khusus.\n\nPola pengeluaran Anda terlihat normal!"
            else:
                insights_response += "💡 *Tips:* Gunakan insights ini untuk mengelola keuangan lebih baik!"
            
            await loading_message.edit_text(insights_response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting full insights: {e}")
            await loading_message.edit_text(
                "❌ Gagal mengambil insights lengkap.\n\n"
                "Silakan coba lagi nanti.",
                parse_mode='Markdown'
            )
        return
    
    if query.data.startswith("budget_status_"):
        # Extract category from callback data
        category = query.data.replace("budget_status_", "").replace("_", " ")
        
        try:
            from models.budget_planner import BudgetPlanner
            budget_planner = BudgetPlanner()
            
            # Get budget status for this category
            budgets = budget_planner.get_user_budgets(user_id)
            if category in budgets:
                budget_amount = budgets[category]
                # Get spending for this category this month
                spent = expense_tracker.get_category_spending_this_month(user_id, category)
                remaining = budget_amount - spent
                percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
                
                status_emoji = "🟢" if percentage <= 70 else "🟡" if percentage <= 90 else "🔴"
                
                response = f"""
{status_emoji} *Budget Status: {category}*

💰 *Budget:* Rp {budget_amount:,}
💸 *Terpakai:* Rp {spent:,} ({percentage:.1f}%)
💵 *Tersisa:* Rp {remaining:,}

{'✅ Anda masih dalam batas budget!' if percentage <= 100 else '⚠️ Budget sudah terlampaui!'}
                """
            else:
                response = f"❌ Budget untuk kategori '{category}' belum diatur.\n\nGunakan /budget untuk mengatur budget."
                
            await query.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in budget_status callback: {e}")
            await query.message.reply_text("❌ Gagal mengambil status budget.")
        return
    
    if query.data.startswith("suggest_budget_"):
        # Extract category from callback data
        category = query.data.replace("suggest_budget_", "").replace("_", " ")
        
        try:
            from models.budget_planner import BudgetPlanner
            budget_planner = BudgetPlanner()
            
            # Get budget suggestion
            suggestion = budget_planner.suggest_budget_for_category(user_id, category, expense_tracker)
            
            response = f"""
💡 *Saran Budget: {category}*

{suggestion}

Gunakan /budget untuk mengatur budget Anda.
            """
            await query.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in suggest_budget callback: {e}")
            await query.message.reply_text("❌ Gagal memberikan saran budget.")
        return
    
    if query.data == "show_help":
        from handlers.command_handlers import help_command
        await help_command(query, context)
        return
    
    # If no specific handler found, log it
    logger.warning(f"Unhandled callback data: {query.data}")
    await query.message.reply_text("❌ Fungsi ini sedang dalam pengembangan.")

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
