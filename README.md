# SWE-bench Evaluation Helper

This repository contains a helper script to evaluate model predictions on the SWE-bench dataset.

Using `ssh ubuntu@35.212.134.229` to connect to the evaluation server.

# Usage

## Setup the environment

0. Pre-requisites

    - Docker Desktop (with `Allow the default Docker socket to be used (requires password)` selected, you can find this option in Docker Desktop -> Settings -> Advanced)
    - Python
    - pip

1. run following commands in terminal

    ```bash
      python3 -m venv .venv
      source .venv/bin/activate
      pip install -e .
    ```

## Run following command to start the evaluation script

### mode 0 (default)

Input the path (or url) of the combined patch file and the instance id to evaluate the model prediction.

```bash
  python -m gru.evaluation
```

### mode 1

Input instance ids and patch file links manually according to instructions.

```bash
  python -m gru.evaluation --mode 1
```

## Disable the Cache

If you want to disable the cache, you can set the `--disable-cache` flag.

| disable-cache flag value | Description                               |
| ------------------------ | ----------------------------------------- |
| 0                        | Enable the cache (default)                |
| 1                        | Disable the cache                         |
| 2                        | disable the cache of unresolved instances |

```bash
  python -m gru.evaluation --disable-cache 1

  # or
  python -m gru.evaluation --mode 1 --disable-cache 2
```

## Modify Max Workers

You can modify the number of workers by setting the `--max-workers` flag, default is 0 (auto mode).

| max-workers flag value | Description                               |
| ---------------------- | ----------------------------------------- |
| 0                      | Auto mode (default), 3/4 of the CPU cores |
| 1                      | Single worker                             |
| k (k>0)                | k workers                                 |

```bash
  python -m gru.evaluation --max-workers 2
```

## Enable Chunk Mode

You can enable the chunk mode by setting the `--enable-chunk` flag, default is False (disable).

```bash
  python -m gru.evaluation --enable-chunk false
```

# Evaluation Results

All of the evaluation results will be saved in the `gru-result/evaluation` directory. Organized by timestamp (Month-Day-Hour-Minute-Second), each evaluation will be saved in a separate directory.

-   `report.json`: contains all evaluation results

-   `predictions.json`: contains the model predictions for each instance
-   `test-instances.json`: contains the test instances

-   `log/`: contains the log file of the evaluation, includes some details of the evaluation process, organized by instance id

# Sync with SWE-bench Official Code

1. Switch to `SWE-bench-official` branch, click `Sync fork` button on the upper-right corner
2. Rebase updates from `SWE-bench-official` branch to `main` branch
