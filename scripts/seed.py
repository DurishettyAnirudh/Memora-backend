"""Seed script — creates default domains and settings row."""

import sys
from pathlib import Path

# Allow running as `python -m scripts.seed` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.services.domain_service import DomainService
from app.services.settings_service import SettingsService


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Seed default domains
        domain_svc = DomainService(db)
        domain_svc.seed_defaults()
        print("✓ Default domains seeded")

        # Ensure default settings row exists
        settings_svc = SettingsService(db)
        settings_svc.get_settings()
        print("✓ Default settings row created")

        db.commit()
        print("Seed complete.")
    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
