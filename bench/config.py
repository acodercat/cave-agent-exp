from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATASETS_DIR = PROJECT_ROOT / "datasets" / "dataset_new"
EVALS_DIR = PROJECT_ROOT / "evals"    # cases imported from FinBench
CASES_DIR = PROJECT_ROOT / "cases"    # cases written here
BENCHMARKS_JSON = PROJECT_ROOT / "benchmarks.json"
CASE_TAXONOMY_PATH = PROJECT_ROOT / "metadata" / "case_taxonomy.json"
MODELS_TOML = PROJECT_ROOT / "models.toml"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
