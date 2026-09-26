"""Central configuration: paths and secrets. Secrets are read from environment
variables (populated from a local .env via python-dotenv) and never hard-coded.
"""
from __future__ import annotations

import os
import platform
import ssl
from pathlib import Path

from dotenv import load_dotenv

try:
    import truststore
    # Use the OS certificate store instead of the bundled certifi one. Needed on
    # machines where TLS-intercepting software (e.g. some antivirus web shields)
    # installs its own root CA into the OS trust store but not into certifi's.
    # Fixes plain `requests`/`urllib` calls (news ingestion).
    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Accept common alternative spellings of the key names; the canonical name wins.
ENV_ALIASES = {"FINNHUB_API_TOKEN": "FINNHUB_API_KEY", "ALPHA_VANTAGE_TOKEN": "ALPHA_VANTAGE_API_KEY"}
for _alias, _canonical in ENV_ALIASES.items():
    if os.getenv(_alias) and not os.getenv(_canonical):
        os.environ[_canonical] = os.environ[_alias]

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"
OUTPUTS_DIR = ROOT_DIR / "outputs"
CACHE_DIR = ROOT_DIR / ".cache"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_curl_ca_bundle() -> None:
    """yfinance uses curl_cffi, which does its own TLS handling independent of
    Python's ssl module — truststore.inject_into_ssl() does not reach it. On
    Windows, export the OS 'CA'+'ROOT' certificate stores to a PEM bundle and
    point CURL_CA_BUNDLE at it, so curl_cffi also trusts whatever the OS trusts
    (e.g. a TLS-intercepting antivirus web shield's root CA). No-op if
    CURL_CA_BUNDLE is already set, or on non-Windows platforms.
    """
    if os.getenv("CURL_CA_BUNDLE") or platform.system() != "Windows":
        return
    bundle_path = CACHE_DIR / "windows_ca_bundle.pem"
    try:
        import base64
        with open(bundle_path, "w") as f:
            for store in ("CA", "ROOT"):
                for cert, encoding, _trust in ssl.enum_certificates(store):
                    if encoding != "x509_asn":
                        continue
                    b64 = base64.b64encode(cert).decode("ascii")
                    lines = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
                    f.write(f"-----BEGIN CERTIFICATE-----\n{lines}\n-----END CERTIFICATE-----\n")
        os.environ["CURL_CA_BUNDLE"] = str(bundle_path)
    except Exception:  # noqa: BLE001 - best-effort; fall back to default cert handling
        pass


_ensure_curl_ca_bundle()
