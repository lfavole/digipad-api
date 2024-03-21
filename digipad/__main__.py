import sys
from pathlib import Path

if __package__ is None and not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).absolute().parent.parent))

import digipad  # pylint: disable=C0413

if __name__ == "__main__":
    digipad.main()
