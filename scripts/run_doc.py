import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="DOC baseline entry point placeholder.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.parse_args()
    raise SystemExit(
        "DOC was skipped in this setup because the user confirmed local DOC experiments already exist and are complete."
    )


if __name__ == "__main__":
    main()
