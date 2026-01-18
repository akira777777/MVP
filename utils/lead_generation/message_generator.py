"""
Message generator for personalized cold outreach to business owners.
"""

from typing import Optional
from utils.lead_generation.models import BusinessLead, OwnerInfo


class MessageGenerator:
    """Generator for personalized cold messages."""

    def __init__(self, language: str = "cs"):
        """
        Initialize message generator.

        Args:
            language: Language code ('cs' for Czech, 'en' for English, 'ru' for Russian)
        """
        self.language = language

    def generate_cold_message(
        self,
        lead: BusinessLead,
        sender_name: Optional[str] = None,
        include_demo_offer: bool = True,
    ) -> str:
        """
        Generate personalized cold message for business owner.

        Args:
            lead: Business lead with owner information
            sender_name: Name of sender (optional)
            include_demo_offer: Whether to include free demo offer

        Returns:
            Personalized message text
        """
        owner = lead.get_primary_owner()
        contact_name = lead.get_contact_name()

        if self.language == "cs":
            return self._generate_czech_message(lead, owner, contact_name, sender_name, include_demo_offer)
        elif self.language == "en":
            return self._generate_english_message(lead, owner, contact_name, sender_name, include_demo_offer)
        elif self.language == "ru":
            return self._generate_russian_message(lead, owner, contact_name, sender_name, include_demo_offer)
        else:
            # Default to Czech
            return self._generate_czech_message(lead, owner, contact_name, sender_name, include_demo_offer)

    def _generate_czech_message(
        self,
        lead: BusinessLead,
        owner: Optional[OwnerInfo],
        contact_name: str,
        sender_name: Optional[str],
        include_demo: bool,
    ) -> str:
        """Generate Czech message."""
        greeting = f"Dobrý den, pane {contact_name.split()[0] if owner else 'řediteli'},"
        if owner and len(contact_name.split()) > 1:
            # Use last name if available
            greeting = f"Dobrý den, pane {contact_name.split()[-1]},"

        business_name = lead.business_name
        business_type = lead.category or "vašeho podniku"

        message_parts = [
            greeting,
            "",
            f"Kontaktuji vás ohledně automatizace pro {business_name}.",
            "",
            "Nabízím řešení pro:",
            "• Automatizaci zákaznických chatů (Telegram, WhatsApp, SMS)",
            "• Integraci s Google Maps a rezervačními systémy",
            "• CRM pro správu klientů a leadů",
            "• Zjednodušení procesu rezervací a komunikace",
            "",
        ]

        if include_demo:
            message_parts.extend(
                [
                    "Rád bych vám nabídl bezplatnou demo verzi nebo mini-audit vašeho současného procesu práce s klienty.",
                    "",
                ]
            )

        message_parts.extend(
            [
                "Můžeme si domluvit krátký hovor nebo osobní setkání v Praze.",
                "",
            ]
        )

        if sender_name:
            message_parts.append(f"S pozdravem,\n{sender_name}")
        else:
            message_parts.append("S pozdravem")

        return "\n".join(message_parts)

    def _generate_english_message(
        self,
        lead: BusinessLead,
        owner: Optional[OwnerInfo],
        contact_name: str,
        sender_name: Optional[str],
        include_demo: bool,
    ) -> str:
        """Generate English message."""
        greeting = f"Hello {contact_name.split()[0] if owner else 'Sir/Madam'},"
        if owner and len(contact_name.split()) > 1:
            greeting = f"Hello Mr./Ms. {contact_name.split()[-1]},"

        business_name = lead.business_name
        business_type = lead.category or "your business"

        message_parts = [
            greeting,
            "",
            f"I'm reaching out regarding automation solutions for {business_name}.",
            "",
            "I offer solutions for:",
            "• Customer chat automation (Telegram, WhatsApp, SMS)",
            "• Integration with Google Maps and booking systems",
            "• CRM for client and lead management",
            "• Streamlining reservations and communication processes",
            "",
        ]

        if include_demo:
            message_parts.extend(
                [
                    "I'd be happy to offer you a free demo or mini-audit of your current client management process.",
                    "",
                ]
            )

        message_parts.extend(
            [
                "We can schedule a short call or in-person meeting in Prague.",
                "",
            ]
        )

        if sender_name:
            message_parts.append(f"Best regards,\n{sender_name}")
        else:
            message_parts.append("Best regards")

        return "\n".join(message_parts)

    def _generate_russian_message(
        self,
        lead: BusinessLead,
        owner: Optional[OwnerInfo],
        contact_name: str,
        sender_name: Optional[str],
        include_demo: bool,
    ) -> str:
        """Generate Russian message."""
        greeting = f"Здравствуйте, {contact_name.split()[0] if owner else 'уважаемый директор'},"
        if owner and len(contact_name.split()) > 1:
            greeting = f"Здравствуйте, {contact_name},"

        business_name = lead.business_name
        business_type = lead.category or "ваш бизнес"

        message_parts = [
            greeting,
            "",
            f"Обращаюсь к вам по поводу автоматизации для {business_name}.",
            "",
            "Предлагаю решения для:",
            "• Автоматизации клиентских чатов (Telegram, WhatsApp, SMS)",
            "• Интеграции с Google Maps и системами бронирования",
            "• CRM для управления клиентами и лидами",
            "• Упрощения процесса бронирований и коммуникации",
            "",
        ]

        if include_demo:
            message_parts.extend(
                [
                    "Буду рад предложить бесплатную демо-версию или мини-аудит вашего текущего процесса работы с клиентами.",
                    "",
                ]
            )

        message_parts.extend(
            [
                "Можем договориться о коротком звонке или личной встрече в Праге.",
                "",
            ]
        )

        if sender_name:
            message_parts.append(f"С уважением,\n{sender_name}")
        else:
            message_parts.append("С уважением")

        return "\n".join(message_parts)
