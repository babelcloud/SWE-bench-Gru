from argparse import ArgumentParser
from typing import TypedDict
import re
import json


class HitReate(TypedDict):
    hit: bool
    partial: bool
    miss: bool


class PhaseInfo(TypedDict):
    files: list[str]
    hit_rate: HitReate
    expanded: bool


class RowInfo(TypedDict):
    instance_id: str
    target: list[str]
    search_result: PhaseInfo
    interested_files: PhaseInfo
    file_change_plan: PhaseInfo
    patch_file: PhaseInfo


def extrack_links(text: str):
    pattern = r"\[([^\]]+)\]\((https?://[^\)]+)\)"
    matches = re.findall(pattern, text)
    link_dict = {
        (title if not title.endswith(".patch") else "patch"): link
        for title, link in matches
    }
    return link_dict


def get_target_from_patch(diff_output) -> list[str]:
    pattern = r"\s+a\/(?P<source>[^\s]+)"
    matches = re.findall(pattern, diff_output)
    matches_unique = list(set(matches))
    return matches_unique


def extract_file_list(
    file_dict: dict, exportedAssets: dict
) -> tuple[list[str], list[str], list[str]]:
    interested_files = []
    file_change_plan = []
    patch_file = []

    interested_files_link = file_dict.get("interested-files.yml", "Not Found")
    file_change_plan_link = file_dict.get("file-change-plan.yml", "Not Found")
    patch_file_link = file_dict.get("patch", "Not Found")

    if interested_files_link != "Not Found":
        interested_files = exportedAssets.get(interested_files_link, "")
        # Regular expression to match the paths
        pattern = r"- path: (/testbed/[^\n]+)\n"
        # Finding all matches
        matches = re.findall(pattern, interested_files)
        interested_files = [m.removeprefix("/testbed/") for m in matches]

    if file_change_plan_link != "Not Found":
        file_change_plan = exportedAssets.get(file_change_plan_link, "")
        # Regular expression to match the paths
        pattern = r"- filePath: (/testbed/[^\n]+)\n"
        # Finding all matches
        matches = re.findall(pattern, file_change_plan)
        file_change_plan = [m.removeprefix("/testbed/") for m in matches]

    if patch_file_link != "Not Found":
        patch_file = exportedAssets.get(patch_file_link)
        patch_file = get_target_from_patch(patch_file)

    return interested_files, file_change_plan, patch_file


def analyze_row(row: dict):
    instance_id = row.get("title")
    if not instance_id:
        raise ValueError("Invalid row, missing instance id")

    deatils = row.get("details", [])
    detail = deatils[0]

    exportedConversation = detail.get("exportedConversation", {})

    jobs = exportedConversation.get("jobs", [])

    # search_results
    job = jobs[0] if jobs else {}
    result = json.loads(job.get("result", {}))
    searchResults = result.get("searchResults", [])
    search_result = [
        res
        for sr in searchResults
        if (res := sr.removeprefix("filePath: /testbed/")) != "No Files Found"
    ]

    # intermidiate results
    summary = job.get("summary", "")
    file_dict = extrack_links(summary)

    exportedAssets = detail.get("exportedAssets", {})
    interested_files, file_change_plan, patch_file = extract_file_list(
        file_dict, exportedAssets
    )

    return instance_id, search_result, interested_files, file_change_plan, patch_file


