import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="w/oMW baseline placeholder.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.parse_args()
    raise SystemExit(
        "w/oMW is not implemented here because the user requested that baselines without an independent official codebase be skipped."
    )


if __name__ == "__main__":
    main()
