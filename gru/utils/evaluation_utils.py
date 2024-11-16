from pathlib import Path
from datasets import Dataset, load_dataset, load_from_disk
import requests
from typing import cast
import os
import json

from .constants import (
    ReportInsatnce,
    SWEbenchInstance,
    SWE_BENCH_DATASET_PATH,
    SWE_BENCH_RESULT_PATH,
)


# =============== Handling the parameters ===============
def handle_parameters(
    mode: int, disable_cache: int, max_workers: int
) -> tuple[int, int, int, str, list[str], list[str]]:
    if disable_cache < 0 or disable_cache > 2:
        raise ValueError("Invalid disable_cache value")
    print(
        f"Evaluation of SWE-bench lite ❗️{'without' if disable_cache == 1 else 'with'} cache{' of solved instances' if disable_cache == 2 else ''}❗️\n",
    )

    if max_workers == 0:
        refreshed_max_workers = min(int(0.75 * os.cpu_count()), 24)
    else:
        refreshed_max_workers = max_workers
    print(
        f"🎯 Max workers{' (auto mode)' if max_workers == 0 else ''}: ",
        refreshed_max_workers,
        "\n",
        sep="",
    )

    # ================= Handle patch input =================
    match mode:
        case 0:
            file_path = input("Enter the path of the json file (url or local path): \n")
            instance_ids, patch_files = parse_json(file_path)
        case 1:
            # get instance ids for input, separated by space
            instance_ids = input("Enter instance ids separated by space: \n").split()
            print()
            # get patch file names for input, separated by comma12
            patch_files = []
            for instance_id in instance_ids:
                patch_files.append(input(f"Enter patch file link for {instance_id}: "))
                print()
            # remove empty or unaccessible patch files
            instance_ids, patch_files = preprocess_data(instance_ids, patch_files)
        case _:
            raise ValueError("Invalid mode")

    return refreshed_max_workers, instance_ids, patch_files


# ================= Data Preprocessing =================


def get_instance(dataset_name: str, instance_ids: list[str]) -> list[SWEbenchInstance]:
    local_path = SWE_BENCH_DATASET_PATH / f"local_{dataset_name}"

    if os.path.exists(local_path):
        dataset = cast(Dataset, load_from_disk(local_path))
    else:
        dataset = cast(
            Dataset, load_dataset(f"princeton-nlp/{dataset_name}", split="test")
        )

        load_dataset(f"princeton-nlp/{dataset_name}")
        # Save the dataset to a local directory
        dataset.save_to_disk(local_path)

    datset = [cast(SWEbenchInstance, instance) for instance in dataset]

    instances = []
    for instance in datset:
        if instance["instance_id"] in instance_ids:
            instances.append(instance)

    return instances


def write_test_instances(
    instances: list[SWEbenchInstance], timestamp: str, temp: bool = False
):
    history_fold = SWE_BENCH_RESULT_PATH / timestamp
    if temp:
        full_path = history_fold / "temp" / "test_instances.json"
    else:
        full_path = history_fold / "test_instances.json"

    try:
        # make a directory for the history
        os.makedirs(history_fold, exist_ok=True)

        with open(full_path, "w") as f:
            json.dump(instances, f, indent=4)

        return full_path
    except Exception as e:
        print(f"Error: {e}")


def write_predictions(
    instance_ids: list[str],
    patchFileList: list[str],
    timestamp: str,
    batch_index: int = -1,
    temp: bool = False,
):
    history_fold = SWE_BENCH_RESULT_PATH / timestamp
    filename = (
        f"predictions_{batch_index}.json" if batch_index != -1 else "predictions.json"
    )
    if temp:
        full_path = history_fold / "temp" / filename
    else:
        full_path = history_fold / filename

    try:
        # make a directory for the history
        full_path.parent.mkdir(parents=True, exist_ok=True)

        predictions = []
        for instance_id, patchFile in zip(instance_ids, patchFileList):
            predictions.append(
                {
                    "instance_id": instance_id,
                    "model_patch": patchFile,
                    "model_name_or_path": "gru-ai",
                }
            )

        with open(full_path, "w") as f:
            json.dump(predictions, f, indent=4)

        return str(full_path)
    except Exception as e:
        print(f"Error: {e}")


def read_patch(patchFile: str) -> str:
    # patchFile is a link of patch file
    try:
        if Path(patchFile).exists():
            with open(patchFile, "r") as f:
                patch_content = f.read()
            return patch_content
        else:
            response = requests.get(patchFile)
            response.raise_for_status()  # Check if the request was successful
            return response.text
    except Exception as e:
        print(f"Error fetching the patch file: {e}")
        return None


