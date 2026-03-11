#!/usr/bin/env python3
"""
Generate secure secrets for Aegis Trader .env file
Run: python generate_secrets.py
"""

import secrets

print("=" * 60)
print("AEGIS TRADER - SECURE SECRET GENERATOR")
print("=" * 60)
print()
print("Copy these values to your .env file:")
print()
print("# Dashboard JWT Secret (min 32 chars)")
print(f"DASHBOARD_JWT_SECRET={secrets.token_urlsafe(48)}")
print()
print("# MT5 Node Secret (min 16 chars)")
print(f"MT5_NODE_SECRET={secrets.token_urlsafe(24)}")
print()
print("=" * 60)
print("IMPORTANT: Never commit these secrets to version control!")
print("=" * 60)
