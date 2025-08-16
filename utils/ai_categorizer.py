"""
AI-powered expense categorization using Google Gemini AI
"""

import logging
import google.generativeai as genai
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

class GeminiCategorizer:
    """AI categorizer using Google Gemini for expense classification"""
    
    def __init__(self):
        """Initialize Gemini AI client"""
        try:
            if Config.GEMINI_API_KEY:
                genai.configure(api_key=Config.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.enabled = True
                logger.info("✅ Gemini AI categorizer initialized successfully")
            else:
                self.enabled = False
                logger.warning("⚠️ GEMINI_API_KEY not found, falling back to rule-based categorization")
        except Exception as e:
            self.enabled = False
            logger.error(f"❌ Failed to initialize Gemini AI: {e}")
    
    def classify_category(self, description: str) -> str:
        """
        Classify expense description into category using Gemini AI
        
        Args:
            description: The expense description text
            
        Returns:
            Category name as string
        """
        if not self.enabled:
            return self._fallback_classify(description)
        
        try:
            # Create prompt for Gemini AI
            prompt = self._create_categorization_prompt(description)
            
            # Generate response from Gemini
            response = self.model.generate_content(prompt)
            
            # Extract category from response
            category = self._extract_category_from_response(response.text)
            
            logger.info(f"AI categorized '{description}' as '{category}'")
            return category
            
        except Exception as e:
            logger.error(f"Error in AI categorization: {e}")
            return self._fallback_classify(description)
    
    def _create_categorization_prompt(self, description: str) -> str:
        """Create prompt for Gemini AI categorization"""
        categories = [
            "Daily Needs",      # Kebutuhan sehari-hari (makanan, minuman, grocery)
            "Transportation",   # Transportasi (bensin, ojek, parkir, tol)  
            "Utilities",        # Utilitas (listrik, air, internet, pulsa)
            "Health",          # Kesehatan (obat, dokter, rumah sakit)
            "Urgent",          # Darurat (emergency, mendadak)
            "Entertainment",    # Hiburan (nonton, cafe, game, jalan-jalan)
            "Education",       # Pendidikan (buku, kursus, sekolah)
            "Shopping",        # Belanja (pakaian, elektronik, non-grocery)
            "Bills",           # Tagihan (cicilan, asuransi, pajak)
            "Other"            # Lainnya (jika tidak masuk kategori lain)
        ]
        
        prompt = f"""
Klasifikasikan pengeluaran berikut ke dalam salah satu kategori yang tersedia.

PENGELUARAN: "{description}"

KATEGORI YANG TERSEDIA:
{chr(10).join([f"- {cat}" for cat in categories])}

ATURAN:
1. Pilih HANYA SATU kategori yang paling sesuai
2. Jawab dengan nama kategori PERSIS seperti dalam daftar
3. Jika ragu antara 2 kategori, pilih yang lebih spesifik
4. Gunakan "Other" hanya jika benar-benar tidak cocok kategori lain

CONTOH:
- "beli beras 50rb" → Daily Needs
- "bensin motor" → Transportation  
- "bayar listrik" → Utilities
- "beli obat flu" → Health
- "nonton bioskop" → Entertainment

JAWABAN (hanya nama kategori):
        """
        
        return prompt
    
    def _extract_category_from_response(self, response_text: str) -> str:
        """Extract category name from Gemini response"""
        # Clean the response
        response = response_text.strip()
        
        # Valid categories
        valid_categories = [
            "Daily Needs", "Transportation", "Utilities", "Health", 
            "Urgent", "Entertainment", "Education", "Shopping", 
            "Bills", "Other"
        ]
        
        # Check if response matches any valid category
        for category in valid_categories:
            if category.lower() in response.lower():
                return category
        
        # If no exact match, try partial matching
        response_lower = response.lower()
        
        # Map common variations
        category_mapping = {
            "kebutuhan": "Daily Needs",
            "harian": "Daily Needs", 
            "makanan": "Daily Needs",
            "makan": "Daily Needs",
            "transportasi": "Transportation",
            "transport": "Transportation",
            "kendaraan": "Transportation",
            "utilitas": "Utilities",
            "listrik": "Utilities",
            "internet": "Utilities",
            "kesehatan": "Health",
            "medis": "Health",
            "obat": "Health",
            "darurat": "Urgent",
            "emergency": "Urgent",
            "hiburan": "Entertainment",
            "entertainment": "Entertainment",
            "pendidikan": "Education",
            "sekolah": "Education",
            "belanja": "Shopping",
            "shopping": "Shopping",
            "tagihan": "Bills",
            "bills": "Bills",
            "lainnya": "Other",
            "other": "Other"
        }
        
        for key, category in category_mapping.items():
            if key in response_lower:
                return category
        
        # Default fallback
        logger.warning(f"Could not extract valid category from response: {response}")
        return "Other"
    
    def _fallback_classify(self, description: str) -> str:
        """Fallback to rule-based classification when AI is not available"""
        description_lower = description.lower()
        
        # Simplified rule-based categories matching the AI categories
        categories = {
            'Daily Needs': ['makan', 'minum', 'beras', 'sayur', 'buah', 'daging', 'ikan', 'telur', 'susu', 'roti', 'nasi', 'lauk', 'snack', 'cemilan', 'grocery', 'belanja', 'pasar', 'supermarket'],
            'Transportation': ['bensin', 'ojek', 'grab', 'gojek', 'taxi', 'bus', 'kereta', 'parkir', 'tol', 'transport'],
            'Utilities': ['listrik', 'air', 'internet', 'wifi', 'pulsa', 'token', 'pln', 'pdam', 'indihome'],
            'Health': ['obat', 'dokter', 'rumah sakit', 'rs', 'klinik', 'vitamin', 'medical', 'kesehatan'],
            'Urgent': ['darurat', 'urgent', 'penting', 'mendadak', 'emergency'],
            'Entertainment': ['nonton', 'bioskop', 'game', 'musik', 'streaming', 'netflix', 'spotify', 'hiburan', 'jalan', 'mall', 'cafe', 'restaurant', 'film', 'nongkrong'],
            'Education': ['buku', 'kursus', 'sekolah', 'kuliah', 'les', 'pendidikan'],
            'Shopping': ['baju', 'sepatu', 'elektronik', 'hp', 'laptop', 'gadget'],
            'Bills': ['cicilan', 'asuransi', 'pajak', 'tagihan', 'iuran']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in description_lower:
                    logger.info(f"Fallback categorized '{description}' as '{category}' (keyword: {keyword})")
                    return category
        
        logger.info(f"Fallback categorized '{description}' as 'Other' (no matching keywords)")
        return 'Other'

# Global instance
categorizer = GeminiCategorizer()

def classify_category_ai(description: str) -> str:
    """
    Main function to classify expense category using AI
    
    Args:
        description: The expense description
        
    Returns:
        Category name
    """
    return categorizer.classify_category(description)
