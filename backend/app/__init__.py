from pathlib import Path

_legacy_root = Path(__file__).resolve().parent.parent / "legacy_app"
if _legacy_root.exists():
    __path__.append(str(_legacy_root))
