from typing import Dict, List, Any
from .tribe_service import TribeOutput


class NeuroMetrics:
    def __init__(self, neuro_virality_score: int, hook_score: int,
                 peak_response: int, sustained_attention: int,
                 ending_strength: int, drop_off_risk: float,
                 emotion_spike: int, visual_punch: int,
                 readability_relevance_blend: int, best_platform: str,
                 confidence: Dict[str, Any], rank: str,
                 sub_scores: List[Dict[str, Any]], fixes: List[str],
                 time_series: List[float], raw_tribe_data: Dict[str, Any]):
        self.neuro_virality_score = neuro_virality_score
        self.hook_score = hook_score
        self.peak_response = peak_response
        self.sustained_attention = sustained_attention
        self.ending_strength = ending_strength
        self.drop_off_risk = drop_off_risk
        self.emotion_spike = emotion_spike
        self.visual_punch = visual_punch
        self.readability_relevance_blend = readability_relevance_blend
        self.best_platform = best_platform
        self.confidence = confidence
        self.rank = rank
        self.sub_scores = sub_scores
        self.fixes = fixes
        self.time_series = time_series
        self.raw_tribe_data = raw_tribe_data

    def to_neurox_format(self) -> Dict[str, Any]:
        return {
            "globalScore": self.neuro_virality_score,
            "confidence": self.confidence,
            "rank": self.rank,
            "subScores": self.sub_scores,
            "fixes": self.fixes,
            "timeSeries": self.time_series,
            "bestPlatform": self.best_platform,
            "dropOffRisk": round(self.drop_off_risk, 2),
            "rawTribeData": self.raw_tribe_data
        }


