import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models.budget_planner import BudgetPlanner
from models.smart_alerts import SmartAlertSystem
from models.spending_analytics import SpendingAnalytics
from utils.date_utils import get_jakarta_now

logger = logging.getLogger(__name__)

# Initialize systems
budget_planner = BudgetPlanner()
alert_system = SmartAlertSystem(budget_planner)
analytics = SpendingAnalytics()

async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /budget command - Budget management main menu"""
    try:
        user_id = update.effective_user.id
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Set Budget Kategori", callback_data="budget_set"),
                InlineKeyboardButton("📊 Lihat Budget", callback_data="budget_view")
            ],
            [
                InlineKeyboardButton("📈 Budget Analytics", callback_data="budget_analytics"),
                InlineKeyboardButton("⚠️ Alert Settings", callback_data="budget_alerts")
            ],
            [
                InlineKeyboardButton("💡 Saran Budget", callback_data="budget_suggestions"),
                InlineKeyboardButton("🗑️ Hapus Budget", callback_data="budget_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "💰 *Budget Management*\n\n"
        message += "Kelola budget pengeluaran Anda per kategori:\n\n"
        message += "• 💰 *Set Budget*: Atur budget bulanan per kategori\n"
        message += "• 📊 *Lihat Budget*: Cek status budget saat ini\n"
        message += "• 📈 *Analytics*: Analisis performa budget\n"
        message += "• ⚠️ *Alerts*: Atur peringatan budget\n"
        message += "• 💡 *Saran*: Dapatkan rekomendasi budget\n"
        message += "• 🗑️ *Hapus*: Hapus budget kategori\n\n"
        message += "Pilih menu di bawah ini:"
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in budget_command: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.")

async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /insights command - Show spending insights and analytics"""
    try:
        user_id = update.effective_user.id
        
        # Check if user has enough data (This will be integrated with ExpenseTracker)
        # For now, show menu
        keyboard = [
            [
                InlineKeyboardButton("📊 Monthly Report", callback_data="insights_monthly"),
                InlineKeyboardButton("📈 Trend Analysis", callback_data="insights_trends")
            ],
            [
                InlineKeyboardButton("🎯 Category Insights", callback_data="insights_categories"),
                InlineKeyboardButton("⚡ Spending Velocity", callback_data="insights_velocity")
            ],
            [
                InlineKeyboardButton("🆚 Comparative Analysis", callback_data="insights_compare"),
                InlineKeyboardButton("🔍 Anomaly Detection", callback_data="insights_anomalies")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "📊 *Spending Insights & Analytics*\n\n"
        message += "Analisis mendalam tentang pola pengeluaran Anda:\n\n"
        message += "• 📊 *Monthly Report*: Laporan lengkap bulanan\n"
        message += "• 📈 *Trend Analysis*: Tren pengeluaran 6 bulan\n"
        message += "• 🎯 *Category Insights*: Analisis per kategori\n"
        message += "• ⚡ *Spending Velocity*: Kecepatan pengeluaran\n"
        message += "• 🆚 *Comparative*: Bandingkan dengan rata-rata\n"
        message += "• 🔍 *Anomaly Detection*: Deteksi pola tidak biasa\n\n"
        message += "Pilih jenis analisis:"
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in insights_command: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.")

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alerts command - Show smart alerts"""
    try:
        user_id = update.effective_user.id
        
        keyboard = [
            [
                InlineKeyboardButton("⚠️ Budget Alerts", callback_data="alerts_budget"),
                InlineKeyboardButton("🚨 Spending Alerts", callback_data="alerts_spending")
            ],
            [
                InlineKeyboardButton("📊 Daily Summary", callback_data="alerts_daily"),
                InlineKeyboardButton("📈 Weekly Review", callback_data="alerts_weekly")
            ],
            [
                InlineKeyboardButton("⚙️ Alert Settings", callback_data="alerts_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "⚠️ *Smart Alerts System*\n\n"
        message += "Sistem peringatan cerdas untuk pengeluaran Anda:\n\n"
        message += "• ⚠️ *Budget Alerts*: Peringatan budget limit\n"
        message += "• 🚨 *Spending Alerts*: Deteksi pengeluaran tidak biasa\n"
        message += "• 📊 *Daily Summary*: Ringkasan harian otomatis\n"
        message += "• 📈 *Weekly Review*: Review mingguan\n"
        message += "• ⚙️ *Settings*: Atur preferensi alert\n\n"
        message += "Pilih jenis alert:"
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in alerts_command: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.")

async def budget_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle budget-related callback queries"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "budget_set":
            await handle_budget_set(query, context)
        elif data == "budget_view":
            await handle_budget_view(query, context)
        elif data == "budget_analytics":
            await handle_budget_analytics(query, context)
        elif data == "budget_alerts":
            await handle_budget_alert_settings(query, context)
        elif data == "budget_suggestions":
            await handle_budget_suggestions(query, context)
        elif data == "budget_delete":
            await handle_budget_delete(query, context)
        elif data.startswith("set_budget_"):
            await handle_set_budget_category(query, context)
        elif data.startswith("delete_budget_"):
            await handle_delete_budget_category(query, context)
        elif data.startswith("insights_"):
            await handle_insights_callback(query, context)
        elif data.startswith("alerts_"):
            await handle_alerts_callback(query, context)
        
    except Exception as e:
        logger.error(f"Error in budget_callback_handler: {e}")
        await query.edit_message_text("❌ Terjadi kesalahan. Silakan coba lagi.")

async def handle_budget_set(query, context):
    """Handle budget setting"""
    categories = budget_planner.get_all_categories_from_config()
    
    keyboard = []
    # Create buttons for each category (2 per row)
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                category = categories[i + j]
                row.append(InlineKeyboardButton(
                    f"💰 {category}", 
                    callback_data=f"set_budget_{category.replace(' ', '_')}"
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "💰 *Set Budget per Kategori*\n\n"
    message += "Pilih kategori untuk mengatur budget bulanan:\n\n"
    for cat in categories:
        message += f"• {cat}\n"
    message += "\nKlik kategori di bawah ini:"
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_budget_view(query, context):
    """Handle budget viewing"""
    user_id = query.from_user.id
    user_budgets = budget_planner.get_user_budgets(user_id)
    
    if not user_budgets:
        message = "📊 *Budget Anda*\n\n"
        message += "Belum ada budget yang diatur.\n\n"
        message += "Gunakan '💰 Set Budget Kategori' untuk mengatur budget bulanan."
        
        keyboard = [[InlineKeyboardButton("💰 Set Budget", callback_data="budget_set")]]
        keyboard.append([InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")])
    else:
        message = "📊 *Budget Anda*\n\n"
        total_budget = 0
        
        for category, budget_info in user_budgets.items():
            amount = budget_info['amount']
            period = budget_info['period']
            alert_threshold = budget_info['alert_threshold']
            total_budget += amount
            
            # TODO: Get actual spending for this category from expense tracker
            # For now, we'll show the budget info
            message += f"💰 *{category}*\n"
            message += f"   Budget: Rp {amount:,} ({period})\n"
            message += f"   Alert: {alert_threshold}%\n\n"
        
        message += f"💳 *Total Budget: Rp {total_budget:,}*\n\n"
        message += "💡 Tip: Gunakan /insights untuk melihat analisis pengeluaran"
        
        keyboard = [
            [InlineKeyboardButton("📈 Lihat Analytics", callback_data="budget_analytics")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_budget_suggestions(query, context):
    """Handle budget suggestions"""
    suggestions = budget_planner.suggest_budget_amounts(query.from_user.id)
    
    message = "💡 *Saran Budget Bulanan*\n\n"
    message += "Berdasarkan pola pengeluaran umum di Indonesia:\n\n"
    
    total_suggested = 0
    for category, amount in suggestions.items():
        total_suggested += amount
        message += f"💰 {category}: Rp {amount:,}\n"
    
    message += f"\n💳 *Total Saran Budget: Rp {total_suggested:,}*\n\n"
    message += "📝 *Catatan:*\n"
    message += "• Sesuaikan dengan penghasilan dan kebutuhan Anda\n"
    message += "• Sisakan 20% untuk tabungan dan investasi\n"
    message += "• Review dan adjust setiap bulan\n\n"
    message += "💡 Mau set budget berdasarkan saran ini?"
    
    keyboard = [
        [InlineKeyboardButton("✅ Apply Suggestions", callback_data="apply_budget_suggestions")],
        [InlineKeyboardButton("💰 Set Custom Budget", callback_data="budget_set")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_insights_callback(query, context):
    """Handle insights callback queries"""
    data = query.data
    user_id = query.from_user.id
    
    # TODO: This will be integrated with actual expense data from ExpenseTracker
    # For now, show placeholder messages
    
    if data == "insights_monthly":
        message = "📊 *Monthly Insights Report*\n\n"
        message += "Fitur ini akan menampilkan:\n"
        message += "• Total pengeluaran bulan ini\n"
        message += "• Breakdown per kategori\n"
        message += "• Perbandingan dengan bulan lalu\n"
        message += "• Rekomendasi dan insight\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    elif data == "insights_trends":
        message = "📈 *Trend Analysis*\n\n"
        message += "Analisis tren pengeluaran 6 bulan terakhir:\n"
        message += "• Pola pengeluaran bulanan\n"
        message += "• Kategori yang meningkat/menurun\n"
        message += "• Prediksi pengeluaran bulan depan\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    elif data == "insights_categories":
        message = "🎯 *Category Insights*\n\n"
        message += "Analisis mendalam per kategori:\n"
        message += "• Pola pengeluaran per kategori\n"
        message += "• Frekuensi dan rata-rata transaksi\n"
        message += "• Perbandingan dengan periode lalu\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    elif data == "insights_velocity":
        message = "⚡ *Spending Velocity Analysis*\n\n"
        message += "Analisis kecepatan pengeluaran:\n"
        message += "• Frekuensi transaksi harian\n"
        message += "• Periode pengeluaran intensif\n"
        message += "• Pola waktu pengeluaran\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    else:
        message = "🔍 *Advanced Analytics*\n\n"
        message += "Fitur analisis lanjutan akan segera hadir!\n\n"
        message += "Silakan gunakan fitur basic analytics yang sudah tersedia."
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="insights_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_budget_analytics(query, context):
    """Handle budget analytics"""
    message = "📈 *Budget Analytics*\n\n"
    message += "Analisis performa budget Anda:\n"
    message += "• Realisasi vs target budget\n"
    message += "• Trend pengeluaran per kategori\n"
    message += "• Efisiensi budget\n"
    message += "• Proyeksi akhir bulan\n\n"
    message += "🔄 Fitur ini akan segera tersedia!"
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_budget_alert_settings(query, context):
    """Handle budget alert settings"""
    message = "⚙️ *Alert Settings*\n\n"
    message += "Pengaturan peringatan budget:\n"
    message += "• Threshold peringatan (default: 80%)\n"
    message += "• Jenis notifikasi\n"
    message += "• Frekuensi reminder\n"
    message += "• Kategori yang dimonitor\n\n"
    message += "🔄 Fitur ini akan segera tersedia!"
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_budget_delete(query, context):
    """Handle budget deletion"""
    user_id = query.from_user.id
    user_budgets = budget_planner.get_user_budgets(user_id)
    
    if not user_budgets:
        message = "🗑️ *Hapus Budget*\n\n"
        message += "Tidak ada budget yang dapat dihapus."
        keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")]]
    else:
        message = "🗑️ *Hapus Budget*\n\n"
        message += "Pilih kategori budget yang ingin dihapus:\n\n"
        
        keyboard = []
        for category in user_budgets.keys():
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {category}",
                callback_data=f"delete_budget_{category.replace(' ', '_')}"
            )])
        keyboard.append([InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_set_budget_category(query, context):
    """Handle setting budget for specific category"""
    category = query.data.replace("set_budget_", "").replace("_", " ")
    
    message = f"💰 *Set Budget: {category}*\n\n"
    message += f"Ketik budget bulanan untuk kategori {category}:\n\n"
    message += "Format: jumlah (contoh: 2000000)\n\n"
    message += "💡 Saran budget untuk kategori ini:\n"
    
    # Get suggestion for this category
    suggestions = budget_planner.suggest_budget_amounts(query.from_user.id)
    if category in suggestions:
        message += f"Rp {suggestions[category]:,}\n\n"
    else:
        message += "Sesuaikan dengan kebutuhan Anda\n\n"
    
    message += "Ketik angka budget atau /cancel untuk batal."
    
    # Store the category in user_data for the next message
    context.user_data['setting_budget_category'] = category
    
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="budget_set")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_delete_budget_category(query, context):
    """Handle deleting budget for specific category"""
    category = query.data.replace("delete_budget_", "").replace("_", " ")
    user_id = query.from_user.id
    
    success = budget_planner.remove_category_budget(user_id, category)
    
    if success:
        message = f"✅ *Budget Dihapus*\n\n"
        message += f"Budget untuk kategori {category} berhasil dihapus."
    else:
        message = f"❌ *Error*\n\n"
        message += f"Gagal menghapus budget untuk kategori {category}."
    
    keyboard = [
        [InlineKeyboardButton("📊 Lihat Budget", callback_data="budget_view")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="budget_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_alerts_callback(query, context):
    """Handle alerts callback queries"""
    data = query.data
    user_id = query.from_user.id
    
    # TODO: This will be integrated with actual alert system
    # For now, show placeholder messages
    
    if data == "alerts_budget":
        message = "⚠️ *Budget Alert Settings*\n\n"
        message += "Pengaturan alert budget:\n"
        message += "• Alert saat mencapai 80% budget\n"
        message += "• Peringatan saat melebihi budget\n"
        message += "• Notifikasi harian progress budget\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    elif data == "alerts_spending":
        message = "🚨 *Smart Spending Alerts*\n\n"
        message += "Deteksi otomatis:\n"
        message += "• Pengeluaran tidak biasa\n"
        message += "• Transaksi berulang cepat\n"
        message += "• Pengeluaran di waktu tidak biasa\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    elif data == "alerts_daily":
        message = "📊 *Daily Summary*\n\n"
        message += "Ringkasan harian otomatis:\n"
        message += "• Total pengeluaran hari ini\n"
        message += "• Kategori pengeluaran utama\n"
        message += "• Status budget\n\n"
        message += "🔄 Sedang dalam pengembangan..."
    
    else:
        message = "⚙️ *Alert System*\n\n"
        message += "Sistem alert cerdas akan segera hadir!\n\n"
        message += "Fitur ini akan membantu Anda mengontrol pengeluaran secara real-time."
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="alerts_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_budget_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle budget amount input from user"""
    try:
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Check if user is in budget setting mode
        if 'setting_budget_category' not in context.user_data:
            return
        
        category = context.user_data['setting_budget_category']
        
        # Validate input
        try:
            amount = int(message_text.replace('.', '').replace(',', '').replace(' ', ''))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await update.message.reply_text(
                "❌ Format tidak valid. Masukkan angka budget (contoh: 2000000)\n"
                "Atau ketik /cancel untuk batal."
            )
            return
        
        # Set budget
        success = budget_planner.set_category_budget(user_id, category, amount)
        
        if success:
            message = f"✅ *Budget Berhasil Diset*\n\n"
            message += f"Kategori: {category}\n"
            message += f"Budget bulanan: Rp {amount:,}\n"
            message += f"Alert threshold: 80% (Rp {amount * 0.8:,.0f})\n\n"
            message += "💡 Gunakan /budget untuk melihat semua budget Anda."
        else:
            message = "❌ Gagal menyimpan budget. Silakan coba lagi."
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
        # Clear the setting mode
        del context.user_data['setting_budget_category']
        
    except Exception as e:
        logger.error(f"Error in handle_budget_input: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.")
        # Clear the setting mode on error
        if 'setting_budget_category' in context.user_data:
            del context.user_data['setting_budget_category']
