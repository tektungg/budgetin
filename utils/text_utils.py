import re
from config import Config

def extract_amount(text):
    """Extract amount from text"""
    text_lower = text.lower().replace(',', '.')
    
    # First try to find numbers with suffixes (rb, ribu, k, juta)
    suffix_pattern = r'(\d+(?:[\.,]\d+)?)(?:\s*)(rb|ribu|k|juta)'
    match = re.search(suffix_pattern, text_lower)
    if match:
        amount_str, satuan = match.groups()
        # Clean up the amount string - remove dots used as thousand separators
        cleaned_amount = re.sub(r'\.(?=\d{3})', '', amount_str)  # Remove dots before 3 digits
        amount = float(cleaned_amount.replace(',', '.'))
        if satuan in ['rb', 'ribu', 'k']:
            amount *= 1000
        elif satuan == 'juta':
            amount *= 1000000
        return int(amount), match.start(), match.end()
    
    # Try to find numbers with dots (like 15.000.000)
    dot_pattern = r'(\d{1,3}(?:\.\d{3})+)(?!\.\d)'  # Matches 15.000.000 but not 1.5
    match = re.search(dot_pattern, text_lower)
    if match:
        amount_str = match.group(1)
        amount = int(amount_str.replace('.', ''))
        return amount, match.start(), match.end()
    
    # Try to find large plain numbers (4+ digits)
    plain_pattern = r'(\d{4,})'
    match = re.search(plain_pattern, text_lower)
    if match:
        amount_str = match.group(1)
        amount = int(amount_str)
        return amount, match.start(), match.end()
    
    return None, None, None

def classify_category(description):
    """
    Classify expense into category using AI
    
    This function now uses Gemini AI for intelligent categorization.
    Falls back to rule-based if AI is not available.
    """
    try:
        from utils.ai_categorizer import classify_category_ai
        return classify_category_ai(description)
    except ImportError as e:
        # Fallback to old rule-based method if AI dependencies not available
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"AI categorizer not available, using fallback: {e}")
        return _classify_category_fallback(description)

def _classify_category_fallback(description):
    """Fallback rule-based classification (legacy method)"""
    description_lower = description.lower()
    
    for category, keywords in Config.CATEGORIES.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category.replace('_', ' ').title()
    
    return 'Other'

def get_description(text, start_pos, end_pos):
    """Extract description by removing amount part"""
    before_amount = text[:start_pos].strip()
    after_amount = text[end_pos:].strip()
    
    description = (before_amount + ' ' + after_amount).strip()
    
    remove_words = ['beli', 'bayar', 'untuk', 'ke', 'di', 'dengan', 'pakai', 'rb', 'ribu', 'k', 'juta']
    words = description.split()
    cleaned_words = [word for word in words if word.lower() not in remove_words]
    
    return ' '.join(cleaned_words).strip() or 'Pengeluaran'
