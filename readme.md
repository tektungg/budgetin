# 🤖 Budgetin Bot - Personal Expense Tracker

Bot Telegram untuk mencatat pengeluaran pribadi yang otomatis tersimpan ke Google Sheets dengan OAuth 2.0 authentication. Setiap user memiliki Google Sheet pribadi di Drive mereka sendiri dengan fitur tracking saldo otomatis.

## ✨ Features

- 📝 **Smart Input**: Format bebas seperti "beli beras 50rb", "makan siang 25ribu"
- 🤖 **Auto Detection**: Deteksi jumlah uang dan kategorisasi otomatis
- 💳 **Balance Tracking**: Set saldo awal, tracking otomatis, dan top-up kapan saja
- 🔐 **OAuth 2.0**: Login dengan Google Account pribadi user
- 📊 **Personal Sheets**: Setiap user punya Google Sheet di Drive sendiri dengan kolom saldo
- 📅 **Monthly Worksheets**: Worksheet terpisah per bulan (Januari 2025, Februari 2025, dll)
- 📈 **Smart Analytics**: Ringkasan bulanan dengan saldo dan pengeluaran rata-rata per hari
- 💳 **Interactive Buttons**: Button untuk isi saldo dan akses cepat fitur
- 🌍 **Indonesian Localized**: Format tanggal dan bahasa Indonesia

## 💳 Balance Features

### 🎯 Balance Tracking Flow

1. **First Login**: Set initial balance (e.g., `1000000` for Rp 1 million)
2. **Record Expense**: Balance automatically reduces with each transaction
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

## 📊 Format Input yang Didukung

- `50rb`, `50 rb`, `50ribu`, `50k`
- `1.5juta`, `2juta`, `500rb`
- `50000`, `200000` (angka biasa 4+ digit)
- `15.000.000` (dengan pemisah titik)
- `25,000` (dengan koma)

## 🏷️ Kategori Otomatis

- **Daily Needs**: makan, minum, beras, sayur, buah, grocery, belanja, pasar
- **Transportation**: bensin, ojek, grab, gojek, taxi, bus, parkir, tol
- **Utilities**: listrik, air, internet, wifi, pulsa, token, pln, indihome
- **Health**: obat, dokter, rumah sakit, klinik, vitamin, medical
- **Urgent**: darurat, urgent, mendadak, emergency
- **Entertainment**: nonton, bioskop, game, musik, cafe, restaurant, netflix

## 🚀 Quick Start

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
BOT_TOKEN=your_telegram_bot_token
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
OAUTH_REDIRECT_URI=http://localhost:8080
```

4. **Run the Bot**

```bash
python main.py
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or use existing
3. Enable **Google Sheets API** and **Google Drive API**
4. Create **OAuth 2.0 Client ID**:
   - Application type: **Desktop application**
   - Download JSON and get `client_id` and `client_secret`

### Telegram Bot Setup

