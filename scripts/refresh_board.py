#!/usr/bin/env python3
"""Fetch live Whip Around data and bake it into the static fleet board."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


API_BASE = "https://api.whip-around.com/api/public/v4"
TEAM_NAME = "Gardena Police Department"
DUE_SOON_MILES = 500
DUE_SOON_DAYS = 14
DUE_THIS_WEEK_DAYS = 7
BOARD_PATH = Path(__file__).resolve().parents[1] / "index.html"


def fetch_collection(path: str, api_key: str) -> list[dict]:
    request = Request(
        f"{API_BASE}{path}",
        headers={"x-api-key": api_key, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=45) as response:
            if response.status != 200:
                raise RuntimeError(f"Whip Around returned HTTP {response.status} for {path}")
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Whip Around returned HTTP {exc.code} for {path}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach Whip Around for {path}: {exc}") from exc

    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"Whip Around response for {path} did not contain a data array")
    return data


def parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def number(value: object, default: float = 0) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def normalize_number(value: object, default: float = 0) -> int | float:
    result = number(value, default)
    return int(result) if result.is_integer() else result


def build_fleet(assets: list[dict], services: list[dict], now: datetime) -> list[dict]:
    by_asset: dict[str, list[dict]] = {}
    for service in services:
        asset_name = service.get("asset_name")
        if isinstance(asset_name, str):
            by_asset.setdefault(asset_name, []).append(service)

    fleet = []
    for asset in assets:
        if (asset.get("team") or {}).get("name") != TEAM_NAME:
            continue

        overdue: list[str] = []
        due_soon: list[str] = []
        due_soon_details: list[dict] = []
        scheduled_this_week: list[dict] = []
        current_odometer = number(asset.get("odometer"))

        for service in by_asset.get(asset.get("name"), []):
            schedule = service.get("schedule") or {}
            due_date = parse_date(schedule.get("date"))
            days_until = int((due_date - now).total_seconds() / 86400 + 0.5) if due_date else None
            status = str(service.get("status") or "").strip().casefold().replace("_", " ").replace("-", " ")
            title = service.get("title") or "Unnamed service"
            scheduled_odometer = schedule.get("odometer")
            miles_remaining = (
                number(scheduled_odometer) - current_odometer
                if scheduled_odometer not in (None, "")
                else None
            )

            def add_due_soon() -> None:
                due_soon.append(title)
                due_soon_details.append(
                    {
                        "title": title,
                        "milesRemaining": (
                            normalize_number(miles_remaining)
                            if miles_remaining is not None and miles_remaining >= 0
                            else None
                        ),
                    }
                )

            if status in ("active", "due soon", "overdue") and days_until is not None and 0 <= days_until <= DUE_THIS_WEEK_DAYS:
                scheduled_this_week.append({"title": title, "dueDate": schedule.get("date")})

            if status == "overdue":
                overdue.append(title)
                continue
            if status == "due soon":
                add_due_soon()
                continue
            if status != "active":
                continue

            if (
                miles_remaining is not None
                and 0 <= miles_remaining <= DUE_SOON_MILES
            ) or (days_until is not None and 0 <= days_until <= DUE_SOON_DAYS):
                add_due_soon()

        last_service = asset.get("last_service") or {}
        fleet.append(
            {
                "unit": asset.get("name"),
                "vin": asset.get("vin"),
                "make": asset.get("make"),
                "model": asset.get("model"),
                "year": asset.get("year"),
                "odometer": normalize_number(asset.get("odometer")),
                "engineHours": normalize_number(asset.get("engine_hours")),
                "outOfService": bool(asset.get("is_out_of_service")),
                "lastServiceTitle": last_service.get("title"),
                "lastServiceDate": last_service.get("date"),
                "lastServiceOdometer": last_service.get("odometer"),
                "overdueCount": len(overdue),
                "dueSoonCount": len(due_soon),
                "overdueServices": overdue,
                "dueSoonServices": due_soon,
                "dueSoonDetails": due_soon_details,
                "scheduledThisWeek": scheduled_this_week,
            }
        )
    return fleet


def update_board(html: str, fleet: list[dict], now: datetime) -> str:
    compact_json = json.dumps(fleet, ensure_ascii=False, separators=(",", ":"))
    data_pattern = re.compile(
        r"(// BOARD_DATA_START[^\n]*\n)const FLEET = .*?;(\n// BOARD_DATA_END)",
        re.DOTALL,
    )
    updated, data_count = data_pattern.subn(
        lambda match: f"{match.group(1)}const FLEET = {compact_json};{match.group(2)}",
        html,
    )
    if data_count != 1:
        raise RuntimeError(f"Expected one fleet data block, found {data_count}")

    timestamp = now.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%b %d, %Y, %-I:%M %p")
    timestamp = re.sub(r"\b0(\d),", r"\1,", timestamp)
    updated, timestamp_count = re.subn(
        r'(<b id="lastRefreshed">).*?(</b>)',
        rf"\g<1>{timestamp}\g<2>",
        updated,
        count=1,
    )
    if timestamp_count != 1:
        raise RuntimeError(f"Expected one last-refreshed field, found {timestamp_count}")
    return updated


def main() -> int:
    api_key = os.environ.get("WHIPAROUND_API_KEY", "").strip()
    if not api_key:
        print("WHIPAROUND_API_KEY is not set", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    assets = fetch_collection("/assets?limit=1000&include[]=team&include[]=last_service", api_key)
    services = fetch_collection("/services?status=pending&limit=1000", api_key)
    fleet = build_fleet(assets, services, now)
    if not fleet:
        raise RuntimeError(f"No assets found for team {TEAM_NAME!r}; refusing to overwrite the board")

    original = BOARD_PATH.read_text(encoding="utf-8")
    updated = update_board(original, fleet, now)
    BOARD_PATH.write_text(updated, encoding="utf-8")
    overdue = sum(item["overdueCount"] for item in fleet)
    due_soon = sum(item["dueSoonCount"] for item in fleet)
    print(f"Updated {len(fleet)} assets: {overdue} overdue, {due_soon} due soon")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
