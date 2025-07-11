# config/schema.py
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict

@dataclass
class PromptFlowConfig:
    job_match: str = "flow_jobposting"
    page_classifier: str = "flow_pagecateg"

@dataclass
class AppConfig:
    base_data_dir: str = "data/01_fetch_serps"
    run_format: str = "run_{run_uid}"
    default_query: str = "Data Scientist"
    default_location: str = "Remote"
    result_limit: int = 10
    promptflow: PromptFlowConfig = field(default_factory=PromptFlowConfig)
    debug: bool = True

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_json(path: Path):
        import json
        if not path.exists():
            return AppConfig()
        data = json.loads(path.read_text())
        return AppConfig(
            base_data_dir=data.get("base_data_dir", "data/01_fetch_serps"),
            run_format=data.get("run_format", "run_{run_uid}"),
            default_query=data.get("default_query", "Data Scientist"),
            default_location=data.get("default_location", "Remote"),
            result_limit=int(data.get("result_limit", 10)),
            promptflow=PromptFlowConfig(**data.get("promptflow", {})),
            debug=bool(data.get("debug", True))
        )


