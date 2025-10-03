# src/backend/categorizer.py
import re
from typing import Tuple

class ContentCategorizer:
    """Categorize clipboard content using regex patterns"""
    
    # Regex patterns for detection
    URL_PATTERN = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    )
    
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    PHONE_PATTERN = re.compile(
        r'(\+\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}|\+\d{10,15}'
    )
    
    # Code patterns - detect common programming syntax
    CODE_PATTERNS = [
        re.compile(r'(function|def|class|import|const|let|var)\s+\w+'),
        re.compile(r'[{};]\s*\n'),
        re.compile(r'(if|for|while|return)\s*\('),
        re.compile(r'(public|private|protected)\s+(static\s+)?(\w+\s+)+\w+\s*\('),
    ]
    
    # Password heuristics
    PASSWORD_INDICATORS = ['password', 'passwd', 'pwd', 'pass', 'secret', 'key', 'token']
    
    @staticmethod
    def categorize(content: str) -> str:
        """
        Categorize content and return category name
        Returns: 'url', 'email', 'phone', 'password', 'code', or 'text'
        """
        if not content or len(content.strip()) == 0:
            return 'text'
        
        content_lower = content.lower()
        
        # Check for URLs
        if ContentCategorizer.URL_PATTERN.search(content):
            return 'url'
        
        # Check for emails
        if ContentCategorizer.EMAIL_PATTERN.search(content):
            return 'email'
        
        # Check for phone numbers
        if ContentCategorizer.PHONE_PATTERN.search(content):
            return 'phone'
        
        # Check for password indicators
        for indicator in ContentCategorizer.PASSWORD_INDICATORS:
            if indicator in content_lower:
                return 'password'
        
        # Check if it's code (at least 2 code patterns match)
        code_matches = sum(1 for pattern in ContentCategorizer.CODE_PATTERNS if pattern.search(content))
        if code_matches >= 2 or (len(content) > 50 and code_matches >= 1):
            return 'code'
        
        # Default to text
        return 'text'
    
    @staticmethod
    def get_category_color(category: str) -> str:
        """Return color code for category"""
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
