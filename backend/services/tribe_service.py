import os
import math
import logging
import json
import re
from typing import Dict, List, Any
from openai import AsyncOpenAI
from urllib.parse import urlparse

logger = logging.getLogger("neurox.tribe")

USE_REAL_TRIBE = os.getenv("USE_REAL_TRIBE", "false").lower() == "true"

ALLOWED_SSRF_DOMAINS = [
    "supabase.co", "supabase.in", "storage.googleapis.com",
    "googleapis.com", "amazonaws.com", "r2.cloudflarestorage.com",
    "cdn.vercel-blobs.com",
]


def is_url_safe(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        netloc = parsed.netloc or ""
        if hostname.startswith("localhost") or hostname.startswith("127.") or hostname.startswith("0."):
            return False
        RESERVED_IP_RANGES = [
            "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.",
            "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.",
            "172.31.", "192.168.", "169.254.", "fe80:", "fc00:", "fd00:", "ff00:"
        ]
        ip_part = netloc.split(":")[0]
        import ipaddress
        try:
            ip = ipaddress.ip_address(ip_part)
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_multicast:
                return False
            ip_address = str(ip)
        except ValueError:
            ip_address = hostname
        for prefix in RESERVED_IP_RANGES:
            if ip_address.startswith(prefix):
                return False
        domain = hostname.split(":")[0]
        if not any(domain.endswith(a) or domain == a for a in ALLOWED_SSRF_DOMAINS):
            return False
        return True
    except Exception:
        return False


# Initialize OpenAI if API key is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CLIENT = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def seeded_random(seed: int, offset: int) -> float:
    x = math.sin(seed + offset) * 10000
    return x - math.floor(x)


class TribeOutput:
    def __init__(self, time_series: List[float],
                 raw_hook_score: float, raw_attention_peak: float,
                 raw_attention_mean: float, raw_ending_strength: float,
                 raw_emotion_spike: float, raw_visual_punch: float,
                 ocr_text: str = "", ocr_readability: float = 0.5,
                 relevance_score: float = 0.5,
                 metadata: Dict[str, Any] = None,
                 ai_adjustment: int = 0, ai_reasoning: str = "",
                 ai_fixes: List[str] = None,
                 ai_best_platform: str = "", ai_rank: str = ""):
        self.time_series = time_series
        self.raw_hook_score = raw_hook_score
        self.raw_attention_peak = raw_attention_peak
        self.raw_attention_mean = raw_attention_mean
        self.raw_ending_strength = raw_ending_strength
        self.raw_emotion_spike = raw_emotion_spike
        self.raw_visual_punch = raw_visual_punch
        self.ocr_text = ocr_text
        self.ocr_readability = ocr_readability
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
        self.ai_adjustment = ai_adjustment
        self.ai_reasoning = ai_reasoning
        self.ai_fixes = ai_fixes or []
        self.ai_best_platform = ai_best_platform
        self.ai_rank = ai_rank

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_series": self.time_series,
            "raw_hook_score": self.raw_hook_score,
            "raw_attention_peak": self.raw_attention_peak,
            "raw_attention_mean": self.raw_attention_mean,
            "raw_ending_strength": self.raw_ending_strength,
            "raw_emotion_spike": self.raw_emotion_spike,
            "raw_visual_punch": self.raw_visual_punch,
            "ocr_text": self.ocr_text,
            "ocr_readability": self.ocr_readability,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "ai_adjustment": self.ai_adjustment,
            "ai_reasoning": self.ai_reasoning,
            "ai_fixes": self.ai_fixes,
            "ai_best_platform": self.ai_best_platform,
            "ai_rank": self.ai_rank
        }


