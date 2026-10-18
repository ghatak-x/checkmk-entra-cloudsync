import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_LITERAL_STRINGS = [
    "cloudsync.test",
    "cmkcs-test01",
    "cmkcs-test02",
    "cmkcs-test03",
    "10.204.3.",
    "930cd5f6-c617-4c74-866a-50e56abdaf5d",
    "47d306ac-cfc7-4655-827a-c7cefa331c5d",
]

FORBIDDEN_PATTERNS = [
    r"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----",
    r"client_secret\s*=\s*['\"][^'\"]+['\"]",
    r"/root/",
]


def test_no_lab_values_or_embedded_secrets():
    roots = [ROOT / "cmk_addons", ROOT / "agents", ROOT / "docs", ROOT / "README.md"]
    paths = []
    for root in roots:
        if root.is_file():
            paths.append(root)
        else:
            paths.extend(path for path in root.rglob("*") if path.is_file())

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for value in FORBIDDEN_LITERAL_STRINGS:
            assert value not in text, f"lab value {value!r} found in {path}"
        for pattern in FORBIDDEN_PATTERNS:
            assert re.search(pattern, text, re.IGNORECASE) is None, f"{pattern} found in {path}"
