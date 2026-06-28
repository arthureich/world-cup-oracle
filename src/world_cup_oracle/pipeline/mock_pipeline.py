from __future__ import annotations

import json
from typing import Any

from world_cup_oracle.pipeline.outputs import build_mock_outputs


def run_mock_pipeline() -> dict[str, Any]:
    outputs = build_mock_outputs()

    return {
        "elo": outputs["ratings_elo.parquet"],
        "tsi_pre": outputs["tsi_pre_cup.parquet"],
        "matches": outputs["match_probabilities.parquet"],
    }


def main() -> None:
    print(json.dumps(run_mock_pipeline(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
