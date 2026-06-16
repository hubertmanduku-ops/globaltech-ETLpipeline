# ================================================================
# run.py — Pipeline Entry Point
# ================================================================
# This is the file you run to execute the entire ETL pipeline.
# Everything starts here.
#
# HOW TO RUN (from the teaching-project/ folder):
#   python run.py
#
# WHAT WILL HAPPEN:
#   1. The ETLPipeline object is created
#   2. raw-data.csv is loaded from data/raw/
#   3. Data quality checks run — problems are reported
#   4. Cleaning transformations run — nulls filled, duplicates removed
#   5. processed-data.csv is saved to data/processed/
#   6. A full report is printed to the terminal
#
# THE if __name__ == "__main__" GUARD:
# ──────────────────────────────────────
# This block only runs when you execute this file directly:
#   python run.py          ← __name__ is "__main__" → runs main()
#
# If another file imports from run.py:
#   from run import something  ← __name__ is "run" → does NOT run main()
#
# Without this guard, importing from run.py would accidentally
# execute the pipeline. The guard prevents that.
# This is a Python best practice — every entry point file should have it.
# ================================================================

import sys
import pathlib

# Add the project root to the Python path so we can import config and src modules
_root = pathlib.Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import INDUSTRY, logger
from src.etl_pipeline import ETLPipeline


def main() -> None:
    """
    Run the complete ETL pipeline.

    We put the logic inside main() rather than at the module level
    so that this file can be imported without triggering execution.
    """

    # Banner — tells the user what is about to run
    logger.info("=" * 55)
    logger.info(f"  MODULE 05 — ETL PIPELINE STARTING")
    logger.info(f"  Industry:  {INDUSTRY}")
    logger.info("=" * 55)

    # Create the pipeline object
    # ETLPipeline.__init__() runs here — sets up paths and state
    pipeline = ETLPipeline()

    # Log what we created — calls ETLPipeline.__str__()
    logger.info(f"Pipeline ready: {pipeline}")

    # Run the full pipeline using method chaining
    # Each method:
    #   1. Does its work
    #   2. Updates self._status
    #   3. Returns self so the next method can chain on
    #
    # If validate() finds a CRITICAL issue, it raises RuntimeError
    # and execution stops here — the remaining steps do not run.
    (
        pipeline
        .extract()       # E: load raw-data.csv
        .validate()      # V: check data quality (stops on CRITICAL)
        .transform()     # T: fix nulls, duplicates, types, add flags
        .load()          # L: save processed-data.csv
        .report()        # print the complete results
    )

    logger.info(f"Pipeline complete: {pipeline}")


if __name__ == "__main__":
    main()
