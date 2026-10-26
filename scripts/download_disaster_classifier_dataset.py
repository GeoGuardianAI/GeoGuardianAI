from __future__ import annotations

import argparse


DATASET_ID = "varpit94/disaster-images-dataset"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the Kaggle disaster image classification dataset.")
    parser.add_argument(
        "--cache-dir",
        help="Optional KaggleHub cache directory. Defaults to KaggleHub's configured cache.",
    )
    args = parser.parse_args()

    import kagglehub

    if args.cache_dir:
        kagglehub.set_cache_dir(args.cache_dir)
    path = kagglehub.dataset_download(DATASET_ID)
    print(f"Dataset downloaded to: {path}")
    print("Use that path as --data-dir when running train_disaster_classifier.py.")


if __name__ == "__main__":
    main()
