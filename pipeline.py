#!/usr/bin/env python3
"""6-agent serial pipeline to generate 60 start-frame prompts from a 3-minute screenplay."""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


@dataclass
class Beat:
    beat_id: int
    title: str
    summary: str
    mood: str


@dataclass
class Shot:
    shot_id: int
    beat_id: int
    beat_title: str
    camera: str
    composition: str
    location: str
    lighting: str
    action: str
    emotion: str


class ScriptIngestAgent:
    """Agent 1: cleans input and extracts rough sections."""

    section_header_pattern = re.compile(
        r"(?im)^\s*(?:SCENE\s*\d*\b.*|장면\s*\d*\b.*|#\s*.+)$"
    )

    def run(self, script_text: str) -> List[str]:
        normalized = re.sub(r"\r\n?", "\n", script_text).strip()
        if not normalized:
            raise ValueError("스크립트가 비어 있습니다.")

        headers = list(self.section_header_pattern.finditer(normalized))
        if not headers:
            return [normalized]

        sections: List[str] = []
        for idx, match in enumerate(headers):
            start = match.start()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(normalized)
            section = normalized[start:end].strip()
            if section:
                sections.append(section)

        return sections or [normalized]


class BeatPlannerAgent:
    """Agent 2: converts sections into dramatic beats."""

    mood_cycle = ["긴장", "불안", "결의", "충돌", "여운", "희망"]

    def run(self, sections: List[str]) -> List[Beat]:
        beats: List[Beat] = []
        for idx, section in enumerate(sections, start=1):
            lines = [ln.strip() for ln in section.split("\n") if ln.strip()]
            title = lines[0][:50] if lines else f"Beat {idx}"
            summary = " ".join(lines[:3])[:260]
            beats.append(
                Beat(
                    beat_id=idx,
                    title=title,
                    summary=summary,
                    mood=self.mood_cycle[(idx - 1) % len(self.mood_cycle)],
                )
            )
        return beats


class ShotAllocatorAgent:
    """Agent 3: allocates exactly N shots across beats."""

    def run(self, beats: List[Beat], total_shots: int = 60) -> List[tuple[Beat, int]]:
        if not beats:
            raise ValueError("비트가 없어 쇼트를 배정할 수 없습니다.")

        base = total_shots // len(beats)
        remainder = total_shots % len(beats)
        allocation: List[tuple[Beat, int]] = []
        for i, beat in enumerate(beats):
            count = base + (1 if i < remainder else 0)
            allocation.append((beat, count))
        return allocation


class ShotDesignerAgent:
    """Agent 4: expands beat allocation into shot-level visual descriptions."""

    cameras = ["wide shot", "medium shot", "close-up", "overhead shot", "tracking shot"]
    compositions = ["rule of thirds", "centered framing", "negative space", "symmetrical framing"]
    lightings = ["soft cinematic light", "high contrast noir light", "golden hour backlight", "cold fluorescent light"]
    locations = ["urban alley", "small apartment", "rooftop", "subway platform", "abandoned warehouse"]

    def run(self, allocation: List[tuple[Beat, int]]) -> List[Shot]:
        shots: List[Shot] = []
        shot_id = 1
        for beat, count in allocation:
            for i in range(count):
                shots.append(
                    Shot(
                        shot_id=shot_id,
                        beat_id=beat.beat_id,
                        beat_title=beat.title,
                        camera=self.cameras[(shot_id - 1) % len(self.cameras)],
                        composition=self.compositions[(i + beat.beat_id) % len(self.compositions)],
                        location=self.locations[(beat.beat_id + i) % len(self.locations)],
                        lighting=self.lightings[(shot_id + i) % len(self.lightings)],
                        action=f"핵심 행동: {beat.summary[:80]}",
                        emotion=beat.mood,
                    )
                )
                shot_id += 1
        return shots


class PromptRefinerAgent:
    """Agent 5: writes image-generation-friendly prompts."""

    style_suffix = (
        "ultra-detailed cinematic still, 35mm film look, realistic texture, "
        "dramatic depth of field, 8k, no text, no watermark"
    )

    def run(self, shots: List[Shot]) -> List[str]:
        prompts = []
        for shot in shots:
            prompt = (
                f"Shot {shot.shot_id:02d}, {shot.camera}, {shot.composition}, {shot.location}, "
                f"{shot.lighting}, {shot.action}, 감정 {shot.emotion}, "
                f"장면 제목 '{shot.beat_title}', {self.style_suffix}"
            )
            prompts.append(prompt)
        return prompts


class QAAgent:
    """Agent 6: validates and normalizes final outputs."""

    def run(self, prompts: List[str], expected: int = 60) -> List[str]:
        cleaned = [re.sub(r"\s+", " ", p).strip() for p in prompts if p.strip()]
        if len(cleaned) != expected:
            raise ValueError(f"프롬프트 수가 {expected}개가 아닙니다: {len(cleaned)}개")
        duplicates = len(cleaned) - len(set(cleaned))
        if duplicates > math.floor(expected * 0.1):
            raise ValueError("중복 프롬프트 비율이 너무 높습니다.")
        return cleaned


class SerialPromptPipeline:
    def __init__(self) -> None:
        self.ingest = ScriptIngestAgent()
        self.beat_planner = BeatPlannerAgent()
        self.allocator = ShotAllocatorAgent()
        self.designer = ShotDesignerAgent()
        self.refiner = PromptRefinerAgent()
        self.qa = QAAgent()

    def run(self, script_text: str, total_shots: int = 60) -> dict:
        sections = self.ingest.run(script_text)
        beats = self.beat_planner.run(sections)
        allocation = self.allocator.run(beats, total_shots=total_shots)
        shots = self.designer.run(allocation)
        prompts = self.refiner.run(shots)
        validated = self.qa.run(prompts, expected=total_shots)

        return {
            "meta": {
                "input_sections": len(sections),
                "beats": len(beats),
                "shots": total_shots,
            },
            "beats": [asdict(b) for b in beats],
            "shots": [asdict(s) for s in shots],
            "prompts": validated,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="3분 극영화 스크립트 → 60컷 스타트프레임 프롬프트 생성")
    parser.add_argument("--input", required=True, help="입력 스크립트 .txt 파일")
    parser.add_argument("--output-dir", default="output", help="결과 저장 디렉터리")
    parser.add_argument("--shots", type=int, default=60, help="생성할 총 컷 수")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    script_text = input_path.read_text(encoding="utf-8")
    result = SerialPromptPipeline().run(script_text, total_shots=args.shots)

    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "prompts.txt").write_text(
        "\n".join(result["prompts"]),
        encoding="utf-8",
    )

    print(f"완료: {len(result['prompts'])}개 프롬프트 생성")
    print(f"- JSON: {out_dir / 'result.json'}")
    print(f"- TEXT: {out_dir / 'prompts.txt'}")


if __name__ == "__main__":
    main()
