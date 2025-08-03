from flask import Flask, Response
import requests
import os
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from prometheus_client.core import GaugeMetricFamily
from dotenv import load_dotenv

load_dotenv()

JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://localhost:8096")
API_KEY = os.getenv("JELLYFIN_API_KEY")

app = Flask(__name__)

# Internal counter to simulate total cumulative sessions
session_cumulative_total = 0

@app.route("/metrics")
def metrics():
    global session_cumulative_total
    registry = CollectorRegistry()
    session_metric = GaugeMetricFamily(
        "jellyfin_playback_progress_percent",
        "Playback progress as a percentage for active Jellyfin sessions",
        labels=["username", "is_paused", "play_method", "now_playing", "series", "media_type"]
    )
    count_metric = GaugeMetricFamily(
        "jellyfin_active_sessions_total",
        "Total number of active Jellyfin playback sessions"
    )
    session_total_metric = GaugeMetricFamily(
        "jellyfin_active_sessions_count_total",
        "Total cumulative number of Jellyfin sessions detected"
    )

    active_count = 0

    try:
        response = requests.get(
            f"{JELLYFIN_URL}/Sessions",
            headers={"X-Emby-Token": API_KEY},
            timeout=5
        )
        response.raise_for_status()
        sessions = response.json()

        for session in sessions:
            if not session.get("IsActive"):
                continue

            now_playing = session.get("NowPlayingItem")
            if not now_playing or not now_playing.get("MediaStreams"):
                continue

            playstate = session.get("PlayState", {})
            position = playstate.get("PositionTicks")
            duration = now_playing.get("RunTimeTicks")
            if not position or not duration:
                continue

            progress = (position / duration) * 100

            session_metric.add_metric(
                labels=[
                    session.get("UserName", "unknown"),
                    str(playstate.get("IsPaused", False)).lower(),
                    playstate.get("PlayMethod", "unknown"),
                    now_playing.get("Name", "unknown"),
                    now_playing.get("SeriesName", ""),
                    now_playing.get("Type", "unknown")
                ],
                value=progress
            )

            active_count += 1

        count_metric.add_metric([], active_count)
        session_cumulative_total += active_count
        session_total_metric.add_metric([], session_cumulative_total)

    except Exception as e:
        print("Error retrieving Jellyfin sessions:", e)

    class SessionCollector:
        def collect(self):
            yield session_metric
            yield count_metric
            yield session_total_metric

    registry.register(SessionCollector())
    return Response(generate_latest(registry), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9789)
