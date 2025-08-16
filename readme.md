# 🤖 Budgetin Bot - Personal Finance Management System

A powerful Telegram bot for personal finance management, automatically saving your transactions to Google Sheets with OAuth 2.0 authentication. Equipped with AI-powered categorization, budget planning, spending analytics, and smart alerts for optimal financial control.

---

## ✨ Core Features

### 📝 Smart Expense Tracking

- **Natural Language Input**: Flexible input like "beli beras 50rb", "makan siang 25ribu"
- **AI-Powered Categorization**: Gemini AI for intelligent expense categorization
- **Flexible Amount Parsing**: Supports various formats (50rb, 1juta, 200.000, etc.)
- **Auto Description Detection**: Automatically extracts descriptions from input

### 💳 Advanced Balance Management

- **Real-time Balance Tracking**: Set initial balance, automatic tracking for each transaction
- **Smart Top-up System**: Top up balance anytime with interactive buttons
- **Balance History**: Complete balance history tracking in Google Sheets
- **Low Balance Alerts**: Automatic alerts when balance is low

### 🛡️ Personal Data Management

- **OAuth 2.0 Security**: Secure login with your personal Google Account
- **Personal Google Sheets**: Each user has their own Sheet in Drive
- **Monthly Worksheets**: Auto-generated worksheets per month (e.g., January 2025)
- **Real-time Sync**: Data saved instantly to Google Sheet with balance column

### 💰 Budget Planning & Management

- **Category-based Budgeting**: Set budgets per expense category
- **Budget Alerts**: Automatic alerts when nearing budget limits
- **Budget Analytics**: Analyze budget performance vs. realization
- **Smart Budget Suggestions**: Recommendations based on Indonesian spending patterns

### 📈 Advanced Analytics & Insights

- **Monthly Spending Reports**: Comprehensive monthly spending reports
- **Trend Analysis**: Analyze spending trends over the last 6 months
- **Category Insights**: In-depth analysis per expense category
- **Spending Velocity Analysis**: Detect spending speed patterns
- **Comparative Analysis**: Compare your spending with general averages
- **Spending Pattern Classification**: Classify spending patterns by category

### 🚨 Smart Alert System

- **Anomaly Detection**: Detect unusual expenses with AI
- **Budget Limit Alerts**: Automatic budget limit warnings
- **Spending Velocity Alerts**: Alerts for rapid spending
- **Weekend Spending Alerts**: Special alerts for weekend spending
- **Daily Summary Alerts**: Automatic daily summaries
- **Weekly Budget Review**: Weekly budget and spending reviews

### 🎯 User Experience

- **Interactive UI**: Button interface for quick feature access
- **Indonesian Localization**: Full Indonesian date and language support
- **Multi-Command Support**: 15+ commands for various features
- **Error Recovery**: Robust error handling with retry mechanisms
- **Performance Optimization**: Caching and timeout handling

---

## 💳 Balance Features

### 🎯 Balance Tracking Flow

1. **First Login**: Set initial balance (e.g., `1000000` for Rp 1 million)
2. **Record Expense**: Balance automatically decreases with each transaction
3. **View Balance**: Use `/balance` command or check monthly summary
4. **Top-up Balance**: Click "💰 Isi Saldo" button or use `/balance` command
5. **Monitor Daily**: See average daily spending in monthly summary

### 📱 Balance Response Examples

**After Recording Expense:**

```
✅ Pengeluaran berhasil dicatat!

💰 Jumlah: Rp 15,000
📝 Keterangan: beli sayur
📂 Kategori: Daily Needs
📅 Tanggal: Rabu, 14 Agustus 2025
📊 Worksheet: Agustus 2025

💳 Sisa Saldo: Rp 985,000

✨ Tersimpan ke Google Sheet pribadi Anda!

[📊 Buka Google Sheet] [💰 Isi Saldo] [📈 Lihat Ringkasan]
```

**Monthly Summary with Balance:**

```
📊 Ringkasan Pengeluaran Agustus 2025

💰 Total pengeluaran: Rp 150,000
💳 Saldo saat ini: Rp 850,000
📝 Jumlah transaksi: 10
📈 Pengeluaran rata-rata per hari: Rp 4,839

*Berdasarkan Kategori:*
• Daily Needs: Rp 75,000 (50.0%)
• Transportation: Rp 50,000 (33.3%)
• Utilities: Rp 25,000 (16.7%)
```

**Balance Command Response:**

```
💳 Saldo Anda Saat Ini

💰 Rp 850,000

💡 Tips:
• Gunakan tombol "Isi Saldo" untuk menambah saldo
• Saldo otomatis berkurang setiap pencatatan pengeluaran
• Lihat history saldo lengkap di Google Sheet Anda

[💰 Isi Saldo] [📊 Buka Google Sheet]
```

---

## 📊 Supported Input Formats

- `50rb`, `50 rb`, `50ribu`, `50k`
- `1.5juta`, `2juta`, `500rb`
- `50000`, `200000` (plain numbers, 4+ digits)
- `15.000.000` (with dot separator)
- `25,000` (with comma separator)

---

## 🏷️ AI-Powered Categorization

Now using **Gemini AI** for smarter and more accurate expense categorization:

### 🤖 Supported AI Categories

- **Daily Needs**: Daily essentials (food, drinks, groceries)
- **Transportation**: Transport (fuel, ride-hailing, parking, toll)
- **Utilities**: Utilities (electricity, water, internet, phone credit)
- **Health**: Health (medicine, doctor, hospital)
- **Urgent**: Emergency (urgent, sudden)
- **Entertainment**: Entertainment (movies, cafes, games, outings)
- **Education**: Education (books, courses, school)
- **Shopping**: Shopping (clothes, electronics, non-grocery)
- **Bills**: Bills (installments, insurance, taxes)
- **Other**: Others (if not in other categories)