def preprocess_data(
    instance_ids: list[str], patchFileList: list[str]
) -> tuple[list[str], list[str]]:

    new_instance_ids = []
    new_patch_files = []
    for ins, patch in zip(instance_ids, patchFileList):
        patch_file = read_patch(patch)
        if patch_file is None:
            print(f"Error fetching the patch file for {ins}, skipping...")
            continue
        new_instance_ids.append(ins)
        new_patch_files.append(patch_file)

    return new_instance_ids, new_patch_files


def parse_json(file_path: str) -> tuple[list[str], list[str]]:
    try:
        if Path(file_path).exists():
            with open(file_path, "r") as f:
                json_file = json.load(f)
        else:
            response = requests.get(file_path)
            response.raise_for_status()  # Check if the request was successful
            json_file = response.json()

        instance_ids = []
        patch_files = []
        for instance in json_file:
            if instance.get("patch") is None:
                continue
            instance_ids.append(instance["instance_id"])
            patch_files.append(instance["patch"])

        return instance_ids, patch_files
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the json file from {file_path} {e}")
        return {}


def combine_reports(
    report1: ReportInsatnce, report2: ReportInsatnce | None
) -> ReportInsatnce:
    if report2 is None:
        return report1

    if set(report1["submitted_ids"]) & set(report2["submitted_ids"]):
        report1["completed_ids"] = list(
            set(report1["completed_ids"]).intersection(set(report2["completed_ids"]))
        )
        report1["incomplete_ids"] = list(
            set(report1["incomplete_ids"]).intersection(set(report2["incomplete_ids"]))
        )
        report1["empty_patch_ids"] = list(
            set(report1["empty_patch_ids"]).intersection(
                set(report2["empty_patch_ids"])
            )
        )
        report1["submitted_ids"] = list(
            set(report1["submitted_ids"]).intersection(set(report2["submitted_ids"]))
        )
        report1["resolved_ids"] = list(
            set(report1["resolved_ids"]).intersection(set(report2["resolved_ids"]))
        )
        report1["unresolved_ids"] = list(
            set(report1["submitted_ids"]) - set(report1["resolved_ids"])
        )
        report1["error_ids"] = list(
            set(report1["error_ids"]).intersection(set(report2["error_ids"]))
        )
        report1["unstopped_containers"] = list(
            set(report1["unstopped_containers"]).intersection(
                set(report2["unstopped_containers"])
            )
        )
        report1["unremoved_images"] = list(
            set(report1["unremoved_images"]).intersection(
                set(report2["unremoved_images"])
            )
        )

        report1["total_instances"] = len(report1["submitted_ids"])
        report1["submitted_instances"] = len(report1["submitted_ids"])
        report1["completed_instances"] = len(report1["completed_ids"])
        report1["resolved_instances"] = len(report1["resolved_ids"])
        report1["unresolved_instances"] = len(report1["unresolved_ids"])
        report1["empty_patch_instances"] = len(report1["empty_patch_ids"])
        report1["error_instances"] = len(report1["error_ids"])
        report1["unstopped_instances"] = len(report1["unstopped_containers"])
    else:
        report1["total_instances"] += report2["total_instances"]
        report1["submitted_instances"] += report2["submitted_instances"]
        report1["completed_instances"] += report2["completed_instances"]
        report1["resolved_instances"] += report2["resolved_instances"]
        report1["unresolved_instances"] += report2["unresolved_instances"]
        report1["empty_patch_instances"] += report2["empty_patch_instances"]
        report1["error_instances"] += report2["error_instances"]
        report1["unstopped_instances"] += report2["unstopped_instances"]

        report1["completed_ids"].extend(report2["completed_ids"])
        report1["incomplete_ids"].extend(report2["incomplete_ids"])
        report1["empty_patch_ids"].extend(report2["empty_patch_ids"])
        report1["submitted_ids"].extend(report2["submitted_ids"])
        report1["resolved_ids"].extend(report2["resolved_ids"])
        report1["unresolved_ids"].extend(report2["unresolved_ids"])
        report1["error_ids"].extend(report2["error_ids"])
        report1["unstopped_containers"].extend(report2["unstopped_containers"])
        report1["unremoved_images"].extend(report2["unremoved_images"])

    return report1


def update_report(timestamp: str):
    foler_path = Path("gru-result/evalution") / timestamp
    report_path = foler_path / "report.json"

    if report_path.exists():
        with open(report_path, "r") as f:
            final_report: ReportInsatnce = json.load(f)
    else:
        final_report = None

    all_files = list((foler_path / "temp").glob("*"))
    for file in all_files:
        if (
            file.is_file()
            and file.name.startswith("report_")
            and file.suffix == ".json"
        ):
            with open(file, "r") as f:
                json_file: ReportInsatnce = json.load(f)
                final_report = combine_reports(json_file, final_report)
                file.unlink()

    with open(report_path, "w") as f:
        json.dump(final_report, f, indent=4)