class TribeService:
    """Hybrid analysis: deterministic PIL features + optional GPT-4o-mini refinement (text-only)."""

    def __init__(self):
        self.use_real = USE_REAL_TRIBE
        logger.info("TRIBE initialized in %s mode", 'REAL' if self.use_real else 'MOCK')

    async def analyze(self, file_path: str, media_type: str, seed: int,
                      ocr_text: str = "", features: Dict[str, Any] = None) -> TribeOutput:
        features = features or {}
        signals = self._compute_signals(features, media_type)

        # AI refinement (text-only, no image sent)
        if OPENAI_CLIENT and self.use_real:
            try:
                ai = await self._get_ai_refinement(features, ocr_text, media_type, signals)
                signals["ai_adjustment"] = ai.get("score_adjustment", 0)
                signals["ai_reasoning"] = ai.get("reasoning", "")
                signals["ai_fixes"] = ai.get("fixes", [])
                signals["ai_best_platform"] = ai.get("best_platform", "X/Twitter")
                signals["ai_rank"] = ai.get("rank", "")
                signals["mode"] = "hybrid_ai"
                logger.info("[TRIBE] AI refinement: adjustment=%d", signals["ai_adjustment"])
            except Exception as e:
                logger.warning("[TRIBE] AI refinement failed, deterministic only: %s", e)
                signals["mode"] = "deterministic"
        else:
            signals["mode"] = "deterministic"
            logger.info("[TRIBE] Deterministic analysis (no AI)")

        return self._build_output(signals, features, media_type, seed, ocr_text)

    # ── Deterministic Scoring ───────────────────────────────────────

    def _compute_signals(self, f: Dict, media_type: str) -> Dict[str, Any]:
        brightness = f.get("brightness", 0.5)
        contrast = f.get("contrast", 0.5)
        saturation = f.get("saturation", 0.5)
        edge_density = f.get("edge_density", 0.3)
        complexity = f.get("image_complexity", 0.6)
        text_detected = f.get("text_detected", False)
        text_density = f.get("text_density", 0.0)
        color_variety = f.get("color_variety", 0.5)
        hook_strength = f.get("hook_strength", "medium")
        aspect_ratio = f.get("aspect_ratio", "1:1")

        # Scoring curves optimized for viral characteristics
        brightness_s = max(0, min(1, 1.0 - 2.0 * abs(brightness - 0.55)))
        contrast_s = min(contrast / 0.7, 1.0)
        saturation_s = min(saturation / 0.6, 1.0)
        edge_s = max(0, min(1, 1.0 - 2.0 * abs(edge_density - 0.35)))
        complexity_s = max(0, min(1, 1.0 - 2.0 * abs(complexity - 0.65)))

        text_s = 0.3
        if text_detected:
            text_s = 0.6 + text_density * 0.4
            if f.get("text_position") == "top":
                text_s = min(text_s + 0.15, 1.0)

        aspect_map = {"1:1": 0.9, "4:5": 1.0, "9:16": 0.85, "16:9": 0.7,
                      "4:3": 0.75, "portrait": 0.8, "landscape": 0.65}
        aspect_s = aspect_map.get(aspect_ratio, 0.7)
        color_s = max(0, min(1, 1.0 - 2.0 * abs(color_variety - 0.5)))
        hook_map = {"strong": 0.9, "medium": 0.6, "weak": 0.3}
        hook_s = hook_map.get(hook_strength, 0.6)

        return {
            "brightness_score": round(brightness_s, 3),
            "contrast_score": round(contrast_s, 3),
            "saturation_score": round(saturation_s, 3),
            "edge_score": round(edge_s, 3),
            "complexity_score": round(complexity_s, 3),
            "text_score": round(text_s, 3),
            "aspect_score": round(aspect_s, 3),
            "color_score": round(color_s, 3),
            "hook_score": round(hook_s, 3),
            "ai_adjustment": 0, "ai_reasoning": "", "ai_fixes": [],
            "ai_best_platform": "", "ai_rank": "",
        }

    # ── AI Refinement (text-only, ~$0.0002/call) ───────────────────

    async def _get_ai_refinement(self, features: Dict, ocr_text: str,
                                  media_type: str, signals: Dict) -> Dict[str, Any]:
        report = self._build_feature_report(features, ocr_text, media_type, signals)

        prompt = f"""You are a viral content analyst for social media. Based on these image features, provide a scoring refinement.

{report}

Respond ONLY with valid JSON (no markdown):
{{"score_adjustment": <int -20 to +20>, "reasoning": "<1-2 sentences>", "fixes": ["<fix1>", "<fix2>", "<fix3>"], "best_platform": "<X/Twitter|TikTok|Instagram|Telegram>", "rank": "<one of the ranks below>"}}

Ranks: "[ALPHA] Top 3% of X/Twitter Shitpost Meta", "[OPTIMAL] High retention span expected", "[BETA] Needs memetic structural refinement", "[WARNING] Low visibility ranking on algorithmic feeds", "[CRITICAL] Extremely volatile engagement trap"
"""

        response = await OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4
        )
        text = response.choices[0].message.content.strip()
        logger.info("[TRIBE] AI response: %s", text[:200])

        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result["score_adjustment"] = max(-20, min(20, int(result.get("score_adjustment", 0))))
            return result

        logger.warning("[TRIBE] Failed to parse AI JSON")
        return {"score_adjustment": 0, "reasoning": "", "fixes": [],
                "best_platform": "X/Twitter",
                "rank": "[BETA] Needs memetic structural refinement"}

    def _build_feature_report(self, f: Dict, ocr_text: str,
                               media_type: str, signals: Dict) -> str:
        lines = [
            f"Media: {media_type}",
            f"Resolution: {f.get('resolution', '?')}",
            f"Aspect ratio: {f.get('aspect_ratio', '?')}",
            f"Brightness: {f.get('brightness',0):.0%} ({f.get('brightness_label','?')})",
            f"Contrast: {f.get('contrast',0):.0%} ({f.get('contrast_label','?')})",
            f"Saturation: {f.get('saturation',0):.0%} ({f.get('saturation_label','?')})",
            f"Edge density: {f.get('edge_density',0):.0%}",
            f"Complexity: {f.get('image_complexity',0):.0%} ({f.get('complexity_label','?')})",
            f"Colors: {', '.join(f.get('dominant_colors',['?'])[:4])}",
            f"Color variety: {f.get('color_variety',0):.0%}",
            f"Text detected: {'Yes' if f.get('text_detected') else 'No'}",
        ]
        if f.get("text_detected"):
            lines.append(f"Text density: {f.get('text_density',0):.0%}")
            lines.append(f"Text position: {f.get('text_position','?')}")
        lines += [
            f"Dark mode: {'Yes' if f.get('is_dark_mode') else 'No'}",
            f"Deep-fried: {'Yes' if f.get('is_deep_fried') else 'No'}",
            f"Hook strength: {f.get('hook_strength','?')}",
            f"Visual weight: {f.get('visual_weight','?')}",
        ]
        if ocr_text and "[no significant" not in ocr_text:
            lines.append(f"Text hint: {ocr_text}")
        lines.append(f"\nBase scores: hook={signals.get('hook_score',0):.0%} "
                     f"contrast={signals.get('contrast_score',0):.0%} "
                     f"saturation={signals.get('saturation_score',0):.0%}")
        return "\n".join(lines)

    # ── Build Output ────────────────────────────────────────────────

    def _build_output(self, signals: Dict, features: Dict,
                      media_type: str, seed: int, ocr_text: str) -> TribeOutput:
        num_frames = 30 if media_type == "image" else 60
        hook = signals["hook_score"]
        base = 0.3 + hook * 0.4

        time_series = []
        for i in range(num_frames):
            progress = i / num_frames
            hook_boost = (3 - i) * 0.1 * hook if i < 3 else 0
            decay = 1 - (progress * 0.25)
            noise = math.sin(seed + i * 0.7) * 0.05
            ending = signals["contrast_score"] * 0.05 if i > num_frames * 0.75 else 0
            val = min(max(base + hook_boost + noise + ending, 0), 1) * decay
            time_series.append(round(val, 4))

        raw_hook = sum(time_series[:3]) / 3 if len(time_series) >= 3 else time_series[0]
        raw_peak = max(time_series)
        raw_mean = sum(time_series) / len(time_series)
        raw_ending = sum(time_series[-10:]) / 10 if len(time_series) >= 10 else raw_mean
        spikes = [time_series[i] - time_series[i-1] for i in range(1, len(time_series))
                  if time_series[i] - time_series[i-1] > 0.03]
        raw_emotion = max(spikes) if spikes else 0
        raw_vp = signals["contrast_score"] * 0.4 + signals["saturation_score"] * 0.3 + signals["color_score"] * 0.3

        compact_meta = {k: v for k, v in features.items()
                        if k not in ("region_edge_scores", "dominant_colors")}

        return TribeOutput(
            time_series=time_series,
            raw_hook_score=raw_hook,
            raw_attention_peak=raw_peak,
            raw_attention_mean=raw_mean,
            raw_ending_strength=raw_ending,
            raw_emotion_spike=raw_emotion,
            raw_visual_punch=raw_vp,
            ocr_text=ocr_text,
            ocr_readability=features.get("text_density", 0.0) if features.get("text_detected") else 0.0,
            relevance_score=signals.get("text_score", 0.5),
            metadata={
                "media_type": media_type, "num_frames": num_frames,
                "seed": seed, "mode": signals.get("mode", "deterministic"),
                "features_summary": compact_meta
            },
            ai_adjustment=signals.get("ai_adjustment", 0),
            ai_reasoning=signals.get("ai_reasoning", ""),
            ai_fixes=signals.get("ai_fixes", []),
            ai_best_platform=signals.get("ai_best_platform", ""),
            ai_rank=signals.get("ai_rank", "")
        )


tribe_service = TribeService()
