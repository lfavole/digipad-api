import sys

if __package__ is None and not hasattr(sys, "frozen"):
    # direct call of __main__.py
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).absolute().parent.parent))

from digipad import main  # pylint: disable=C0413

if __name__ == "__main__":
    main()
