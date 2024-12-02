from pathlib import Path
import shutil
from typing import TypedDict
import json
import hashlib

from gru.utils.constants import ReportInsatnce

CACHE_FOLDER = Path("gru/dataset/cache")
RESULTS_FOLDER = Path("gru-result/evaluation")


class InstanceCache(TypedDict):
    instance_id: str
    passed: bool
    patch: str
    pass_to_pass: str
    fail_to_pass: str
    timestamp: str


class CacheMap(TypedDict):
    instances: dict[str, InstanceCache]  # (instance_id, hashed_patch)


class CacheManager:
    def __init__(
        self, dataset_name: str = "SWE-bench", mode: int = 0
    ):  # "SWE-bench" or "SWE-bench_Lite"
        self.mode = mode
        self.cache_path = CACHE_FOLDER / f"cache_{dataset_name.lower()}_v4.json"
        self.cache = self.load_cache()

    def load_cache(self) -> CacheMap:
        if self.cache_path.exists():
            with open(self.cache_path, "r") as f:
                return json.load(f)
        else:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_map = CacheMap(instances={})
            with open(self.cache_path, "w") as f:
                json.dump(cache_map, f)
            return cache_map

    def refresh_cache(self):
        self.cache = self.load_cache()

    def filter_cached_instances(
        self,
        instance_ids: list[str],
        patch_files: list[str],
        timestamp: str,
        cache_mode: int,
    ) -> tuple[list[str], list[str], list[InstanceCache]]:

        if cache_mode == 1:
            return instance_ids, patch_files, []

        skip_unsolved = cache_mode == 2

        filtered_instance_ids = []
        filtered_patch_files = []
        cache = []

        print("\n", "=" * 50, sep="")
        print("\t\tCached Instances")
        print("=" * 50, "\n")

        count = 0

        for instance_id, patch in zip(instance_ids, patch_files):
            patch_hash = self.generate_hash(patch)
            key = instance_id + "-" + patch_hash
            if key not in self.cache["instances"].keys() or (
                skip_unsolved and self.cache["instances"][key]["passed"] is False
            ):
                filtered_instance_ids.append(instance_id)
                filtered_patch_files.append(patch)
            else:
                count += 1
                cache.append(self.cache["instances"][key])
                self.print_instance_result(instance_id, key)
                # load the cached logs
                self.load_cached_log(timestamp, [cache[-1]])

        if count == 0:
            print("\tNo cached instances found.\n")

        print("=" * 50)

        return filtered_instance_ids, filtered_patch_files, cache

    def load_cached_log(self, timestamp: str, cache: list[InstanceCache]):
        for instance_record in cache:
            target_folder = (
                RESULTS_FOLDER / timestamp / "log" / instance_record["instance_id"]
            )
            source_folder = (
                RESULTS_FOLDER
                / instance_record["timestamp"]
                / "log"
                / instance_record["instance_id"]
            )
            # copy all contents from source_folder to target_folder
            shutil.copytree(source_folder, target_folder, symlinks=True)

    def save_instance_result(
        self,
        timestamp: str,
        instance_ids: list[str],
        filtered_patch_files: list[str],
        only_print_res: bool = False,
    ):
        INSTANCE_FOLDER = RESULTS_FOLDER / timestamp / "log"
        if len(instance_ids) == 0:
            return
        print("\n")
        print("-" * 50)
        print("\t\tEvaluation Results")
        print("-" * 50, "\n")

        for instance_id, patch in zip(instance_ids, filtered_patch_files):
            instance_report = INSTANCE_FOLDER / instance_id / "report.json"
            print(instance_report)
            if instance_report.exists():
                with open(instance_report, "r") as f:
                    instance_result_json = json.load(f)
                    result = instance_result_json.get(instance_id, {})

                    if result.get("patch_successfully_applied", False) is False:
                        continue

                    key = instance_id + "-" + self.generate_hash(patch)
                    pass_to_pass, fail_to_pass = self.get_pass_info(result)

                    instance_record = InstanceCache(
                        instance_id=instance_id,
                        passed=result.get("resolved", False),
                        pass_to_pass=pass_to_pass,
                        fail_to_pass=fail_to_pass,
                        patch=patch,
                        timestamp=timestamp,
                    )
                    if only_print_res is False:
                        self.cache["instances"][key] = instance_record
                    self.print_instance_result(instance_id, key, cached=False)
        if only_print_res is False:
            self.save_cache()
        print("\n")

    def get_pass_info(self, result: dict) -> tuple[str, str]:
        pass_to_pass = result.get("tests_status", {}).get("PASS_TO_PASS")
        fail_to_pass = result.get("tests_status", {}).get("FAIL_TO_PASS")

        if not pass_to_pass or not fail_to_pass:
            return "0 / 0", "0 / 0"

        pass_to_pass_str = f'{len(pass_to_pass["success"])} / {len(pass_to_pass["success"]) + len(pass_to_pass["failure"])}'
        fail_to_pass_str = f'{len(fail_to_pass["success"])} / {len(fail_to_pass["success"]) + len(fail_to_pass["failure"])}'

        return pass_to_pass_str, fail_to_pass_str

    def save_cache(self):
        with open(self.cache_path, "w") as f:
            json.dump(self.cache, f)

    def generate_hash(self, input_string: str) -> str:
        # Create a new hash object using SHA256
        hash_object = hashlib.sha256()

        # Update the hash object with the bytes of the input string
        hash_object.update(input_string.encode("utf-8"))

        # Get the hexadecimal representation of the hash
        hash_value = hash_object.hexdigest()

        return hash_value

    def print_instance_result(self, instance_id: str, key: str, cached: bool = True):
        instance_record = self.cache["instances"].get(key, {})

        if not instance_record:
            return
        if instance_record["passed"]:
            print(f"✅ Instance {instance_id}{' already' if cached else ''} passed!\n")
        else:
            print(
                f"❌ Instance {instance_id} failed with \n   {self.get_accuracy_emoji(instance_record['pass_to_pass'])} pass_to_pass: {instance_record['pass_to_pass']}\n   {self.get_accuracy_emoji(instance_record['fail_to_pass'])} fail_to_pass: {instance_record['fail_to_pass']}\n"
            )

    def get_accuracy_emoji(self, accuracy: str) -> str:
        try:
            res = int(eval(accuracy) * 100)
            if res == 100:
                return "🌕"
            elif res > 70:
                return "🌖"
            elif res > 40:
                return "🌗"
            elif res > 10:
                return "🌘"
            else:
                return "🌑"
        except:
            return "🌑"

    def write_cache_to_report(self, cache: list[InstanceCache], timestamp: str):
        report = ReportInsatnce(
            total_instances=len(cache),
            submitted_instances=len(cache),
            completed_instances=len(cache),
            resolved_instances=0,
            unresolved_instances=0,
            empty_patch_instances=0,
            error_instances=0,
            unstopped_instances=0,
            completed_ids=[instance["instance_id"] for instance in cache],
            incomplete_ids=[],
            empty_patch_ids=[],
            submitted_ids=[instance["instance_id"] for instance in cache],
            resolved_ids=[],
            unresolved_ids=[],
            error_ids=[],
            unstopped_containers=[],
            unremoved_images=[],
            schema_version=2,
        )

        resolved_ids = [
            instance["instance_id"] for instance in cache if instance["passed"]
        ]
        unresolved_ids = [
            instance["instance_id"] for instance in cache if not instance["passed"]
        ]

        report["resolved_instances"] = len(resolved_ids)
        report["unresolved_instances"] = len(unresolved_ids)
        report["resolved_ids"] = resolved_ids
        report["unresolved_ids"] = unresolved_ids

        report_path = RESULTS_FOLDER / timestamp / "report.json"

        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f)