class ScoreMapper:
    """Maps TribeOutput → NeuroMetrics using:
       base_score (deterministic from features) + ai_adjustment (from GPT-4o-mini)."""

    def __init__(self):
        self.platform_weights = {
            "X/Twitter": {"hook": 0.35, "peak": 0.30, "sustained": 0.25, "ending": 0.10},
            "TikTok":    {"hook": 0.25, "peak": 0.35, "sustained": 0.30, "ending": 0.10},
            "Instagram": {"hook": 0.30, "peak": 0.25, "sustained": 0.25, "ending": 0.20},
            "Telegram":  {"hook": 0.40, "peak": 0.20, "sustained": 0.20, "ending": 0.20}
        }

    def map(self, tribe_output: TribeOutput) -> NeuroMetrics:
        # Raw signal scores (0-100)
        hook_score = int(tribe_output.raw_hook_score * 100)
        peak_response = int(tribe_output.raw_attention_peak * 100)
        sustained_attention = int(tribe_output.raw_attention_mean * 100)
        ending_strength = int(tribe_output.raw_ending_strength * 100)
        emotion_spike = int(tribe_output.raw_emotion_spike * 100)
        visual_punch = int(tribe_output.raw_visual_punch * 100)

        readability = tribe_output.ocr_readability
        relevance = tribe_output.relevance_score
        rr_blend = int((readability * 0.4 + relevance * 0.6) * 100)

        # ── Deterministic base score ────────────────────────────
        base_score = int(
            0.30 * hook_score +
            0.20 * peak_response +
            0.20 * sustained_attention +
            0.15 * ending_strength +
            0.15 * rr_blend
        )

        # ── Apply AI adjustment (clamped -20 to +20) ───────────
        ai_adj = tribe_output.ai_adjustment
        neuro_virality = max(0, min(100, base_score + ai_adj))

        # Drop-off risk
        ts = tribe_output.time_series
        if len(ts) >= 10:
            early = sum(ts[:3]) / 3
            late = sum(ts[-7:]) / 7
            drop_off_risk = max(0, 1 - (late / early)) if early > 0 else 0
        else:
            drop_off_risk = 0.5

        # Best platform — prefer AI's pick, else compute
        if tribe_output.ai_best_platform:
            best_platform = tribe_output.ai_best_platform
        else:
            best_platform = self._determine_best_platform(
                hook_score, peak_response, sustained_attention, ending_strength)

        confidence = self._calculate_confidence(tribe_output)

        # Rank — prefer AI's pick, else generate
        rank = tribe_output.ai_rank if tribe_output.ai_rank else \
            self._generate_rank(neuro_virality)

        # Fixes — prefer AI's picks, else generate deterministic
        fixes = tribe_output.ai_fixes[:3] if tribe_output.ai_fixes else \
            self._generate_fixes(tribe_output, hook_score, drop_off_risk, readability)
        while len(fixes) < 3:
            fixes.append("Enhance visual hierarchy for stronger platform impact.")
        fixes = fixes[:3]

        sub_scores = [
            {"name": "Hook Score", "val": hook_score},
            {"name": "Peak Response", "val": peak_response},
            {"name": "Sustained Attention", "val": sustained_attention},
            {"name": "Ending Strength", "val": ending_strength},
            {"name": "Visual Punch", "val": visual_punch},
            {"name": "Emotion Spike", "val": emotion_spike},
            {"name": "Readability Blend", "val": rr_blend}
        ]

        return NeuroMetrics(
            neuro_virality_score=neuro_virality,
            hook_score=hook_score,
            peak_response=peak_response,
            sustained_attention=sustained_attention,
            ending_strength=ending_strength,
            drop_off_risk=drop_off_risk,
            emotion_spike=emotion_spike,
            visual_punch=visual_punch,
            readability_relevance_blend=rr_blend,
            best_platform=best_platform,
            confidence=confidence,
            rank=rank,
            sub_scores=sub_scores,
            fixes=fixes,
            time_series=tribe_output.time_series,
            raw_tribe_data=tribe_output.to_dict()
        )

    def _determine_best_platform(self, hook, peak, sustained, ending) -> str:
        scores = {}
        for platform, w in self.platform_weights.items():
            scores[platform] = w["hook"]*hook + w["peak"]*peak + w["sustained"]*sustained + w["ending"]*ending
        return max(scores, key=scores.get)

    def _calculate_confidence(self, t: TribeOutput) -> Dict[str, Any]:
        mode = t.metadata.get("mode", "deterministic")
        if mode == "hybrid_ai":
            return {"text": "HIGH CONFIDENCE", "color": "#10b981"}
        var = self._variance(t.time_series)
        if var < 0.05 and len(t.time_series) >= 30:
            return {"text": "HIGH CONFIDENCE", "color": "#10b981"}
        if var < 0.15:
            return {"text": "MEDIUM CONFIDENCE", "color": "#f59e0b"}
        return {"text": "EXPERIMENTAL", "color": "#8b5cf6"}

    def _variance(self, data: List[float]) -> float:
        if not data:
            return 1.0
        m = sum(data) / len(data)
        return sum((x - m) ** 2 for x in data) / len(data)

    def _generate_rank(self, score: int) -> str:
        if score >= 90:   return "[ALPHA] Top 3% of X/Twitter Shitpost Meta"
        if score >= 80:   return "[OPTIMAL] High retention span expected"
        if score >= 70:   return "[BETA] Needs memetic structural refinement"
        if score >= 60:   return "[WARNING] Low visibility ranking on algorithmic feeds"
        return "[CRITICAL] Extremely volatile engagement trap"

    def _generate_fixes(self, t: TribeOutput, hook: int,
                        drop_off: float, readability: float) -> List[str]:
        fixes = []
        if hook < 60:
            fixes.append("Increase shadow contrast by 15% to trigger higher dopamine retention.")
        if drop_off > 0.3:
            fixes.append("Crop outer margins by 10% to force focal entity recognition.")
        if t.raw_attention_peak < 0.6:
            fixes.append("Add glowing eyes or explicit ticker symbols for instant recognition.")
        if readability < 0.5:
            fixes.append("Text layout conflicts with visual anchor. Center or increase weight by 200.")
        if len(t.time_series) > 0 and t.time_series[0] < 0.5:
            fixes.append("Opening frame reads as dull. Deep-fry metrics require stronger first impression.")
        if t.raw_visual_punch < 0.6:
            fixes.append("Aspect ratio triggers algorithmic throttling. Remount to 4:5 for feed dominance.")
        if not fixes:
            fixes.append("Consider adding obvious meme references for mass adoption.")
        return fixes[:4]


score_mapper = ScoreMapper()
