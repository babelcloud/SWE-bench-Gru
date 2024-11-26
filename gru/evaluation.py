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
def main(mode: int, disable_cache: int, max_workers: int, enable_chunk: bool):
    # Handle parameters
    max_workers, instance_ids, patch_files, enable_chunk = handle_parameters(
        mode, disable_cache, max_workers, enable_chunk
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
    chunk_size = max_workers if enable_chunk else max(n, 1)
    for i in range(0, n, chunk_size):
        print("=" * 50)
        upper_bound = min(i + chunk_size, n)
        if chunk_size > 1 and (upper_bound != i + 1):
            print(
                f"  🔥 Running evaluation for instances {i+1} to {min(i + chunk_size, n)}"
            )
        else:
            print(f"  🔥 Running evaluation instance {i+1}")
        print("=" * 50 + "\n")

        instance_ids_batch = filtered_instance_ids[i : i + chunk_size]
        patch_files_batch = filtered_patch_files[i : i + chunk_size]
        instances_batch = instances[i : i + chunk_size]

        batch_index = i // chunk_size
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
    print(f"📃 Report: gru-result/evaluation/{timestamp}/report.json")
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
    parser.add_argument(
        "--enable-chunk",
        type=bool,
        default=False,
        help="Disable chunking the evaluation into smaller batches",
    )
    args = parser.parse_args()
    main(**vars(args))
