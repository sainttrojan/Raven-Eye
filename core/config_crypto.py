"""Transparent encryption for config.json.

The plaintext file is NEVER committed (gitignored). When a master key
is available, it is stored as config.json.enc (Fernet) and the plaintext
is removed. Without the key the app still works from env vars / Streamlit
secrets, but the file on disk stays unreadable.

Key resolution (first hit wins):
  1. Streamlit secrets RAVEN_CONFIG_KEY
  2. Env var RAVEN_CONFIG_KEY
  3. File ~/.config/raven-eye.key  (or $RAVEN_KEY_FILE)
  4. File ./raven.key  (project root, gitignored)

Generate a key once:
    venv/bin/python -m core.config_crypto --generate
Then set it as RAVEN_CONFIG_KEY (and/or save to ~/.config/raven-eye.key)
and run:
    venv/bin/python -m core.config_crypto --encrypt
"""

import base64
import json
import os
from pathlib import Path

CONFIG_JSON = Path("config.json")
CONFIG_ENC = Path("config.json.enc")
DEFAULT_KEY_FILE = Path.home() / ".config" / "raven-eye.key"


def _load_key() -> bytes | None:
    # 1. Streamlit secrets
    try:
        import streamlit as st
        k = (st.secrets.get("RAVEN_CONFIG_KEY", "") or "").strip()
        if k:
            return k.encode()
    except Exception:
        pass
    # 2. Env var
    k = (os.getenv("RAVEN_CONFIG_KEY", "") or "").strip()
    if k:
        return k.encode()
    # 3. File from env or default locations
    for p in [os.getenv("RAVEN_KEY_FILE", ""), str(DEFAULT_KEY_FILE), "./raven.key"]:
        if not p:
            continue
        fp = Path(p).expanduser()
        if fp.exists():
            try:
                return fp.read_text().strip().encode()
            except Exception:
                pass
    return None


def _fernet():
    key = _load_key()
    if not key:
        return None
    from cryptography.fernet import Fernet, InvalidToken
    # Accept both raw Fernet keys and passwords (derive if not valid Fernet)
    try:
        # Validate key is 32 url-safe base64
        Fernet(key)
        return Fernet(key), InvalidToken
    except Exception:
        # Derive from password via PBKDF2HMAC (deterministic per install)
        import hashlib, base64
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        salt = b"raven-eye-config-v1"
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
        dkey = base64.urlsafe_b64encode(kdf.derive(key))
        return Fernet(dkey), InvalidToken


def is_encrypted() -> bool:
    return CONFIG_ENC.exists()


def encrypt_file() -> bool:
    """Encrypt config.json -> config.json.enc and remove plaintext. Returns True if encrypted."""
    if not CONFIG_JSON.exists():
        print("No config.json to encrypt.")
        return False
    f, _ = _fernet() or (None, None)
    if not f:
        print("No master key found. Set RAVEN_CONFIG_KEY first (see core/config_crypto.py header).")
        return False
    data = CONFIG_JSON.read_bytes()
    CONFIG_ENC.write_bytes(f.encrypt(data))
    CONFIG_JSON.unlink()
    print(f"Encrypted -> {CONFIG_ENC} (plaintext removed). Keep your key safe!")
    return True


def decrypt_file() -> dict | None:
    """Decrypt config.json.enc -> dict, or None if not encrypted / no key."""
    if not CONFIG_ENC.exists():
        return None
    f, InvalidToken = _fernet() or (None, None)
    if not f:
        return None
    try:
        raw = f.decrypt(CONFIG_ENC.read_bytes())
        return json.loads(raw.decode())
    except InvalidToken:
        print("Invalid master key — cannot decrypt config.json.enc")
        return None
    except Exception as e:
        print(f"Decrypt failed: {e}")
        return None


def load_config_dict() -> dict:
    """Load config from encrypted file (if key available) or plaintext, else {}."""
    d = decrypt_file()
    if d is not None:
        return d
    if CONFIG_JSON.exists():
        try:
            return json.loads(CONFIG_JSON.read_text())
        except Exception:
            return {}
    return {}


def save_config_dict(data: dict):
    """Save config: encrypted if key available, else plaintext."""
    f, _ = _fernet() or (None, None)
    if f:
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode()
        CONFIG_ENC.write_bytes(f.encrypt(raw))
        if CONFIG_JSON.exists():
            CONFIG_JSON.unlink()
    else:
        CONFIG_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        if CONFIG_ENC.exists():
            pass  # keep enc if it exists, plaintext is fallback


if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser(description="Raven-Eye config encryption")
    ap.add_argument("--generate", action="store_true", help="Print a new Fernet key")
    ap.add_argument("--encrypt", action="store_true", help="Encrypt config.json -> config.json.enc")
    ap.add_argument("--decrypt", action="store_true", help="Decrypt and print config (for verification)")
    ap.add_argument("--status", action="store_true", help="Show encryption status")
    args = ap.parse_args()
    if args.generate:
        from cryptography.fernet import Fernet
        print(Fernet.generate_key().decode())
        sys.exit(0)
    if args.status:
        print(f"config.json: {'exists' if CONFIG_JSON.exists() else 'missing'}")
        print(f"config.json.enc: {'exists' if CONFIG_ENC.exists() else 'missing'}")
        print(f"key available: {bool(_load_key())}")
        if CONFIG_ENC.exists() and _load_key():
            print(f"decryptable: {decrypt_file() is not None}")
        sys.exit(0)
    if args.encrypt:
        sys.exit(0 if encrypt_file() else 1)
    if args.decrypt:
        d = decrypt_file()
        if d is None:
            print("Nothing to decrypt or no key.")
            sys.exit(1)
        print(json.dumps(d, ensure_ascii=False, indent=2))
        sys.exit(0)
    ap.print_help()
