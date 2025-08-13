#!/usr/bin/env python3
"""
Simple test runner untuk menjalankan tests tanpa pytest
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_text_utils():
    """Test text utility functions"""
    print("Testing text_utils...")
    
    from utils.text_utils import extract_amount, classify_category, get_description
    
    # Test extract_amount
    test_cases = [
        ("beli beras 50rb", 50000),
        ("makan siang 25ribu", 25000),
        ("bensin 30k", 30000),
        ("cicilan 2juta", 2000000),
        ("laptop 15.000.000", 15000000),
    ]
    
    for text, expected in test_cases:
        amount, _, _ = extract_amount(text)
        assert amount == expected, f"Expected {expected}, got {amount} for '{text}'"
        print(f"✅ extract_amount('{text}') = {amount}")
    
    # Test classify_category
    category_tests = [
        ("beli beras", "Daily Needs"),
        ("isi bensin", "Transportation"),
        ("bayar listrik", "Utilities"),
        ("beli obat", "Health"),
        ("nonton film", "Entertainment"),
        ("sesuatu yang aneh", "Other")
    ]
    
    for text, expected in category_tests:
        category = classify_category(text)
        assert category == expected, f"Expected '{expected}', got '{category}' for '{text}'"
        print(f"✅ classify_category('{text}') = '{category}'")
    
    print("✅ All text_utils tests passed!\n")

def test_date_utils():
    """Test date utility functions"""
    print("Testing date_utils...")
    
    from utils.date_utils import get_month_worksheet_name, format_tanggal_indo, get_jakarta_now
    from datetime import datetime
    
    # Test get_month_worksheet_name
    test_cases = [
        (2025, 1, "Januari 2025"),
        (2025, 6, "Juni 2025"),
        (2025, 12, "Desember 2025"),
    ]
    
    for year, month, expected in test_cases:
        result = get_month_worksheet_name(year, month)
        assert result == expected, f"Expected '{expected}', got '{result}'"
        print(f"✅ get_month_worksheet_name({year}, {month}) = '{result}'")
    
    # Test format_tanggal_indo
    result = format_tanggal_indo("2025-01-15")
    assert "15 Januari 2025" in result
    print(f"✅ format_tanggal_indo('2025-01-15') = '{result}'")
    
    # Test get_jakarta_now
    jakarta_time = get_jakarta_now()
    assert isinstance(jakarta_time, datetime)
    assert jakarta_time.tzinfo is not None
    print(f"✅ get_jakarta_now() = {jakarta_time}")
    
    print("✅ All date_utils tests passed!\n")

def test_config():
    """Test configuration loading"""
    print("Testing config...")
    
    from config import Config
    
    # Test that Config class has required attributes
    required_attrs = ['CATEGORIES', 'OAUTH_SCOPES', 'USER_CREDENTIALS_FILE']
    for attr in required_attrs:
        assert hasattr(Config, attr), f"Config missing attribute: {attr}"
        print(f"✅ Config.{attr} exists")
    
    # Test categories structure
    assert isinstance(Config.CATEGORIES, dict)
    assert len(Config.CATEGORIES) > 0
    print(f"✅ Config.CATEGORIES has {len(Config.CATEGORIES)} categories")
    
    print("✅ All config tests passed!\n")

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    import_tests = [
        "config",
        "utils.text_utils",
        "utils.date_utils", 
        "models.expense_tracker",
        "handlers.command_handlers",
        "handlers.auth_handlers",
        "handlers.expense_handlers"
    ]
    
    for module in import_tests:
        try:
            __import__(module)
            print(f"✅ Successfully imported {module}")
        except ImportError as e:
            print(f"❌ Failed to import {module}: {e}")
            return False
    
    print("✅ All imports successful!\n")
    return True

def main():
    """Run all tests"""
    print("🧪 Running Budgetin Bot Tests\n" + "="*50 + "\n")
    
    try:
        test_imports()
        test_config()
        test_text_utils()
        test_date_utils()
        
        print("🎉 All tests passed! Your refactored code is working correctly.")
        return True
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