def main(row_file_path: str):
    try:
        if not row_file_path.endswith(".json"):
            raise ValueError(
                "Invalid file format, expected .json, got .{}".format(
                    row_file_path.split(".")[-1]
                )
            )
        with open("raw-analysis/targets.json", "r") as f:
            targets = json.load(f)

        res = {}
        all_search_hit = 0
        all_search_partial = 0
        all_interested_hit = 0
        all_interested_partial = 0
        all_interested_expanded = 0
        all_interested_expanded_and_target = 0
        all_file_change_hit = 0
        all_file_change_partial = 0
        all_file_change_expanded = 0
        all_file_change_expanded_and_target = 0
        all_patch_hit = 0
        all_patch_partial = 0
        all_patch_expanded = 0
        all_patch_expanded_and_target = 0

        with open(row_file_path, "r") as f:
            data = json.load(f)
            rows = data["rows"]
            for row in rows:
                (
                    instance_id,
                    search_result,
                    interested_files,
                    file_change_plan,
                    patch_file,
                ) = analyze_row(row)
                target = targets.get(instance_id)

                if not target:
                    continue

                # Search Result
                seach_hit = set(target) <= set(search_result)
                search_partial = len(set(target).intersection(set(search_result))) > 0
                if seach_hit and not search_partial:
                    print(instance_id, target, search_result)
                search_miss = len(set(target).intersection(set(search_result))) == 0
                all_search_hit += int(seach_hit)
                all_search_partial += int(search_partial)
                search_result_obj = PhaseInfo(
                    files=search_result,
                    hit_rate={
                        "hit": seach_hit,
                        "partial": search_partial,
                        "miss": search_miss,
                    },
                    expanded=False,
                )

                # Interested Files
                interested_hit = set(target) <= set(interested_files)
                interested_partial = (
                    len(set(target).intersection(set(interested_files))) > 0
                )
                interested_miss = (
                    len(set(target).intersection(set(interested_files))) == 0
                )
                interested_expand = len(set(interested_files) - set(search_result)) > 0
                all_interested_hit += int(interested_hit)
                all_interested_partial += int(interested_partial)
                all_interested_expanded += int(interested_expand)
                all_interested_expanded_and_target += 1 if (search_miss and set(target) <= (set(interested_files) - set(search_result))) else 0

                interested_files_obj = PhaseInfo(
                    files=interested_files,
                    hit_rate={
                        "hit": interested_hit,
                        "partial": interested_partial,
                        "miss": interested_miss,
                    },
                    expanded=interested_expand,
                )

                # File Change Plan
                file_change_hit = set(target) <= set(file_change_plan)
                file_change_partial = (
                    len(set(target).intersection(set(file_change_plan))) > 0
                )
                file_change_miss = (
                    len(set(target).intersection(set(file_change_plan))) == 0
                )
                file_change_expand = (
                    len(set(file_change_plan) - set(interested_files)) > 0
                )
                all_file_change_hit += int(file_change_hit)
                all_file_change_partial += int(file_change_partial)
                all_file_change_expanded += int(file_change_expand)
                all_file_change_expanded_and_target += 1 if (interested_miss and set(target) <= (set(file_change_plan) - set(interested_files))) else 0

                file_change_plan_obj = PhaseInfo(
                    files=file_change_plan,
                    hit_rate={
                        "hit": file_change_hit,
                        "partial": file_change_partial,
                        "miss": file_change_miss,
                    },
                    expanded=file_change_expand,
                )

                # Patch File
                patch_hit = set(target) <= set(patch_file)
                patch_partial = len(set(target).intersection(set(patch_file))) > 0
                patch_miss = len(set(target).intersection(set(patch_file))) == 0
                patch_expand = len(set(patch_file) - set(file_change_plan)) > 0
                all_patch_hit += int(patch_hit)
                all_patch_partial += int(patch_partial)
                all_patch_expanded += int(patch_expand)
                all_patch_expanded_and_target += 1 if (file_change_miss and set(target) <= (set(patch_file) - set(file_change_plan))) else 0

                patch_file_obj = PhaseInfo(
                    files=patch_file,
                    hit_rate={
                        "hit": patch_hit,
                        "partial": patch_partial,
                        "miss": patch_miss,
                    },
                    expanded=patch_expand,
                )

                res[instance_id] = RowInfo(
                    instance_id=instance_id,
                    target=target,
                    search_result=search_result_obj,
                    interested_files=interested_files_obj,
                    file_change_plan=file_change_plan_obj,
                    patch_file=patch_file_obj,
                )

            with open("raw-analysis/analysis.json", "w") as f:
                json.dump(res, f, indent=4)

            print("Search Result")
            print(f"Hit: {all_search_hit} ({all_search_hit / 3}%)")
            print(f"Partial: {all_search_partial}")
            print()
            print("Interested Files")
            print(f"Hit: {all_interested_hit} ({all_interested_hit / 3}%)")
            print(f"Partial: {all_interested_partial}")
            print(f"Expanded: {all_interested_expanded}")
            print(f"Expanded and included target file: {all_interested_expanded_and_target}")
            print()
            print("File Change Plan")
            print(f"Hit: {all_file_change_hit} ({all_file_change_hit / 3}%)")
            print(f"Partial: {all_file_change_partial}")
            print(f"Expanded: {all_file_change_expanded}")
            print(f"Expanded and included target file: {all_file_change_expanded_and_target}")
            print()
            print("Patch File")
            print(f"Hit: {all_patch_hit} ({all_patch_hit / 3}%)")
            print(f"Partial: {all_patch_partial}")
            print(f"Expanded: {all_patch_expanded}")
            print(f"Expanded and included target file: {all_patch_expanded_and_target}")
            print()

    except Exception as e:
        raise e


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--row_file_path",
        default="raw-analysis/raw.json",
        type=str,
        help="Path to the row file",
    )
    args = parser.parse_args()
    main(**vars(args))
