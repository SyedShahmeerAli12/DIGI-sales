"""Generates a bcrypt hash for APP_PASSWORD_HASH in .env.

Usage: python -m app.scripts.hash_password "your-demo-password"
"""

import sys

from app.core.security import hash_password


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.hash_password <password>")
        raise SystemExit(1)
    print(hash_password(sys.argv[1]))


if __name__ == "__main__":
    main()
