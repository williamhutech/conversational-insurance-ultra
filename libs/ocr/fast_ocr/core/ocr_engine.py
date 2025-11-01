"""
OCR Engine wrapper around RapidOCR.

Provides a clean interface with lazy initialization and result parsing.
"""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import numpy as np
from PIL import Image

from ..config import OCRConfig

# RapidOCR enum types (will be imported lazily when needed)
_RAPIDOCR_ENUMS = None


class OCREngine:
    """
    Wrapper around RapidOCR with caching and optimization.

    Lazily initializes RapidOCR instance on first use to avoid
    unnecessary model loading.
    """

    def __init__(self, config: OCRConfig):
        """
        Initialize OCR engine.

        Args:
            config: OCR configuration
        """
        self.config = config
        self._ocr = None  # Lazy initialization

    def _load_rapidocr_enums(self):
        """
        Lazy load RapidOCR enum types.
        """
        global _RAPIDOCR_ENUMS
        if _RAPIDOCR_ENUMS is None:
            try:
                from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion
                _RAPIDOCR_ENUMS = {
                    'EngineType': EngineType,
                    'LangDet': LangDet,
                    'LangRec': LangRec,
                    'ModelType': ModelType,
                    'OCRVersion': OCRVersion
                }
            except ImportError:
                raise ImportError(
                    "RapidOCR not installed. Install with: pip install rapidocr onnxruntime"
                )
        return _RAPIDOCR_ENUMS

    def _map_language_to_rapidocr(self, lang: str, enums: dict) -> tuple:
        """
        Map language code to RapidOCR language enum types.

        Args:
            lang: Language code (e.g., 'en', 'ch', 'fr')
            enums: Dictionary of RapidOCR enum types

        Returns:
            Tuple of (det_lang, rec_lang) enum values for RapidOCR
        """
        LangDet = enums['LangDet']
        LangRec = enums['LangRec']

        # Language mapping for detection (Det.lang_type)
        # RapidOCR detection supports: CH, EN, MULTI
        det_lang_map = {
            'ch': LangDet.CH,
            'chinese_cht': LangDet.CH,
            'en': LangDet.EN,
        }
        det_lang = det_lang_map.get(lang, LangDet.MULTI)  # Default to multi-language detection

        # Language mapping for recognition (Rec.lang_type)
        # RapidOCR uses script-based language codes:
        # CH, CH_DOC, EN, ARABIC, CHINESE_CHT, CYRILLIC, DEVANAGARI, JAPAN, KOREAN,
        # KA, LATIN, TA, TE, ESLAV, TH, EL

        rec_lang_map = {
            # Chinese variants
            'ch': LangRec.CH,
            'chinese_cht': LangRec.CHINESE_CHT,

            # English
            'en': LangRec.EN,

            # European languages (Latin script)
            'fr': LangRec.LATIN,
            'german': LangRec.LATIN,
            'it': LangRec.LATIN,
            'es': LangRec.LATIN,
            'pt': LangRec.LATIN,
            'nl': LangRec.LATIN,
            'no': LangRec.LATIN,
            'pl': LangRec.LATIN,
            'cs': LangRec.LATIN,
            'da': LangRec.LATIN,
            'sv': LangRec.LATIN,
            'tr': LangRec.LATIN,
            'hr': LangRec.LATIN,
            'hu': LangRec.LATIN,
            'ro': LangRec.LATIN,
            'sk': LangRec.LATIN,
            'sl': LangRec.LATIN,

            # Cyrillic script languages
            'ru': LangRec.CYRILLIC,
            'bg': LangRec.CYRILLIC,
            'uk': LangRec.CYRILLIC,
            'be': LangRec.CYRILLIC,
            'rs_cyrillic': LangRec.CYRILLIC,

            # Other scripts
            'ar': LangRec.ARABIC,
            'japan': LangRec.JAPAN,
            'korean': LangRec.KOREAN,
            'hi': LangRec.DEVANAGARI,
            'ta': LangRec.TA,
            'te': LangRec.TE,
            'th': LangRec.TH,
            'ka': LangRec.KA,
            'el': LangRec.EL,
        }

        # Default to CH (Chinese) which supports multi-language including English
        rec_lang = rec_lang_map.get(lang, LangRec.CH)

        return det_lang, rec_lang

    @property
    def ocr(self):
        """
        Lazy-load RapidOCR instance.

        Returns:
            RapidOCR instance
        """
        if self._ocr is None:
            try:
                from rapidocr import RapidOCR
            except ImportError:
                raise ImportError(
                    "RapidOCR not installed. Install with: pip install rapidocr onnxruntime"
                )

            # Load enum types
            enums = self._load_rapidocr_enums()
            EngineType = enums['EngineType']
            ModelType = enums['ModelType']
            OCRVersion = enums['OCRVersion']

            # Map language codes to enum types
            det_lang, rec_lang = self._map_language_to_rapidocr(self.config.lang, enums)

            # Map engine_type string to enum
            engine_type_map = {
                'onnxruntime': EngineType.ONNXRUNTIME,
                'openvino': EngineType.OPENVINO,
                'paddle': EngineType.PADDLE,
                'torch': EngineType.TORCH,
            }
            engine_type = engine_type_map.get(self.config.engine_type.lower(), EngineType.ONNXRUNTIME)

            # Map model_type string to enum
            model_type_map = {
                'mobile': ModelType.MOBILE,
                'server': ModelType.SERVER,
            }
            model_type = model_type_map.get(self.config.model_type.lower(), ModelType.MOBILE)

            # Map ocr_version string to enum
            ocr_version_map = {
                'PP-OCRv4': OCRVersion.PPOCRV4,
                'PP-OCRv5': OCRVersion.PPOCRV5,
            }
            ocr_version = ocr_version_map.get(self.config.ocr_version, OCRVersion.PPOCRV5)

            # Build RapidOCR params dict with proper enum types
            params = {
                # Global settings
                "Global.text_score": self.config.text_score,
                "Global.use_det": self.config.det,
                "Global.use_cls": self.config.use_angle_cls,
                "Global.use_rec": self.config.rec,
                "Global.log_level": "info" if self.config.show_log else "critical",

                # Detection settings
                "Det.engine_type": engine_type,
                "Det.lang_type": det_lang,
                "Det.model_type": model_type,
                "Det.ocr_version": ocr_version,
                "Det.thresh": self.config.det_db_thresh,
                "Det.box_thresh": self.config.det_db_box_thresh,

                # Classification settings
                "Cls.engine_type": engine_type,
                "Cls.model_type": model_type,
                "Cls.ocr_version": ocr_version,

                # Recognition settings
                "Rec.engine_type": engine_type,
                "Rec.lang_type": rec_lang,
                "Rec.model_type": model_type,
                "Rec.ocr_version": ocr_version,
                "Rec.rec_batch_num": self.config.rec_batch_num,
            }

            self._ocr = RapidOCR(params=params)

        return self._ocr

    def extract_from_image(
        self,
        image: Union[str, Path, np.ndarray, Image.Image]
    ) -> Dict[str, Any]:
        """
        Extract text from image with bounding boxes and confidence scores.

        Args:
            image: Image file path, numpy array, or PIL Image

        Returns:
            Dictionary with:
                - text: str - Extracted text (newline-separated)
                - boxes: list - Bounding boxes [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                - texts: list - Individual text strings
                - confidences: list - Confidence scores per text region
                - average_confidence: float - Average confidence
        """
        # Convert PIL Image to numpy array if needed
        if isinstance(image, Image.Image):
            image = np.array(image)

        # Convert Path to string
        if isinstance(image, Path):
            image = str(image)

        # Run RapidOCR
        # RapidOCR returns: (dt_boxes, rec_res, elapse) or None
        # where rec_res is list of [text, score]
        result = self.ocr(image)

        # Parse results
        return self._parse_results(result)

    def extract_from_multiple_images(
        self,
        images: List[Union[str, Path, np.ndarray, Image.Image]]
    ) -> List[Dict[str, Any]]:
        """
        Extract text from multiple images.

        Args:
            images: List of images

        Returns:
            List of extraction results (one per image)
        """
        return [self.extract_from_image(img) for img in images]

    def _parse_results(self, result) -> Dict[str, Any]:
        """
        Parse RapidOCR results into structured format.

        Args:
            result: RapidOCROutput object or None

        Returns:
            Structured dictionary with text, boxes, confidences
        """
        # Handle None or empty results
        if result is None:
            return {
                'text': '',
                'boxes': [],
                'texts': [],
                'confidences': [],
                'average_confidence': 0.0
            }

        # RapidOCROutput has: boxes, txts, scores, elapse attributes
        boxes_raw = result.boxes
        texts_raw = result.txts
        scores_raw = result.scores

        # Handle empty results (check for None or empty list)
        if boxes_raw is None or texts_raw is None or len(texts_raw) == 0:
            return {
                'text': '',
                'boxes': [],
                'texts': [],
                'confidences': [],
                'average_confidence': 0.0
            }

        boxes = []
        texts = []
        confidences = []

        # RapidOCR RapidOCROutput provides:
        # - boxes: list of numpy arrays with 4 corner points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        # - txts: list of text strings
        # - scores: list of confidence scores
        for i, box in enumerate(boxes_raw):
            # Convert numpy array to list if needed
            if hasattr(box, 'tolist'):
                box = box.tolist()
            boxes.append(box)
            texts.append(texts_raw[i])
            confidences.append(float(scores_raw[i]))

        # Join texts with newlines
        full_text = '\n'.join(texts)

        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            'text': full_text,
            'boxes': boxes,
            'texts': texts,
            'confidences': confidences,
            'average_confidence': avg_confidence
        }

    def detect_language(self, image: Union[str, Path, np.ndarray]) -> str:
        """
        Auto-detect language from image (simplified heuristic).

        Args:
            image: Image to analyze

        Returns:
            Detected language code

        Note:
            This is a simplified implementation. For production use,
            consider using langdetect or similar library on extracted text.
        """
        # Save current language
        original_lang = self.config.lang

        # Try OCR with multi-language model
        self.config.lang = 'ch'  # Chinese+English model for broad coverage
        self._ocr = None  # Reset instance

        try:
            result = self.extract_from_image(image)
            text = result['text']

            # Simple character-based detection
            detected_lang = self._detect_language_from_text(text)

            return detected_lang

        finally:
            # Restore original language
            self.config.lang = original_lang
            self._ocr = None  # Reset instance

    def _detect_language_from_text(self, text: str) -> str:
        """
        Detect language from text using character analysis.

        Args:
            text: Text to analyze

        Returns:
            Language code
        """
        if not text:
            return 'en'

        # Count character types
        char_counts = {
            'latin': 0,
            'chinese': 0,
            'japanese': 0,
            'korean': 0,
            'arabic': 0,
            'cyrillic': 0
        }

        for char in text:
            code_point = ord(char)

            # Latin (including extended Latin)
            if (0x0041 <= code_point <= 0x007A) or (0x00C0 <= code_point <= 0x024F):
                char_counts['latin'] += 1

            # Chinese (CJK Unified Ideographs)
            elif 0x4E00 <= code_point <= 0x9FFF:
                char_counts['chinese'] += 1

            # Japanese (Hiragana, Katakana)
            elif (0x3040 <= code_point <= 0x309F) or (0x30A0 <= code_point <= 0x30FF):
                char_counts['japanese'] += 1

            # Korean (Hangul)
            elif (0xAC00 <= code_point <= 0xD7AF) or (0x1100 <= code_point <= 0x11FF):
                char_counts['korean'] += 1

            # Arabic
            elif (0x0600 <= code_point <= 0x06FF) or (0x0750 <= code_point <= 0x077F):
                char_counts['arabic'] += 1

            # Cyrillic
            elif 0x0400 <= code_point <= 0x04FF:
                char_counts['cyrillic'] += 1

        # Determine predominant script
        max_script = max(char_counts, key=char_counts.get)
        max_count = char_counts[max_script]

        # Need at least 10% non-space characters to be confident
        total_chars = sum(char_counts.values())
        if total_chars < 10:
            return 'en'

        # Map script to language
        script_to_lang = {
            'latin': 'en',
            'chinese': 'ch',
            'japanese': 'japan',
            'korean': 'korean',
            'arabic': 'ar',
            'cyrillic': 'ru'
        }

        return script_to_lang.get(max_script, 'en')

    def set_language(self, lang: str):
        """
        Change OCR language.

        Args:
            lang: New language code

        Note:
            This will reset the OCR instance on next use.
        """
        if lang != self.config.lang:
            self.config.lang = lang
            self._ocr = None  # Force re-initialization

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.

        Returns:
            List of language codes supported by RapidOCR (PP-OCRv5)
        """
        # RapidOCR with PP-OCRv5 supports 80+ languages
        # This list is compatible with the previous PaddleOCR implementation
        return [
            'ch', 'en', 'fr', 'german', 'japan', 'korean', 'it', 'es', 'pt', 'ru',
            'ar', 'hi', 'ug', 'fa', 'ur', 'rs_latin', 'oc', 'mr', 'ne', 'rs_cyrillic',
            'bg', 'uk', 'be', 'te', 'abq', 'ta', 'af', 'az', 'bs', 'cs', 'cy', 'da',
            'et', 'ga', 'hr', 'hu', 'id', 'is', 'ku', 'lt', 'lv', 'mi', 'ms', 'mt',
            'nl', 'no', 'pl', 'ro', 'sk', 'sl', 'sq', 'sv', 'sw', 'tl', 'tr', 'uz',
            'vi', 'mn', 'chinese_cht', 'latin', 'arabic', 'cyrillic', 'devanagari'
        ]
