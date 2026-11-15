"""Read baby profiles without changing the live Ayla session or manual settings."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from urllib.parse import quote

import aiohttp
from pyowletapi.const import REGION_INFO

logger = logging.getLogger(__name__)
BABY_FIELDS = ("baby_name", "birth_date", "baby_pronouns")


def normalize_profiles(payload: object, account_id: str) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        raise ValueError("Invalid profile response")
    result = []
    prefix = f"accounts/{account_id}/profiles/"
    for item in payload["profiles"]:
        if not isinstance(item, dict):
            continue
        identifier = item.get("name")
        if not isinstance(identifier, str) or not identifier.startswith(prefix):
            continue
        suffix = identifier[len(prefix) :]
        if not suffix or "/" in suffix or "?" in suffix or "#" in suffix:
            continue
        profile = {"id": identifier}
        name = item.get("givenName")
        if isinstance(name, str) and name.strip():
            profile["baby_name"] = name.strip()[:40]
        birthday = item.get("birthdate")
        if isinstance(birthday, str):
            try:
                birthday = date.fromisoformat(birthday)
                today = datetime.now(UTC).date()
                if today - timedelta(days=366 * 6) <= birthday <= today:
                    profile["birth_date"] = birthday.isoformat()
            except ValueError:
                pass
        gender = item.get("gender")
        if isinstance(gender, str):
            pronoun = {"female": "she", "f": "she", "male": "he", "m": "he"}.get(gender.lower())
            if pronoun:
                profile["baby_pronouns"] = pronoun
        result.append(profile)
    return result


async def fetch_profiles(region: str, refresh_token: str) -> list[dict]:
    if region not in REGION_INFO or not refresh_token:
        raise ValueError("Missing profile authentication")
    headers = {
        "X-Android-Package": "com.owletcare.owletcare",
        "X-Android-Cert": "2A3BC26DB0B8B0792DBE28E6FFDC2598F9B12B74",
    }
    async with aiohttp.ClientSession(
        trust_env=True, timeout=aiohttp.ClientTimeout(total=15)
    ) as session:
        async with session.post(
            "https://securetoken.googleapis.com/v1/token",
            params={"key": REGION_INFO[region]["apiKey"]},
            headers=headers,
            data={"grantType": "refresh_token", "refreshToken": refresh_token},
        ) as response:
            response.raise_for_status()
            auth = await response.json()
        account_id = str(auth["user_id"])
        suffix = ".eu" if region == "europe" else ""
        url = f"https://accounts{suffix}.owletdata.com/v2/accounts/{quote(account_id, safe='')}/profiles"
        async with session.get(
            url, headers={"Authorization": f"Bearer {auth['id_token']}"}
        ) as response:
            response.raise_for_status()
            return normalize_profiles(await response.json(), account_id)


def selected_profile(prefs: dict) -> dict | None:
    profiles = prefs.get("owlet_profiles") or []
    identifier = prefs.get("owlet_profile_id")
    return next((p for p in profiles if p.get("id") == identifier), None)


def effective_preferences(prefs: dict) -> dict:
    result = dict(prefs)
    imported = selected_profile(prefs) or {}
    for key in BABY_FIELDS:
        if key not in prefs and key in imported:
            result[key] = imported[key]
    return result


async def save_profiles(store, account_id: int, profiles: list[dict]) -> dict:
    account = await store.get_account(account_id)
    prefs = account.get("dashboard_preferences") or {}
    selected = prefs.get("owlet_profile_id")
    if selected not in {p["id"] for p in profiles}:
        selected = profiles[0]["id"] if len(profiles) == 1 else None
    return await store.update_account_preferences(
        account_id,
        dashboard_preferences={
            "owlet_profiles": profiles,
            "owlet_profile_id": selected,
        },
    )


async def sync_profiles(store, account_id: int, client) -> None:
    try:
        profiles = await asyncio.wait_for(client.profiles(), timeout=20)
        await save_profiles(store, account_id, profiles)
    except Exception as exc:
        # Optional metadata must never prevent live collection. No upstream text.
        logger.warning("Baby profile sync unavailable: %s", type(exc).__name__)
