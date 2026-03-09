"""Settings service — get/update single-row user settings."""

from sqlalchemy.orm import Session

from app.models.settings import UserSettings
from app.schemas.settings import SettingsUpdate


class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> UserSettings:
        """Get the single-row user settings, creating defaults if needed."""
        settings = self.db.query(UserSettings).filter(UserSettings.id == 1).first()
        if not settings:
            settings = UserSettings(id=1)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update_settings(self, data: SettingsUpdate) -> UserSettings:
        """Update user settings (partial update)."""
        settings = self.get_settings()

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings
