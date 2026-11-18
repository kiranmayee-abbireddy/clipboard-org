# src/backend/categorizer.py
import re
import json
from typing import Dict

class ContentCategorizer:
    """Categorize clipboard content using pattern analysis and heuristics"""
    
    # URL patterns
    URL_STRICT_PATTERN = re.compile(
        r'^(https?://|ftp://|www\.)[^\s/$.?#].[^\s]*$', re.IGNORECASE
    )
    URL_FIND_PATTERN = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    )
    
    # Email patterns
    EMAIL_STRICT_PATTERN = re.compile(
        r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    )
    EMAIL_FIND_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    )
    
    # Phone patterns - standard international and domestic formats
    PHONE_CHARS_PATTERN = re.compile(r'^\+?[0-9\s\-\.\(\)]{7,25}$')
    PHONE_FIND_PATTERN = re.compile(
        r'(\+\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}'
    )
    
    # Code patterns - covers major programming languages and formats
    CODE_PATTERNS = [
        # Functions / declarations
        re.compile(r'\b(def|class|function|func|fn|pub fn|interface|enum|struct|type)\s+[A-Za-z_]\w*'),
        # Imports and modules
        re.compile(r'\b(import|from\s+\w+\s+import|require\(|#include|using\s+namespace|package\s+\w+)'),
        # Control structures
        re.compile(r'\b(if|elif|else if|for|while|switch|case|catch|except|finally)\s*[\(\{:]'),
        # Variable declarations (JS/TS, Go, Rust, C)
        re.compile(r'\b(const|let|var|val)\s+[A-Za-z_]\w*\s*='),
        # Return / throw statements
        re.compile(r'\b(return\s+[^\n;]+|throw\s+new\s+\w+|yield\s+)'),
        # Common methods / console
        re.compile(r'\b(console\.(log|error|warn)|print\(|fmt\.Print|System\.out\.print)'),
        # OOP / C++ / Java modifiers
        re.compile(r'\b(public|private|protected)\s+(static\s+)?(void|int|string|boolean|[A-Z]\w*)\s+\w+'),
        # Syntax markers: semicolons/braces at line ends, arrow functions, Python decorators
        re.compile(r'[{};]\s*$|=>|\bself\.\w+|\bthis\.\w+|@\w+\('),
    ]
    
    # SQL pattern
    SQL_PATTERN = re.compile(
        r'\b(SELECT\s+.*?\s+FROM|INSERT\s+INTO\s+\w+|UPDATE\s+\w+\s+SET|DELETE\s+FROM\s+\w+|CREATE\s+TABLE)\b',
        re.IGNORECASE
    )
    
    # HTML / XML pattern
    HTML_PATTERN = re.compile(
        r'<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>|<\!DOCTYPE\s+html>',
        re.IGNORECASE
    )
    
    # Password / Token heuristics
    PASSWORD_KEYWORDS = {'password', 'passwd', 'pwd', 'passphrase', 'secret', 'api_key', 'apikey', 'auth_token', 'access_token'}
    TOKEN_PREFIXES = ('bearer ', 'ghp_', 'gho_', 'glpat-', 'sk-', 'xoxb-', 'xoxp-', 'eyJh', 'eyBi')
    
    @staticmethod
    def categorize(content: str) -> str:
        """
        Categorize content and return category name:
        'url', 'email', 'phone', 'password', 'code', or 'text'
        """
        if not content:
            return 'text'
        
        trimmed = content.strip()
        if not trimmed:
            return 'text'
        
        content_lower = trimmed.lower()
        length = len(trimmed)
        
        # 1. URL Detection
        if ContentCategorizer.URL_STRICT_PATTERN.match(trimmed):
            return 'url'
        # If content has URL and is short or mostly URL
        url_match = ContentCategorizer.URL_FIND_PATTERN.search(trimmed)
        if url_match and (length <= 150 or (len(url_match.group(0)) / length) > 0.5):
            return 'url'
        
        # 2. Email Detection
        if ContentCategorizer.EMAIL_STRICT_PATTERN.match(trimmed):
            return 'email'
        email_match = ContentCategorizer.EMAIL_FIND_PATTERN.search(trimmed)
        if email_match and (length <= 100 or (len(email_match.group(0)) / length) > 0.5):
            return 'email'
        
        # 3. Password / API Key / Secret Detection (Checked before phone to prevent token misclassification)
        # Check token prefixes
        if any(trimmed.startswith(prefix) or trimmed.lower().startswith(prefix) for prefix in ContentCategorizer.TOKEN_PREFIXES):
            return 'password'
            
        # Check keyword in short snippet (e.g. "password: secret123", "apiKey = xxx")
        if length <= 64:
            for kw in ContentCategorizer.PASSWORD_KEYWORDS:
                if kw in content_lower:
                    return 'password'

        # 4. Phone Number Detection (Phone numbers must not contain alphabetic characters)
        has_letters = any(c.isalpha() for c in trimmed)
        if not has_letters:
            digit_count = sum(c.isdigit() for c in trimmed)
            if 7 <= digit_count <= 15 and ContentCategorizer.PHONE_CHARS_PATTERN.match(trimmed):
                return 'phone'
            phone_match = ContentCategorizer.PHONE_FIND_PATTERN.search(trimmed)
            if phone_match and length <= 30 and 7 <= digit_count <= 15:
                return 'phone'
        
        # 5. Code Detection
        # JSON detection
        if (trimmed.startswith('{') and trimmed.endswith('}')) or (trimmed.startswith('[') and trimmed.endswith(']')):
            if length > 10:
                try:
                    json.loads(trimmed)
                    return 'code'
                except Exception:
                    pass
        
        # SQL detection
        if ContentCategorizer.SQL_PATTERN.search(trimmed):
            return 'code'
            
        # HTML/XML tags detection
        if len(ContentCategorizer.HTML_PATTERN.findall(trimmed)) >= 2 or trimmed.startswith('<!DOCTYPE html>'):
            return 'code'
            
        # Programming language patterns
        code_matches = sum(1 for pattern in ContentCategorizer.CODE_PATTERNS if pattern.search(trimmed))
        if code_matches >= 2 or (length > 30 and code_matches >= 1 and ('\n' in trimmed or '\t' in trimmed or '    ' in trimmed)):
            return 'code'
        if code_matches >= 1 and any(trimmed.startswith(kw) for kw in ('def ', 'class ', 'import ', 'from ', 'function ', 'const ', 'let ', 'var ')):
            return 'code'
        
        # Default
        return 'text'
    
    @staticmethod
    def get_category_color(category: str) -> str:
        """Return hex color code for category"""
        colors = {
            'url': '#3B82F6',      # Blue
            'email': '#10B981',    # Green
            'phone': '#F59E0B',    # Amber
            'password': '#EF4444', # Red
            'code': '#8B5CF6',     # Purple
            'text': '#6B7280'      # Gray
        }
        return colors.get(category, '#6B7280')
    
    @staticmethod
    def get_category_icon(category: str) -> str:
        """Return emoji icon for category"""
        icons = {
            'url': '🔗',
            'email': '📧',
            'phone': '📞',
            'password': '🔒',
            'code': '💻',
            'text': '📝'
        }
        return icons.get(category, '📝')
