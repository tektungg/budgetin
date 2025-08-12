# Expense Tracker Telegram Bot

Bot Telegram untuk mencatat pengeluaran yang otomatis tersimpan ke Google Sheets.

## Features

- 📝 Input pengeluaran dengan format bebas (contoh: "beli beras 50rb")
- 🤖 Deteksi otomatis jumlah uang dalam berbagai format
- 📂 Kategorisasi otomatis berdasarkan kata kunci
- 📊 Ringkasan bulanan dengan breakdown kategori
- 💾 Otomatis tersimpan ke Google Sheets
- 🔐 Multi-user support untuk keluarga

## Format Input yang Didukung

- `50rb`, `50 rb`, `50ribu`
- `50k`, `50 k` 
- `1.5juta`, `2juta`
- `50000` (angka biasa)
- `50.000` (dengan titik pemisah)

## Kategori Otomatis

- **Daily Needs**: makan, minum, beras, sayur, grocery, dll
- **Transportation**: bensin, ojek, grab, gojek, parkir, dll  
- **Utilities**: listrik, air, internet, pulsa, token, dll
- **Health**: obat, dokter, rumah sakit, vitamin, dll
- **Urgent**: darurat, urgent, mendadak, emergency
- **Entertainment**: nonton, game, musik, cafe, restaurant, dll

## Setup

### 1. Persiapan Bot Telegram
1. Chat @BotFather di Telegram
2. Ketik `/newbot` dan ikuti instruksi
3. Simpan token yang diberikan

### 2. Setup Google Sheets API
1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru atau gunakan yang ada
3. Enable Google Sheets API
4. Buat Service Account:
   - IAM & Admin → Service Accounts → Create Service Account
   - Buat key (JSON) dan download
5. Buat Google Spreadsheet baru
6. Share spreadsheet ke email service account dengan akses Editor

### 3. Deployment di Render

1. Fork/clone repository ini
2. Buat akun di [Render.com](https://render.com)
3. Connect repository ke Render
4. Pilih "Web Service"
5. Set environment variables:
   ```
   BOT_TOKEN=your_telegram_bot_token
   SPREADSHEET_ID=your_google_spreadsheet_id
   GOOGLE_CREDENTIALS_JSON=your_service_account_json_as_string
   ```
6. Deploy!

### 4. Set Webhook
Setelah deploy berhasil, set webhook URL di kode (baris 276):
```python
webhook_url=f"https://your-app-name.onrender.com/{bot_token}"
```

## Environment Variables

- `BOT_TOKEN`: Token dari @BotFather
- `SPREADSHEET_ID`: ID spreadsheet dari URL Google Sheets
- `GOOGLE_CREDENTIALS_JSON`: Seluruh isi file JSON credentials sebagai string

## Cara Mendapatkan Spreadsheet ID

Dari URL Google Sheets:
```
https://docs.google.com/spreadsheets/d/1ABC123DEF456GHI789/edit#gid=0
```
Ambil bagian: `1ABC123DEF456GHI789`

## Perintah Bot

- `/start` - Mulai menggunakan bot
- `/help` - Bantuan lengkap
- `/ringkasan` - Ringkasan pengeluaran bulan ini
- `/kategori` - Lihat semua kategori

## Struktur Google Sheets

Bot akan membuat worksheet "Pengeluaran" dengan kolom:
- Tanggal
- Waktu  
- Jumlah
- Keterangan
- Kategori
- User

## Local Development

1. Copy `.env.example` ke `.env`
2. Isi dengan credentials yang sesuai
3. Install dependencies: `pip install -r requirements.txt`
4. Jalankan: `python bot.py`

## Troubleshooting

- **Bot tidak respond**: Cek webhook URL dan token
- **Tidak bisa simpan ke Sheets**: Cek service account permissions
- **Kategori salah**: Tambahkan kata kunci di dictionary `categories`

## Contributing

Silakan buat issue atau pull request untuk improvement!
