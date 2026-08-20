from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BaseOMRProcessor(ABC):
    """
    Abstract base class for OMR (Optical Mark Recognition) & OCR answer sheet processors.
    Enables future plug-and-play integrations (e.g. OpenCV bubble sheet, Tesseract OCR, etc.)
    without modifying the core bot business logic.
    """

    @abstractmethod
    async def process_image(self, image_path: Path) -> Tuple[bool, Dict[int, str], str]:
        """
        Processes an answer sheet image.
        Returns: (success, answers_dict {1: 'A', 2: 'B'}, status_or_error_message)
        """
        pass


class DefaultOMRService(BaseOMRProcessor):
    """
    Production-ready stub/interface for image answer sheet processing.
    Gracefully notifies users when OCR/OMR scanning module is called.
    """

    async def process_image(self, image_path: Path) -> Tuple[bool, Dict[int, str], str]:
        # Validates image existence
        if not image_path.exists():
            return False, {}, "Fayl topilmadi."

        # Modular response without crashing the system
        return (
            False,
            {},
            "📷 Rasm orqali avtomatik tekshirish (OMR/OCR) moduli keyingi yangilanishda faollashtiriladi. "
            "Iltimos, javoblaringizni '1-A 2-B 3-C' formatida matn shaklida yuboring."
        )


omr_service = DefaultOMRService()
