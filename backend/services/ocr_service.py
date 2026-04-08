import io
import logging
from typing import Dict, Any
from PIL import Image, ImageStat, ImageFilter, ImageEnhance
import httpx
from .tribe_service import is_url_safe
from .retry import retry_with_backoff

logger = logging.getLogger("neurox")


class OCRResult:
    def __init__(self, text: str, readability_score: float,
                 detected_language: str, text_regions: list):
        self.text = text
        self.readability_score = readability_score
        self.detected_language = detected_language
        self.text_regions = text_regions

    def to_dict(self):
        return {
            "text": self.text,
            "readability_score": self.readability_score,
            "detected_language": self.detected_language,
            "text_regions": self.text_regions
        }


class OCRService:
    """Lightweight PIL-based text detection. No EasyOCR/PyTorch needed.
    Detects text presence, density, and position via edge analysis.
    Actual text reading is delegated to GPT-4o-mini in the tribe service."""

    def __init__(self):
        logger.info("[OCR] Initialized lightweight PIL-based text detection")

    async def extract_text(self, file_path: str, media_type: str) -> OCRResult:
        logger.info(f"[OCR] Analyzing text in {media_type}: {file_path}")
        if media_type == "image":
            return await self._analyze_image(file_path)
        return self._video_fallback()

    async def _analyze_image(self, file_path: str) -> OCRResult:
        is_http = file_path.startswith('http')
        if is_http and not is_url_safe(file_path):
            raise ValueError(f"URL not allowed: {file_path}")

        try:
            if is_http:
                async def _dl():
                    async with httpx.AsyncClient(timeout=30.0) as c:
                        r = await c.get(file_path); r.raise_for_status(); return r.content
                data = await retry_with_backoff(_dl)
            else:
                with open(file_path, 'rb') as f:
                    data = f.read()

            img = Image.open(io.BytesIO(data)).convert("RGB")
            analysis = self._analyze_text_characteristics(img)
            desc = self._build_description(analysis)
            return OCRResult(
                text=desc,
                readability_score=analysis.get("readability", 0.5),
                detected_language="en",
                text_regions=analysis.get("regions", [])
            )
        except Exception as e:
            logger.error(f"[OCR] Analysis failed: {e}")
            return OCRResult(text="", readability_score=0.0,
                             detected_language="unknown", text_regions=[])

    def _video_fallback(self) -> OCRResult:
        return OCRResult(
            text="[video content]",
            readability_score=0.3,
            detected_language="en",
            text_regions=[]
        )

    def _analyze_text_characteristics(self, img: Image.Image) -> Dict[str, Any]:
        w, h = img.size
        gray = img.convert("L")
        enhanced = ImageEnhance.Contrast(gray).enhance(1.5)
        edges = enhanced.filter(ImageFilter.FIND_EDGES)

        # Analyze edge density in horizontal strips
        strip_h = max(h // 20, 1)
        strip_scores = []
        for y in range(0, h, strip_h):
            strip = edges.crop((0, y, w, min(y + strip_h, h)))
            strip_scores.append(ImageStat.Stat(strip).mean[0])

        avg_strip = sum(strip_scores) / max(len(strip_scores), 1)
        high_strips = sum(1 for s in strip_scores if s > avg_strip * 1.3)
        text_ratio = high_strips / max(len(strip_scores), 1)

        overall_edge = ImageStat.Stat(edges).mean[0] / 255.0
        has_text = overall_edge > 0.08 and text_ratio > 0.1
        text_density = min(text_ratio * 2, 1.0) if has_text else 0.0
        readability = min(ImageStat.Stat(gray).stddev[0] / 128.0, 1.0) if has_text else 0.0

        third_h = h // 3
        regions = []
        for name, y0, y1 in [("top",0,third_h),("middle",third_h,2*third_h),("bottom",2*third_h,h)]:
            d = ImageStat.Stat(edges.crop((0, y0, w, y1))).mean[0] / 255.0
            if d > 0.1:
                regions.append({"position": name, "edge_density": round(d, 3), "likely_text": d > 0.12})

        return {"has_text": has_text, "text_density": round(text_density, 3),
                "readability": round(readability, 3), "regions": regions}

    def _build_description(self, analysis: Dict[str, Any]) -> str:
        if not analysis.get("has_text"):
            return "[no significant text detected]"
        d = analysis.get("text_density", 0)
        level = "heavy" if d > 0.6 else "moderate" if d > 0.3 else "light"
        positions = [r["position"] for r in analysis.get("regions", []) if r.get("likely_text")]
        pos_str = f" in {', '.join(positions)}" if positions else ""
        return f"{level} text content detected{pos_str}"


ocr_service = OCRService()