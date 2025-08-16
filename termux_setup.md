# Setup untuk Termux Android

## Masalah yang Ditemui
- Error saat install cryptography: "can't find Rust compiler"
- Tidak bisa upgrade pip di Termux: "Installing pip is forbidden"

## Solusi Step-by-Step

### 1. Install Rust Compiler
```bash
pkg install rust
```

### 2. Install Build Dependencies
```bash
pkg install build-essential
pkg install libffi-dev
pkg install openssl-dev
pkg install python-dev
```

### 3. Update Package Manager Termux
```bash
pkg update && pkg upgrade
```

### 4. Install Dependencies Secara Bertahap

#### Option A: Install dengan Pre-compiled Wheels
Coba install dependencies satu per satu dengan prioritas menggunakan pre-compiled wheels:

```bash
# Install dependencies yang tidak memerlukan kompilasi
pip install python-telegram-bot==20.7
pip install python-dotenv==1.0.0
pip install pytz==2023.3
pip install flask==3.0.0
pip install tenacity==8.2.3
pip install structlog==23.2.0

# Install Google dependencies
pip install google-generativeai==0.3.2
pip install gspread==6.0.2
pip install google-auth==2.32.0
pip install google-auth-oauthlib==1.2.1
pip install google-auth-httplib2==0.2.0
pip install google-api-python-client==2.109.0

# Install cryptography (yang sering bermasalah)
pip install --only-binary=all cryptography==41.0.7
```

#### Option B: Gunakan Versi Cryptography yang Lebih Lama
Jika masih bermasalah, gunakan versi cryptography yang lebih lama:
```bash
pip install cryptography==3.4.8
```

### 5. Alternative: Buat Requirements Khusus Termux
Buat file requirements_termux.txt dengan versi yang kompatibel untuk Termux.

## Tips Tambahan
1. Pastikan storage Termux tidak penuh
2. Restart Termux session jika ada error persistent
3. Gunakan `pip install --no-cache-dir` jika storage terbatas
4. Jika masih bermasalah, coba install di virtual environment
