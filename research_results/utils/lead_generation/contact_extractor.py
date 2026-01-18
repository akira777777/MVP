"""
Извлечение контактов (email, телефон) с веб-сайтов бизнесов.
"""

import logging
from typing import Dict, Optional

try:
    from phone_email_extractor import extract_emails, extract_phones

    CONTACT_EXTRACTOR_AVAILABLE = True
except ImportError:
    CONTACT_EXTRACTOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContactExtractor:
    """
    Извлекает email и телефонные номера с веб-сайтов бизнесов.
    """

    def __init__(self, use_library: bool = True):
        """
        Initialize contact extractor.

        Args:
            use_library: Use phone-email-extractor library if available
        """
        self.use_library = use_library and CONTACT_EXTRACTOR_AVAILABLE
        if not self.use_library:
            logger.warning(
                "phone-email-extractor not available, using basic regex extraction"
            )

    def extract_from_html(self, html_content: str) -> Dict[str, Optional[str]]:
        """
        Extract email and phone from HTML content.

        Args:
            html_content: HTML content of the webpage

        Returns:
            Dictionary with 'email' and 'phone' keys
        """
        result = {"email": None, "phone": None}

        if self.use_library:
            try:
                emails = extract_emails(html_content)
                phones = extract_phones(html_content)

                # Filter emails
                if emails:
                    filtered_emails = [
                        e
                        for e in emails
                        if not any(
                            domain in e.lower()
                            for domain in [
                                "example.com",
                                "test.com",
                                "placeholder",
                                "noreply",
                            ]
                        )
                    ]
                    if filtered_emails:
                        result["email"] = filtered_emails[0].lower().strip()

                # Filter Czech phone numbers
                if phones:
                    czech_phones = [
                        p
                        for p in phones
                        if "+420" in p.replace(" ", "")
                        or len(
                            p.replace(" ", "")
                            .replace("-", "")
                            .replace("(", "")
                            .replace(")", "")
                        )
                        == 9
                    ]
                    if czech_phones:
                        result["phone"] = czech_phones[0]

            except Exception as e:
                logger.debug(f"Error using contact extractor library: {e}")

        # Fallback to basic regex if library not available or failed
        if not result["email"]:
            from .utils import extract_email_from_text

            result["email"] = extract_email_from_text(html_content)

        return result
