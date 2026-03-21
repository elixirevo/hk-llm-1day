from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.pipeline import run_interview_question_pipeline


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate interview questions from a JD and personal statement.")
    parser.add_argument("--jd", default="JD-sample.md", help="Path to the JD markdown file.")
    parser.add_argument("--essay", default="essay-sample.md", help="Path to the personal statement markdown file.")
    parser.add_argument(
        "--output",
        choices=["report", "json"],
        default="report",
        help="Choose the final output format.",
    )
    args = parser.parse_args()

    result = run_interview_question_pipeline(
        jd_text=_read_text(args.jd),
        essay_text=_read_text(args.essay),
    )

    if args.output == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(result["phase5_report"])


if __name__ == "__main__":
    main()
