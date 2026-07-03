from app.analytics import build_insights, build_rollups, sleep_state_label
from app.models import normalize_reading


def _reading(timestamp: str, *, hr=120, spo2=96, movement=0, sleep_state=1):
    return normalize_reading(
        {
            "heart_rate": hr,
            "oxygen_saturation": spo2,
            "movement": movement,
            "sleep_state": sleep_state,
            "last_updated": timestamp,
            "battery": 100,
        },
        device_serial="AC123",
    )


def test_sleep_state_labels_match_known_owlet_codes():
    assert sleep_state_label("0") == "inactive"
    assert sleep_state_label("1") == "awake"
    assert sleep_state_label("8") == "light sleep"
    assert sleep_state_label("15") == "deep sleep"
    assert sleep_state_label("99") == "state 99"


def test_build_rollups_computes_hourly_averages_and_duration_estimates():
    readings = [
        _reading("2026-07-03T10:00:00Z", hr=100, spo2=93, sleep_state=8),
        _reading("2026-07-03T10:30:00Z", hr=110, spo2=94, sleep_state=15),
        _reading("2026-07-03T11:00:00Z", hr=120, spo2=96, sleep_state=1),
        _reading("2026-07-03T11:30:00Z", hr=130, spo2=98, sleep_state=1),
    ]

    rollups = build_rollups(readings, bucket="hour")

    assert [row["bucket_label"] for row in rollups] == ["Jul 3, 10 AM", "Jul 3, 11 AM"]
    assert rollups[0]["avg_heart_rate"] == 105
    assert rollups[0]["avg_oxygen_saturation"] == 93.5
    assert rollups[0]["min_oxygen_saturation"] == 93
    assert rollups[0]["sleep_seconds"] == 3600
    assert rollups[0]["awake_seconds"] == 0
    assert rollups[1]["awake_seconds"] == 1800


def test_build_rollups_supports_requested_average_windows():
    readings = [
        _reading("2026-07-03T10:04:00Z", hr=100, spo2=93),
        _reading("2026-07-03T10:06:00Z", hr=110, spo2=94),
        _reading("2026-07-03T16:10:00Z", hr=120, spo2=96),
        _reading("2026-07-03T23:55:00Z", hr=130, spo2=98),
    ]

    five_minute = build_rollups(readings, bucket="5m")
    six_hour = build_rollups(readings, bucket="6h")
    twelve_hour = build_rollups(readings, bucket="12h")

    assert [row["bucket_label"] for row in five_minute[:2]] == [
        "Jul 3, 10:00 AM",
        "Jul 3, 10:05 AM",
    ]
    assert [row["bucket_label"] for row in six_hour] == [
        "Jul 3, 6 AM",
        "Jul 3, 12 PM",
        "Jul 3, 6 PM",
    ]
    assert [row["bucket_label"] for row in twelve_hour] == ["Jul 3, 12 AM", "Jul 3, 12 PM"]


def test_build_insights_answers_breathing_trend_and_sleep_totals():
    readings = [
        _reading("2026-07-03T10:00:00Z", spo2=92, sleep_state=8),
        _reading("2026-07-03T10:30:00Z", spo2=93, sleep_state=15),
        _reading("2026-07-03T11:00:00Z", spo2=96, sleep_state=1),
        _reading("2026-07-03T11:30:00Z", spo2=97, sleep_state=1),
    ]

    insights = build_insights(readings)

    assert insights["latest"]["oxygen_saturation"] == 97
    assert insights["breathing"]["direction"] == "improving"
    assert insights["breathing"]["previous_avg_oxygen"] == 92.5
    assert insights["breathing"]["recent_avg_oxygen"] == 96.5
    assert insights["breathing"]["low_oxygen_samples"] == 0
    assert insights["sleep"]["sleep_seconds"] == 3600
    assert insights["sleep"]["awake_seconds"] == 1800
    assert insights["sleep"]["sleep_state_label"] == "awake"