### 🧠 AI Categorization Advantages

- **Context Aware**: Understands sentence context, not just keywords
- **Natural Language**: Understands natural Indonesian language
- **Learning**: Becomes more accurate over time
- **Fallback**: Automatically falls back to rule-based if AI is unavailable

### 📝 AI Categorization Examples

```
"beli beras di pasar" → Daily Needs
"isi bensin motor" → Transportation
"bayar tagihan listrik" → Utilities
"emergency ke dokter" → Health (urgent context)
"langganan Netflix" → Entertainment
"beli buku kuliah" → Education
"cicilan motor" → Bills
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Console account
- Telegram Bot Token
- Gemini AI API Key (optional but recommended)

### Installation & Setup

1. **Clone Repository**

```bash
git clone https://github.com/tektungg/budgetin.git
cd budgetin
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Environment Setup**
   Copy environment template:

```bash
cp env_example.txt .env
```

Edit `.env` with your credentials:

```env
# Required
BOT_TOKEN=your_telegram_bot_token
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
OAUTH_REDIRECT_URI=http://localhost:8080

# Optional but recommended for AI features
GEMINI_API_KEY=your_gemini_api_key

# Optional for production deployment
PUBLIC_URL=https://your-app.onrender.com
PORT=8080
```

4. **Run the Bot**

```bash
python main.py
```

---

## 🗂️ Project Structure

```
budgetin/
├── main.py                  # Entry point with clean architecture
├── config.py                # Centralized configuration
├── models/                  # Core business logic
│   ├── expense_tracker.py
│   ├── budget_planner.py
│   ├── smart_alerts.py
│   ├── spending_analytics.py
│   └── anomaly_detector.py
├── handlers/                # Request handlers
│   ├── auth_handlers.py
│   ├── command_handlers.py
│   ├── expense_handlers.py
│   └── budget_handlers.py
├── bot/                     # Bot initialization & setup
│   └── __init__.py
├── routes/                  # Flask route handlers
│   └── __init__.py
├── webhooks/                # Webhook processing
│   └── __init__.py
├── utils/                   # Utility functions
│   ├── text_utils.py
│   ├── date_utils.py
│   ├── ai_categorizer.py
│   ├── app_utils.py
│   ├── config_validator.py
│   ├── error_handlers.py
│   ├── performance_cache.py
│   └── timeout_wrapper.py
├── scripts/                 # Utility scripts
├── improvements/            # Feature improvements tracking
├── tests/                   # Comprehensive test suite
├── user_credentials.pkl     # Encrypted user data storage
├── user_budgets.pkl         # Budget data storage
└── Documentation files
```

---

## 📱 Bot Usage

### 🔐 Authentication Flow

1. User: `/login`
2. Bot: Provides Google OAuth link
3. User: Clicks link, grants permissions
4. User: Sends authorization code to bot
5. **Bot: Prompts for initial balance setup**
6. **User: Sets initial balance (e.g., "1000000" for Rp 1 million)**
7. Bot: Creates personal Google Sheet in user's Drive with balance column

### 💰 Balance Management

**Initial Setup:**

- Set your starting balance after first login
- Format: `1000000`, `1juta`, `500ribu`, `500rb`

**Top-up Balance:**

- Use "💰 Isi Saldo" button after recording expenses
- Or use `/balance` command anytime
- Same format as initial setup

### 💸 Recording Expenses

Simply send messages like:

- `beli sayur 15rb` → Balance automatically reduced
- `isi bensin 50k` → Shows remaining balance
- `makan siang warteg 12ribu` → Interactive buttons appear
- `bayar listrik 200.000` → Option to top-up balance

---

## 📝 Available Commands

### 🔐 Authentication Commands

- `/start` - Welcome message and setup info
- `/login` - Login with your Google Account
- `/logout` - Logout from your Google Account

### 💰 Balance & Expense Management

- `/balance` - View current balance and top up balance
- `/sheet` - Open your personal Google Sheet
- `/ringkasan` - Monthly expense summary with balance

### 💳 Budget Management Commands

- `/budget` - Budget management main menu with submenus:
  - 💰 Set Category Budget
  - 📊 View Current Budget
  - 📈 Budget Analytics & Performance
  - ⚠️ Alert Settings per category
  - 💡 Automatic Budget Suggestions
  - 🗑️ Delete Category Budget

### 📊 Analytics & Insights Commands

- `/insights` - Advanced spending analytics with submenus:
  - 📊 Monthly Report - Complete monthly report
  - 📈 Trend Analysis - 6-month spending trends
  - 🎯 Category Insights - Category analysis
  - ⚡ Spending Velocity - Spending speed analysis
  - 🆚 Comparative Analysis - Compare with average
  - 🔍 Anomaly Detection - Detect unusual patterns

### 🚨 Smart Alert System Commands

- `/alerts` - Smart alerts system with submenus:
  - ⚠️ Budget Alerts - Budget limit warnings
  - 🚨 Spending Alerts - Detect unusual spending
  - 📊 Daily Summary - Automatic daily summary
  - 📈 Weekly Review - Weekly review
  - ⚙️ Alert Settings - Set alert preferences

### 📋 Information Commands

- `/help` - Complete help for all features
- `/kategori` - View all available categories

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Made with ❤️ for comprehensive personal finance management in Indonesia 🇮🇩

**🎯 Total Features**: 50+ complete features for personal finance management  
**🤖 AI-Powered**: Gemini AI integration for smart categorization and anomaly detection  
**📊 Analytics-Ready**: Advanced spending analytics with deep insights  
**💳 Budget-Friendly**: Complete budget planning and alert system  
**🔒 Privacy-First**: Data stored in your personal Google Drive with OAuth security
