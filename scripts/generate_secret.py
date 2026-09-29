#!/usr/bin/env python3
"""
CloudBox Secrets Generator
Generates high-entropy cryptographic keys and secrets for production .env configuration.
"""

import secrets
import string

def generate_url_token(length=32):
    return secrets.token_urlsafe(length)

def generate_hex_token(length=32):
    return secrets.token_hex(length)

def generate_alphanumeric_password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def print_production_secrets():
    print("==========================================================")
    print("  CLOUDBOX PRODUCTION SECRETS GENERATOR")
    print("==========================================================")
    print(f"SECRET_KEY={generate_hex_token(32)}")
    print(f"JWT_SECRET_KEY={generate_hex_token(32)}")
    print(f"POSTGRES_PASSWORD={generate_alphanumeric_password(24)}")
    print(f"MINIO_ROOT_USER=cloudbox_admin_{secrets.token_hex(4)}")
    print(f"MINIO_ROOT_PASSWORD={generate_alphanumeric_password(24)}")
    print("==========================================================")
    print("Copy these values into your production .env file.")
    print("NEVER commit real production secrets to version control.")

if __name__ == "__main__":
    print_production_secrets()
