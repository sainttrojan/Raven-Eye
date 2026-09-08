import re
from typing import Optional, Dict

class SmartParser:
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        if not text:
            return None
        # Match Egyptian numbers: 010, 011, 012, 015, optionally with spaces or +20
        phone_pattern = r'(?:\+?20\s*|0)?1[0125]\s*\d{2,3}\s*\d{3,4}\s*\d{2,3}'
        matches = re.findall(phone_pattern, text)
        for match in matches:
            clean_num = re.sub(r'\s+', '', match)
            # Ensure it looks like a valid length for an Egyptian mobile number
            if len(clean_num) == 11 and clean_num.startswith('01'):
                return clean_num
            elif len(clean_num) == 13 and clean_num.startswith('+201'):
                return clean_num
            elif len(clean_num) == 12 and clean_num.startswith('201'):
                return '+' + clean_num
        return None

    @staticmethod
    def extract_price(text: str) -> Optional[str]:
        if not text:
            return None
        # Extract numeric values followed by EGP, جنيه, or مليون
        price_pattern = r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s*(?:مليون|الف|ألف|ج\.م|جنيه|جنية|EGP))'
        matches = re.findall(price_pattern, text)
        if matches:
            return matches[0]
        return None

    @staticmethod
    def extract_area(text: str) -> Optional[str]:
        if not text:
            return None
        # Area extraction, e.g. "120m", "120 متر", "120م"
        area_pattern = r'(\d{2,4}\s*(?:متر|م٢|م2|م|sqm|m2))'
        matches = re.findall(area_pattern, text)
        if matches:
            return matches[0]
        return None

    @staticmethod
    def parse_text(text: str) -> Dict[str, Optional[str]]:
        return {
            'phone_number': SmartParser.extract_phone(text),
            'price': SmartParser.extract_price(text),
            'area': SmartParser.extract_area(text)
        }
