import io
import os
import math
import tempfile
import logging
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageStat, ImageFilter, ImageEnhance
import httpx
from .tribe_service import is_url_safe
from .retry import retry_with_backoff

logger = logging.getLogger("neurox")


class PreprocessResult:
    def __init__(self,
                 processed_path: Optional[str],
                 duration_seconds: float,
                 num_frames: int,
                 resolution: Tuple[int, int],
                 preprocessing_steps: list,
                 features: Optional[Dict[str, Any]] = None,
                 frame_paths: Optional[List[str]] = None,
                 temp_files: Optional[List[str]] = None):
        self.processed_path = processed_path
        self.duration_seconds = duration_seconds
        self.num_frames = num_frames
        self.resolution = resolution
        self.preprocessing_steps = preprocessing_steps
        self.features = features or {}
        self.frame_paths = frame_paths or []
        self.temp_files = temp_files or []

    def cleanup(self):
        for path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        self.temp_files.clear()

    def to_dict(self):
        return {
            "processed_path": self.processed_path,
            "duration_seconds": self.duration_seconds,
            "num_frames": self.num_frames,
            "resolution": self.resolution,
            "preprocessing_steps": self.preprocessing_steps,
            "features": self.features
        }


class PreprocessService:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="neurox_preprocess_")

    async def process_media(self, file_path: str, media_type: str) -> PreprocessResult:
        logger.info(f"[PREPROCESS] Processing {media_type}: {file_path}")
        if media_type == "image":
            return await self._process_image(file_path)
        else:
            return await self._process_video(file_path)

    async def _process_image(self, file_path: str) -> PreprocessResult:
        is_http = file_path.startswith('http')
        if is_http and not is_url_safe(file_path):
            raise ValueError(f"URL not allowed: {file_path}")

        try:
            if is_http:
                async def _download():
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(file_path)
                        response.raise_for_status()
                        return response.content
                image_data = await retry_with_backoff(_download)
            else:
                with open(file_path, 'rb') as f:
                    image_data = f.read()

            img = Image.open(io.BytesIO(image_data))
            original_size = img.size

            # Extract features BEFORE any resizing
            features = self._extract_features(img)

            img_rgb = img.convert("RGB")
            if img_rgb.size[0] > 1080 or img_rgb.size[1] > 1080:
                img_rgb.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
            normalized_size = (img_rgb.size[0] // 16 * 16, img_rgb.size[1] // 16 * 16)
            img_rgb = img_rgb.resize(normalized_size, Image.Resampling.LANCZOS)

            steps = [
                f"{'Downloaded' if is_http else 'Loaded'} image",
                f"Original size: {original_size}",
                f"Normalized to: {normalized_size}",
                f"Extracted {len(features)} feature metrics"
            ]

            return PreprocessResult(
                processed_path=file_path,
                duration_seconds=3.0,
                num_frames=30,
                resolution=normalized_size,
                preprocessing_steps=steps,
                features=features
            )

        except Exception as e:
            logger.error(f"[PREPROCESS] Image processing failed: {e}")
            return PreprocessResult(
                processed_path=file_path,
                duration_seconds=3.0,
                num_frames=30,
                resolution=(512, 512),
                preprocessing_steps=[f"Error: {str(e)}"],
                features=self._default_features()
            )

    async def _process_video(self, file_path: str) -> PreprocessResult:
        is_http = file_path.startswith('http')
        if is_http and not is_url_safe(file_path):
            raise ValueError(f"URL not allowed: {file_path}")

        try:
            if is_http:
                async def _download():
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.get(file_path)
                        response.raise_for_status()
                        return response.content
                video_data = await retry_with_backoff(_download)
            else:
                with open(file_path, 'rb') as f:
                    video_data = f.read()

            features = self._default_features()
            features["media_type"] = "video"
            features["file_size_kb"] = round(len(video_data) / 1024, 1)

            return PreprocessResult(
                processed_path=file_path,
                duration_seconds=15.0,
                num_frames=60,
                resolution=(720, 1280),
                preprocessing_steps=[f"Video loaded ({features['file_size_kb']}KB)"],
                features=features
            )

        except Exception as e:
            logger.error(f"[PREPROCESS] Video processing failed: {e}")
            return PreprocessResult(
                processed_path=file_path,
                duration_seconds=15.0,
                num_frames=60,
                resolution=(720, 1280),
                preprocessing_steps=[f"Error: {str(e)}"],
                features=self._default_features()
            )

    # ── Feature Extraction ──────────────────────────────────────────

    def _extract_features(self, img: Image.Image) -> Dict[str, Any]:
        """Extract comprehensive visual features using PIL only (~50MB RAM)"""
        features = {}
        try:
            img_rgb = img.convert("RGB") if img.mode != "RGB" else img
            width, height = img_rgb.size
            features["resolution"] = [width, height]
            features["aspect_ratio_value"] = round(width / max(height, 1), 2)
            features["aspect_ratio"] = self._classify_aspect_ratio(width, height)

            # Brightness
            gray = img_rgb.convert("L")
            gs = ImageStat.Stat(gray)
            brightness = gs.mean[0] / 255.0
            features["brightness"] = round(brightness, 3)
            features["brightness_label"] = (
                "very_dark" if brightness < 0.2 else
                "dark" if brightness < 0.4 else
                "moderate" if brightness < 0.6 else
                "bright" if brightness < 0.8 else "very_bright"
            )

            # Contrast
            contrast = min(gs.stddev[0] / 128.0, 1.0)
            features["contrast"] = round(contrast, 3)
            features["contrast_label"] = "low" if contrast < 0.3 else "medium" if contrast < 0.6 else "high"

            # Saturation
            hsv = img_rgb.convert("HSV")
            sat = ImageStat.Stat(hsv).mean[1] / 255.0
            features["saturation"] = round(sat, 3)
            features["saturation_label"] = (
                "desaturated" if sat < 0.2 else
                "muted" if sat < 0.4 else
                "moderate" if sat < 0.6 else
                "vivid" if sat < 0.8 else "hyper_saturated"
            )

            # Edge density
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_density = min(ImageStat.Stat(edges).mean[0] / 128.0, 1.0)
            features["edge_density"] = round(edge_density, 3)

            # Image complexity (histogram entropy)
            histogram = gray.histogram()
            total = sum(histogram)
            entropy = -sum((c / total) * math.log2(c / total) for c in histogram if c > 0)
            complexity = entropy / math.log2(256)
            features["image_complexity"] = round(complexity, 3)
            features["complexity_label"] = "simple" if complexity < 0.5 else "moderate" if complexity < 0.75 else "complex"

            # Dominant colors (quantize a tiny thumbnail)
            small = img_rgb.resize((32, 32), Image.Resampling.LANCZOS)
            color_counts: Dict[tuple, int] = {}
            for px in small.getdata():
                q = (px[0] // 32 * 32, px[1] // 32 * 32, px[2] // 32 * 32)
                color_counts[q] = color_counts.get(q, 0) + 1
            top5 = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            features["dominant_colors"] = [f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c, _ in top5]
            features["color_variety"] = round(min(len(color_counts) / 50.0, 1.0), 3)

            # Text detection heuristics
            features.update(self._detect_text_heuristics(gray, edges))

            # Visual weight
            features["visual_weight"] = self._analyze_visual_weight(gray)

            # Derived flags
            features["is_dark_mode"] = brightness < 0.35
            features["is_deep_fried"] = contrast > 0.7 and sat > 0.7
            features["hook_strength"] = self._estimate_hook_strength(features)
            features["media_type"] = "image"

        except Exception as e:
            logger.error(f"[PREPROCESS] Feature extraction failed: {e}")
            return self._default_features()

        return features

    # ── Helper Methods ──────────────────────────────────────────────

    def _classify_aspect_ratio(self, w: int, h: int) -> str:
        r = w / max(h, 1)
        if abs(r - 1.0) < 0.1:   return "1:1"
        if abs(r - 16/9) < 0.15: return "16:9"
        if abs(r - 9/16) < 0.15: return "9:16"
        if abs(r - 4/5) < 0.15:  return "4:5"
        if abs(r - 4/3) < 0.15:  return "4:3"
        return "landscape" if r > 1 else "portrait"

    def _detect_text_heuristics(self, gray: Image.Image, edges: Image.Image) -> Dict[str, Any]:
        w, h = gray.size
        third = h // 3
        region_scores = {}
        for name, y0, y1 in [("top", 0, third), ("middle", third, 2*third), ("bottom", 2*third, h)]:
            stat = ImageStat.Stat(edges.crop((0, y0, w, y1)))
            region_scores[name] = stat.mean[0] / 128.0

        max_score = max(region_scores.values())
        avg_score = sum(region_scores.values()) / 3
        text_detected = max_score > 0.15
        text_density = min(avg_score / 0.5, 1.0) if text_detected else 0.0

        if not text_detected:
            text_position = "none"
        elif region_scores["top"] >= max_score:
            text_position = "top"
        elif region_scores["bottom"] >= max_score:
            text_position = "bottom"
        else:
            text_position = "middle"

        return {
            "text_detected": text_detected,
            "text_density": round(text_density, 3),
            "text_position": text_position,
            "region_edge_scores": {k: round(v, 3) for k, v in region_scores.items()}
        }

    def _analyze_visual_weight(self, gray: Image.Image) -> str:
        w, h = gray.size
        hw, hh = w // 2, h // 2
        weights = {}
        for name, box in [("top_left",(0,0,hw,hh)),("top_right",(hw,0,w,hh)),
                          ("bottom_left",(0,hh,hw,h)),("bottom_right",(hw,hh,w,h))]:
            weights[name] = ImageStat.Stat(gray.crop(box)).stddev[0]
        avg = sum(weights.values()) / 4
        var = sum((v - avg) ** 2 for v in weights.values()) / 4
        return "center" if var < 100 else max(weights, key=weights.get)

    def _estimate_hook_strength(self, f: Dict) -> str:
        s = 0
        if f.get("contrast", 0) > 0.6: s += 2
        elif f.get("contrast", 0) > 0.4: s += 1
        if f.get("text_detected"):
            s += 1
            if f.get("text_position") == "top": s += 1
        if f.get("saturation", 0) > 0.5: s += 1
        if f.get("is_deep_fried"): s += 1
        if f.get("image_complexity", 0) > 0.7: s += 1
        return "strong" if s >= 5 else "medium" if s >= 3 else "weak"

    def _default_features(self) -> Dict[str, Any]:
        return {
            "brightness": 0.5, "brightness_label": "moderate",
            "contrast": 0.5, "contrast_label": "medium",
            "saturation": 0.5, "saturation_label": "moderate",
            "edge_density": 0.3, "image_complexity": 0.6,
            "complexity_label": "moderate",
            "aspect_ratio": "1:1", "aspect_ratio_value": 1.0,
            "resolution": [512, 512],
            "dominant_colors": ["#808080"], "color_variety": 0.5,
            "text_detected": False, "text_density": 0.0,
            "text_position": "none",
            "region_edge_scores": {"top": 0.1, "middle": 0.1, "bottom": 0.1},
            "visual_weight": "center",
            "is_dark_mode": False, "is_deep_fried": False,
            "hook_strength": "medium", "media_type": "image"
        }


preprocess_service = PreprocessService()