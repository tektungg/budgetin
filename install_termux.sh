#!/data/data/com.termux/files/usr/bin/bash

# Script install untuk Termux Android
# Jalankan dengan: bash install_termux.sh

echo "🚀 Starting Termux setup for BudgetIn..."

# Update package manager
echo "📦 Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install build dependencies
echo "🔧 Installing build dependencies..."
pkg install -y rust
pkg install -y build-essential
pkg install -y libffi-dev
pkg install -y openssl-dev
pkg install -y python-dev
pkg install -y git

# Install Python dependencies step by step
echo "🐍 Installing Python dependencies..."

# Install basic dependencies first
echo "Installing basic dependencies..."
pip install --no-cache-dir python-dotenv==1.0.0
pip install --no-cache-dir pytz==2023.3
pip install --no-cache-dir tenacity==8.2.3
pip install --no-cache-dir structlog==23.2.0

# Install Flask
echo "Installing Flask..."
pip install --no-cache-dir flask==3.0.0

# Try to install cryptography with binary wheel
echo "Installing cryptography..."
pip install --only-binary=all --no-cache-dir "cryptography>=3.4.8,<42.0.0" || {
    echo "⚠️ Failed to install cryptography with binary wheel, trying older version..."
    pip install --no-cache-dir cryptography==3.4.8
}

# Install Google dependencies
echo "Installing Google dependencies..."
pip install --no-cache-dir google-auth==2.32.0
pip install --no-cache-dir google-auth-httplib2==0.2.0
pip install --no-cache-dir google-auth-oauthlib==1.2.1
pip install --no-cache-dir google-api-python-client==2.109.0
pip install --no-cache-dir gspread==6.0.2

# Install Gemini AI
echo "Installing Gemini AI..."
pip install --no-cache-dir google-generativeai==0.3.2

# Install Telegram Bot
echo "Installing Telegram Bot..."
pip install --no-cache-dir python-telegram-bot==20.7

echo "✅ Installation completed!"
echo "📝 Create your .env file based on env_example.txt"
echo "🎯 Run the bot with: python main.py"
