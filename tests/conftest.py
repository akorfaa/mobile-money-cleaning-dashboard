import sys
from pathlib import Path

# So tests can `from scripts.clean import ...` regardless of where pytest is
# invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