1. Chat [@BotFather](https://t.me/BotFather) on Telegram
2. Create new bot: `/newbot`
3. Save the token provided

## 🏗️ Architecture

```
budgetin/
├── 🚀 main.py                  # Entry point (138 lines)
├── ⚙️ config.py                # Centralized configuration
├── 📁 models/
│   └── expense_tracker.py      # Core business logic
├── 📁 handlers/
│   ├── auth_handlers.py        # OAuth authentication
│   ├── command_handlers.py     # Bot commands (/start, /help)
│   └── expense_handlers.py     # Expense processing
├── 📁 utils/
│   ├── text_utils.py          # Text parsing & categorization
│   └── date_utils.py          # Indonesian date utilities
├── 📁 tests/
│   ├── test_text_utils.py     # Text utility tests
│   └── test_date_utils.py     # Date utility tests
├── 🧪 run_tests.py            # Test runner
└── 📖 Documentation files...
```

## 🧪 Testing

### Run All Tests

```bash
python run_tests.py
```

### Example Test Output

```
🧪 Running Budgetin Bot Tests
==================================================

✅ Successfully imported all modules
✅ extract_amount('beli beras 50rb') = 50000
✅ extract_amount('laptop 15.000.000') = 15000000
✅ classify_category('beli beras') = 'Daily Needs'
✅ get_month_worksheet_name(2025, 1) = 'Januari 2025'

🎉 All tests passed! Your refactored code is working correctly.
```

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

### 📊 Available Commands

- `/start` - Welcome message dan setup info
- `/login` - Login dengan Google Account
- `/logout` - Logout dari Google Account  
- `/balance` - Lihat saldo saat ini dan isi saldo
- `/help` - Bantuan lengkap semua fitur
- `/ringkasan` - Ringkasan pengeluaran bulan ini dengan saldo
- `/kategori` - Lihat semua kategori yang tersedia
- `/sheet` - Buka Google Sheet pribadi Anda

## 🗄️ Data Structure

### Google Sheet Organization

- **📁 Folder**: "Budgetin" di Google Drive user
- **📊 Sheet**: "Budgetin - [Username]"
- **📋 Worksheets**: Per bulan (Januari 2025, Februari 2025, dll)
- **💰 Balance**: Tracked in memory and persisted to local file

### Local Data Storage

- **📄 user_credentials.pkl**: Stores OAuth tokens, spreadsheet IDs, dan user balances
- **🔐 Format**: Encrypted pickle file containing:
  ```python
  {
      'credentials': {user_id: oauth_credentials},
      'spreadsheets': {user_id: spreadsheet_id}, 
      'balances': {user_id: current_balance}
  }
  ```

### Worksheet Columns

| Column     | Description              | Example               |
| ---------- | ------------------------ | --------------------- |
| Tanggal    | Indonesian date format   | Rabu, 15 Januari 2025 |
| Waktu      | Time of entry            | 14:30:25              |
| Jumlah     | Amount in IDR            | 50000                 |
| Keterangan | Description              | sayur bayam           |
| Kategori   | Auto-classified category | Daily Needs           |
| Notes      | Additional notes (empty) | -                     |
| **Saldo**  | **Remaining balance**    | **950000**            |

## 🚀 Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py
```

### Production Deployment (Render/Heroku/VPS)

1. **Environment Variables**:

```env
BOT_TOKEN=your_telegram_bot_token
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
PORT=8080
PUBLIC_URL=https://your-app.onrender.com  # optional
```

2. **Webhook Setup**: Bot auto-configures webhook based on environment

3. **Deploy**:

```bash
# For Render - connect your repo and auto-deploy
# For VPS
git clone your-repo
cd budgetin
pip install -r requirements.txt
python main_refactored.py
```

## 🔧 Development

### Adding New Categories

Edit `config.py`:

```python
CATEGORIES = {
    'your_category': ['keyword1', 'keyword2', 'keyword3']
}
```

### Adding New Commands

1. Add handler in `handlers/command_handlers.py`
2. Register in `main_refactored.py`
3. Add tests in `tests/`

### Running Tests

```bash
# Run all tests
python run_tests.py

# Or with pytest (if installed)
pytest tests/
```

## 📖 Documentation

This README contains all the documentation you need to get started with Budgetin Bot.

## 🐛 Troubleshooting

### Common Issues

**Bot tidak respond**

- ✅ Check BOT_TOKEN in environment
- ✅ Verify webhook URL (check logs)
- ✅ Ensure bot is running and accessible

**OAuth login gagal**

- ✅ Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
- ✅ Verify OAuth redirect URI configuration
- ✅ Ensure Google Sheets + Drive APIs enabled

**Gagal buat/akses Google Sheet**

- ✅ Check user granted proper permissions
- ✅ Verify Google APIs are enabled
- ✅ Check user has Google Drive space

**Balance/Saldo tidak tersimpan**

- ✅ Ensure user completed initial balance setup after login
- ✅ Check user_credentials.pkl file exists and readable
- ✅ Verify balance format (numbers only, or with rb/ribu/juta suffix)
- ✅ Test with `/balance` command to check current balance

**Saldo tidak berkurang setelah pencatatan**

- ✅ Check balance was set initially (`/balance` to verify)
- ✅ Ensure expense amount is detected correctly
- ✅ Verify Google Sheet has 7 columns including "Saldo"

**Amount parsing tidak akurat**

- ✅ Check supported formats in documentation
- ✅ Use 4+ digit numbers or add suffix (rb, k, juta)
- ✅ Test with `python -c "from utils.text_utils import extract_amount; print(extract_amount('your text'))"`

### Debug Mode

```bash
# Enable debug logging
export PYTHONPATH="."
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from utils.text_utils import extract_amount
print(extract_amount('your problematic text'))
"
```

## 🤝 Contributing

Contributions are welcome! Please:

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Add tests** for new functionality
4. **Ensure tests pass**: `python run_tests.py`
5. **Commit** changes: `git commit -m 'Add amazing feature'`
6. **Push** to branch: `git push origin feature/amazing-feature`
7. **Open** Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/budgetin.git
cd budgetin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements_dev.txt

# Run tests
python run_tests.py
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Telegram Bot API
- Google Sheets API
- Google OAuth 2.0
- All contributors and users

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/tektungg/budgetin/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/tektungg/budgetin/discussions)  
- 📧 **Email**: Create an issue for support
- 💰 **Balance Issues**: Check troubleshooting section first

---

Made with ❤️ for personal expense tracking with balance management in Indonesia 🇮🇩
