#!/usr/bin/env python3
"""
Pre-Flight Environment Variable Validation & Fail-Fast Script for SurakshaGrid.
Validates database URIs, secrets, external services, and satellite credentials prior to boot.
"""

from __future__ import annotations

import os
import sys
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("env_verifier")

# Attempt loading .env or .env.production if present
for env_file in [".env", ".env.production"]:
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k not in os.environ:
                        os.environ[k] = v

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
]

OPTIONAL_RECOMMENDED_VARS = [
    "OSRM_HOST",
    "CORS_ORIGINS",
    "REDIS_URL",
    "COPERNICUS_API_KEY",
]


def verify_environment() -> bool:
    logger.info("Running pre-flight environment variable validation...")
    missing_critical = []

    for var_name in REQUIRED_ENV_VARS:
        val = os.getenv(var_name)
        if not val:
            missing_critical.append(var_name)
        else:
            logger.info("✓ %s is set.", var_name)

    if missing_critical:
        logger.error("❌ CRITICAL: Missing required environment variables: %s", ", ".join(missing_critical))
        logger.error("System boot halted to prevent unauthenticated or degraded operation.")
        return False

    # Validate DATABASE_URL format
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        try:
            parsed = urlparse(db_url.replace("postgresql+asyncpg://", "http://"))
            if not parsed.hostname or not parsed.path:
                logger.error("❌ Malformed DATABASE_URL: %s", db_url)
                return False
            logger.info("✓ DATABASE_URL format validated (Host: %s, DB: %s).", parsed.hostname, parsed.path.lstrip('/'))
        except Exception as err:
            logger.error("❌ Failed to parse DATABASE_URL: %s", err)
            return False

    for var_name in OPTIONAL_RECOMMENDED_VARS:
        val = os.getenv(var_name)
        if not val:
            logger.warning("⚠️ Recommended variable %s is not set. Using default fallback.", var_name)
        else:
            logger.info("✓ %s configured.", var_name)

    logger.info("✅ Pre-flight environment validation PASSED successfully.")
    return True


if __name__ == "__main__":
    success = verify_environment()
    sys.exit(0 if success else 1)
