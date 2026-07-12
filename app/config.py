from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    owlet_email: str | None = Field(default=None, alias="OWLET_EMAIL")
    owlet_password: str | None = Field(default=None, alias="OWLET_PASSWORD")
    owlet_region: str = Field(default="world", alias="OWLET_REGION")
    poll_interval_seconds: int = Field(default=30, alias="POLL_INTERVAL_SECONDS")
    database_path: Path = Field(default=Path("data/owlet.sqlite3"), alias="DATABASE_PATH")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8788, alias="PORT")
    owlet_basic_auth_username: str | None = Field(default=None, alias="OWLET_BASIC_AUTH_USERNAME")
    owlet_basic_auth_password: str | None = Field(default=None, alias="OWLET_BASIC_AUTH_PASSWORD")
    owlet_share_token: str | None = Field(default=None, alias="OWLET_SHARE_TOKEN")
    # Seeds an 'admin'/'password' login at startup. Convenience for local/desktop
    # use only - NEVER enable on a publicly reachable deployment.
    seed_default_admin: bool = Field(default=False, alias="SEED_DEFAULT_ADMIN")
    # Set by the desktop shell: surfaces the collects-only-while-running warning.
    desktop_mode: bool = Field(default=False, alias="OWLET_DESKTOP")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def has_owlet_credentials(self) -> bool:
        return bool(self.owlet_email and self.owlet_password)

    @property
    def basic_auth_enabled(self) -> bool:
        return bool(self.owlet_basic_auth_username and self.owlet_basic_auth_password)

    @property
    def share_enabled(self) -> bool:
        return bool(self.owlet_share_token)
