from gru.utils.cache_utils import CacheManager
from gru.utils.evaluation_utils import (
    handle_parameters,
    get_instance,
    update_report,
    write_test_instances,
    write_predictions,
)
from gru.utils.constants import SWE_BENCH_RESULT_PATH
from datetime import datetime
from argparse import ArgumentParser
import json
import shutil

from swebench.harness.run_evaluation import main as run_evaluation

# ================= Configurations =================

DATASET_NAME = "SWE-bench"  # "SWE-bench_Lite"


# ================= Main Functions =================
def main(mode: int, disable_cache: int, max_workers: int):
    # Handle parameters
    max_workers, instance_ids, patch_files = handle_parameters(
        mode, disable_cache, max_workers
    )

    # Handle cache
    timestamp = datetime.now().strftime("%m-%d-%H-%M-%S")
    cache_maneger = CacheManager(DATASET_NAME)

    filtered_instance_ids, filtered_patch_files, cache = (
        cache_maneger.filter_cached_instances(
            instance_ids, patch_files, timestamp, cache_mode=disable_cache
        )
    )

    cache_maneger.write_cache_to_report(cache, timestamp)

    # ================================================ #
    #               RUN EVALUATION                     #
    # ================================================ #
    write_predictions(filtered_instance_ids, filtered_patch_files, timestamp)
    instances = get_instance(DATASET_NAME, filtered_instance_ids)
    write_test_instances(instances, timestamp)

    print("\t\t🔄 Running evaluation")
    print("=" * 50)
    print()

    n = len(instances)
    for i in range(0, n, max_workers):
        print("=" * 50)
        upper_bound = min(i + max_workers, n)
        if max_workers > 1 and (upper_bound != i + 1):
            print(
                f"  🔥 Running evaluation for instances {i+1} to {min(i + max_workers, n)}"
            )
        else:
            print(f"  🔥 Running evaluation instance {i+1}")
        print("=" * 50 + "\n")

        instance_ids_batch = filtered_instance_ids[i : i + max_workers]
        patch_files_batch = filtered_patch_files[i : i + max_workers]
        instances_batch = instances[i : i + max_workers]

        batch_index = i // max_workers
        predictions_path = write_predictions(
            instance_ids_batch, patch_files_batch, timestamp, batch_index, temp=True
        )

        run_evaluation(
            dataset_name=f"princeton-nlp/{DATASET_NAME}",
            split="test",
            instance_ids=instance_ids_batch,
            predictions_path=predictions_path,
            max_workers=min(max_workers, len(instances_batch)),
            force_rebuild=False,
            cache_level="env",
            clean=False,
            open_file_limit=4096,
            run_id=timestamp,
            timeout=1_800,
            test_instances=instances_batch,
        )

        if disable_cache != 1:
            # save the results to the cache
            cache_maneger.refresh_cache()
            cache_maneger.save_instance_result(
                timestamp,
                instance_ids_batch,
                patch_files_batch,
                only_print_res=False,
            )
            # combine reports
            update_report(timestamp)

    # Remove temp files
    temp_folder = SWE_BENCH_RESULT_PATH / timestamp / "temp"
    if temp_folder.exists():
        shutil.rmtree(temp_folder)

    # Output combined result
    with open(SWE_BENCH_RESULT_PATH / timestamp / "report.json", "r") as f:
        report_data = json.load(f)

    print()
    print("=" * 50)
    print(" " * 12, "🎉 Evaluation completed 🎉")
    print(f"📃 Report: gru-result/evalution/{timestamp}/report.json")
    print("=" * 50)

    print(f"Total instances: {report_data.get('total_instances', 0)}")
    print(f"Instances completed: {report_data.get('completed_instances', 0)}")
    print(f"Instances incomplete: {len(report_data.get('incomplete_ids', []))}")
    print(f"Instances resolved: {report_data.get('resolved_instances', 0)}")
    print(f"Instances unresolved: {report_data.get('unresolved_instances', 0)}")
    print(f"Instances with errors: {len(report_data.get('error_ids', []))}")
    print()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--mode", type=int, default=0, help="0: input from file, 1: input manually"
    )
    parser.add_argument(
        "--disable-cache",
        type=int,
        default=0,
        help="0: enable cache, 1: disable cache, 2: disable unsolved instances cache",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=0,
        help="Dataset name: SWE-bench or SWE-bench_Lite",
    )
    args = parser.parse_args()
    main(**vars(args))
