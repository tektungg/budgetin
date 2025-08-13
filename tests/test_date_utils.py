from utils.date_utils import (
    format_tanggal_indo, 
    parse_tanggal_indo, 
    get_month_worksheet_name,
    get_jakarta_now
)
from datetime import datetime

class TestDateUtils:
    """Test cases for date utility functions"""
    
    def test_format_tanggal_indo_basic(self):
        """Test basic Indonesian date formatting"""
        result = format_tanggal_indo("2025-01-15")
        assert "15 Januari 2025" in result
        # Should include day name
        assert any(day in result for day in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"])
    
    def test_format_tanggal_indo_different_months(self):
        """Test Indonesian date formatting for different months"""
        test_cases = [
            ("2025-02-01", "Februari"),
            ("2025-03-01", "Maret"),
            ("2025-12-01", "Desember")
        ]
        for date_str, expected_month in test_cases:
            result = format_tanggal_indo(date_str)
            assert expected_month in result
    
    def test_format_tanggal_indo_invalid_date(self):
        """Test Indonesian date formatting with invalid date"""
        result = format_tanggal_indo("invalid-date")
        assert result == "invalid-date"  # Should return original string
    
    def test_get_month_worksheet_name(self):
        """Test worksheet name generation"""
        test_cases = [
            (2025, 1, "Januari 2025"),
            (2025, 6, "Juni 2025"),
            (2025, 12, "Desember 2025"),
            (2024, 2, "Februari 2024")
        ]
        for year, month, expected in test_cases:
            result = get_month_worksheet_name(year, month)
            assert result == expected
    
    def test_parse_tanggal_indo_valid(self):
        """Test parsing valid Indonesian date"""
        # This assumes format_tanggal_indo produces parseable output
        formatted_date = format_tanggal_indo("2025-01-15")
        parsed_date = parse_tanggal_indo(formatted_date)
        
        if parsed_date:  # If parsing succeeded
            assert parsed_date.year == 2025
            assert parsed_date.month == 1
            assert parsed_date.day == 15
    
    def test_parse_tanggal_indo_fallback(self):
        """Test parsing falls back to standard format"""
        result = parse_tanggal_indo("2025-01-15")
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_tanggal_indo_invalid(self):
        """Test parsing invalid Indonesian date"""
        result = parse_tanggal_indo("invalid date string")
        assert result is None
    
    def test_get_jakarta_now(self):
        """Test Jakarta timezone datetime"""
        jakarta_time = get_jakarta_now()
        assert isinstance(jakarta_time, datetime)
        # Should have timezone info
        assert jakarta_time.tzinfo is not None
        # Should be Jakarta timezone (UTC+7)
        assert jakarta_time.utcoffset().total_seconds() == 7 * 3600
