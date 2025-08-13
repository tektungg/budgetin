from utils.text_utils import extract_amount, classify_category, get_description

class TestTextUtils:
    """Test cases for text utility functions"""
    
    def test_extract_amount_with_ribu(self):
        """Test amount extraction with 'ribu' suffix"""
        amount, start, end = extract_amount("beli beras 50ribu")
        assert amount == 50000
        assert isinstance(start, int)
        assert isinstance(end, int)
    
    def test_extract_amount_with_rb(self):
        """Test amount extraction with 'rb' suffix"""
        amount, start, end = extract_amount("makan siang 25rb")
        assert amount == 25000
    
    def test_extract_amount_with_k(self):
        """Test amount extraction with 'k' suffix"""
        amount, start, end = extract_amount("bensin motor 30k")
        assert amount == 30000
    
    def test_extract_amount_with_juta(self):
        """Test amount extraction with 'juta' suffix"""
        amount, start, end = extract_amount("bayar cicilan 2juta")
        assert amount == 2000000
    
    def test_extract_amount_with_decimal_juta(self):
        """Test amount extraction with decimal juta"""
        amount, start, end = extract_amount("beli motor 1.5juta")
        assert amount == 1500000
    
    def test_extract_amount_plain_number(self):
        """Test amount extraction with plain numbers"""
        amount, start, end = extract_amount("bayar listrik 200000")
        assert amount == 200000
    
    def test_extract_amount_with_dots(self):
        """Test amount extraction with dot separators"""
        amount, start, end = extract_amount("beli laptop 15.000.000")
        assert amount == 15000000
    
    def test_extract_amount_no_amount(self):
        """Test when no amount is found"""
        amount, start, end = extract_amount("hanya text biasa tanpa angka")
        assert amount is None
        assert start is None
        assert end is None
    
    def test_extract_amount_small_number(self):
        """Test with numbers too small (less than 3 digits)"""
        amount, start, end = extract_amount("beli permen 50")
        assert amount is None  # Should not detect numbers < 1000 unless with suffix
    
    def test_classify_category_daily_needs(self):
        """Test category classification for daily needs"""
        assert classify_category("beli beras di pasar") == "Daily Needs"
        assert classify_category("makan siang warteg") == "Daily Needs"
        assert classify_category("belanja grocery") == "Daily Needs"
    
    def test_classify_category_transportation(self):
        """Test category classification for transportation"""
        assert classify_category("isi bensin motor") == "Transportation"
        assert classify_category("naik grab ke mall") == "Transportation"
        assert classify_category("bayar parkir") == "Transportation"
    
    def test_classify_category_utilities(self):
        """Test category classification for utilities"""
        assert classify_category("bayar listrik bulan ini") == "Utilities"
        assert classify_category("beli pulsa telkomsel") == "Utilities"
        assert classify_category("bayar internet indihome") == "Utilities"
    
    def test_classify_category_health(self):
        """Test category classification for health"""
        assert classify_category("beli obat di apotek") == "Health"
        assert classify_category("periksa ke dokter") == "Health"
        assert classify_category("vitamin C") == "Health"
    
    def test_classify_category_urgent(self):
        """Test category classification for urgent"""
        assert classify_category("dana darurat untuk emergency") == "Urgent"
        assert classify_category("kebutuhan mendadak") == "Urgent"
    
    def test_classify_category_entertainment(self):
        """Test category classification for entertainment"""
        assert classify_category("nonton film di bioskop") == "Entertainment"
        assert classify_category("main game online") == "Entertainment"
        assert classify_category("nongkrong di cafe") == "Entertainment"
    
    def test_classify_category_other(self):
        """Test category classification for unrecognized items"""
        assert classify_category("sesuatu yang tidak dikenal") == "Other"
    
    def test_get_description_removes_amount(self):
        """Test description extraction removes amount part"""
        desc = get_description("beli beras 50rb di pasar", 11, 15)
        assert "50rb" not in desc
        assert "beras" in desc or "pasar" in desc
    
    def test_get_description_removes_common_words(self):
        """Test description removes common words like 'beli', 'bayar'"""
        desc = get_description("beli sayur bayam untuk masak", 0, 0)
        # Should remove 'beli' and 'untuk'
        words = desc.lower().split()
        assert "beli" not in words
        assert "untuk" not in words
        assert "sayur" in desc.lower()
    
    def test_get_description_fallback(self):
        """Test description fallback when nothing left"""
        desc = get_description("beli untuk bayar", 0, 0)
        assert desc == "Pengeluaran"  # Default fallback
