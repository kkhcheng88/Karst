"""One parameterized CLI for any validated offline research bundle."""
import argparse
import sys

from .packet import load_bundle
from .calculations import calculate
from .publish import publish
from .schema import ContractError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="Directory with packet/evidence/research JSON and source assets")
    parser.add_argument("--output", help="Immutable release parent directory")
    parser.add_argument("--previous-publication-id")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only and not args.output:
        parser.error("--output is required unless --validate-only")
    try:
        if args.validate_only:
            _, _, research = load_bundle(args.bundle)
            calculate(research)
            print("Bundle contracts, references and calculation inputs validated.")
        else:
            path = publish(args.bundle, args.output,
                           previous_publication_id=args.previous_publication_id)
            print(path.resolve() / "index.html")
        return 0
    except (ContractError, OSError) as exc:
        print(f"karst: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
