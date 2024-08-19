from typing import TypedDict
from pathlib import Path


# Constants - Task Instance Class
class SWEbenchInstance(TypedDict):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: str
    PASS_TO_PASS: str
    environment_setup_commit: str


class ReportInsatnce(TypedDict):
    total_instances: int
    submitted_instances: int
    completed_instances: int
    resolved_instances: int
    unresolved_instances: int
    empty_patch_instances: int
    error_instances: int
    unstopped_instances: int
    completed_ids: list[str]
    incomplete_ids: list[str]
    empty_patch_ids: list[str]
    submitted_ids: list[str]
    resolved_ids: list[str]
    unresolved_ids: list[str]
    error_ids: list[str]
    unstopped_containers: list[str]
    unremoved_images: list[str]
    schema_version: int


SWE_BENCH_DATASET_PATH = Path("gru/dataset/swe-bench")
SWE_BENCH_RESULT_PATH = Path("gru-result/evalution")
