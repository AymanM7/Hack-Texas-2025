"""FastAPI server to provide backend API for the Next.js frontend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import sys
from pathlib import Path
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.data_loader import (
    fetch_data,
    fetch_laps,
    fetch_drivers,
    fetch_pit_stop,
    fetch_stints
)
from app.data_processor import build_driver_color_map
from app.lap_analyzer import analyze_single_lap, analyze_driver_laps
from app.race_predictor import (
    fetch_historical_austin_races,
    build_perfect_lap_profile,
    generate_simulated_race,
    predict_podium,
    calculate_race_positions
)

app = FastAPI(title="F1 Strategy Dashboard API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telemetry cache to avoid re-fetching FastF1 data
_telemetry_cache = {}


def _get_cached_telemetry(session_key: str):
    """Get telemetry from cache or return None."""
    return _telemetry_cache.get(session_key)


def _set_cached_telemetry(session_key: str, telemetry_data: dict):
    """Store telemetry in cache."""
    _telemetry_cache[session_key] = telemetry_data
    return telemetry_data


@app.on_event("startup")
async def warm_cache():
    """Pre-warm cache with recent/popular sessions on startup."""
    import threading
    import time

    # Sessions to warm (most recent races and popular circuits)
    sessions_to_warm = [
        "9662",  # Abu Dhabi Race
        "9636",  # Las Vegas Race
        "9635",  # Singapore Race
    ]

    def _warm_sessions():
        """Warm cache in background thread."""
        for session_key in sessions_to_warm:
            try:
                # Make request to populate cache
                get_animation_telemetry(session_key)
                print(f"✓ Warmed cache for session {session_key}")
                time.sleep(1)  # Small delay between requests
            except Exception as e:
                print(f"⚠ Failed to warm cache for session {session_key}: {e}")

    # Run cache warming in background thread to not block startup
    cache_thread = threading.Thread(target=_warm_sessions, daemon=True)
    cache_thread.start()


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/sessions/{year}/{country}")
def get_sessions(year: int, country: str):
    """Get available sessions for a given year and country."""
    try:
        meetings = fetch_data("meetings", {"year": year, "country_name": country})
        if meetings.empty:
            return {"error": "No meetings found"}

        available_sessions = []
        for _, meeting in meetings.iterrows():
            meeting_key = meeting["meeting_key"]
            sessions = fetch_data("sessions", {"meeting_key": meeting_key})
            for _, session in sessions.iterrows():
                available_sessions.append({
                    "session_key": session["session_key"],
                    "session_name": session["session_name"],
                    "meeting_name": meeting.get("meeting_name", ""),
                    "location": meeting.get("location", ""),
                })

        return {"sessions": available_sessions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/lap-analysis/{session_key}/{driver_number}")
def get_lap_analysis(session_key: str, driver_number: str):
    """Get lap analysis for a driver."""
    try:
        laps = fetch_laps(session_key)
        drivers = fetch_drivers(session_key)

        # Get driver name
        driver_row = drivers[drivers["driver_number"].astype(str) == driver_number]
        if driver_row.empty:
            return {"error": "Driver not found"}

        driver_name = driver_row.iloc[0].get("name_acronym", f"DRV{driver_number}")

        # Filter laps for this driver
        driver_laps = laps[laps["driver_number"].astype(str) == driver_number]

        if driver_laps.empty:
            return {"error": "No laps found for this driver"}

        # Analyze
        analysis = analyze_driver_laps(
            driver_number=driver_number,
            driver_name=driver_name,
            lap_df=driver_laps
        )

        return analysis
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/race-prediction/{year}")
def get_race_prediction(year: int):
    """Get race prediction for Austin F1."""
    try:
        # Fetch historical data
        historical_races = fetch_historical_austin_races([2022, 2023, 2024, 2025])

        if not historical_races:
            return {"error": "No historical race data available"}

        # Build profile
        perfect_profile = build_perfect_lap_profile(historical_races)

        # Build driver name map
        driver_name_map = {}
        for yr in [2025, 2024, 2023]:
            if yr in historical_races:
                try:
                    drivers_df = fetch_drivers(historical_races[yr]["session_key"])
                    for _, driver_row in drivers_df.iterrows():
                        driver_num = str(int(driver_row["driver_number"]))
                        if driver_num not in driver_name_map:
                            driver_name_map[driver_num] = {
                                "name": driver_row.get("name_acronym", f"DRV{driver_num}"),
                                "team": driver_row.get("team_name", "Unknown"),
                            }
                except:
                    pass

        # Generate simulation
        simulated_df = generate_simulated_race(
            perfect_profile,
            driver_name_map=driver_name_map,
            num_laps=56
        )
        positions_df = calculate_race_positions(simulated_df)

        # Get podium
        podium_df = predict_podium(simulated_df, driver_name_map)

        return {
            "simulated_laps": len(simulated_df),
            "drivers": simulated_df["driver_number"].nunique(),
            "podium": podium_df.to_dict(orient="records"),
            "positions": positions_df.to_dict(orient="records")[:56]  # First 56 positions
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/animation-telemetry/{session_key}")
def get_animation_telemetry(session_key: str):
    """
    Fetch telemetry data for F1 Race Animator using FastF1
    Returns driver positions, speeds, and telemetry data formatted for animation
    Uses caching to avoid re-fetching data for the same session
    """
    # Check cache first
    cached_data = _get_cached_telemetry(session_key)
    if cached_data is not None:
        return cached_data

    try:
        import fastf1
        import pandas as pd

        # Map OpenF1 session keys to (GP_name, year, session_type)
        # Sessions include Race (R), Qualifying (Q), and Practice (FP1, FP2, FP3)
        SESSION_KEY_MAPPING = {
            # Bahrain
            "9609": ("Bahrain", 2024, "FP1"),
            "9610": ("Bahrain", 2024, "FP2"),
            "9611": ("Bahrain", 2024, "Q"),
            "9612": ("Bahrain", 2024, "R"),
            # Saudi Arabia
            "9613": ("Saudi Arabia", 2024, "R"),
            # Australia
            "9614": ("Australia", 2024, "R"),
            # Japan
            "9615": ("Japan", 2024, "R"),
            # China
            "9616": ("China", 2024, "R"),
            # United States (Austin)
            "9618": ("United States", 2024, "R"),
            "9644": ("United States", 2024, "R"),
            # Mexico
            "9619": ("Mexico", 2024, "R"),
            # Brazil
            "9620": ("Brazil", 2024, "R"),
            # Abu Dhabi
            "9461": ("Abu Dhabi", 2024, "FP1"),
            "9656": ("Abu Dhabi", 2024, "FP2"),
            "9658": ("Abu Dhabi", 2024, "Q"),
            "9662": ("Abu Dhabi", 2024, "R"),
            "9621": ("Abu Dhabi", 2024, "R"),
            # Miami
            "9625": ("Miami", 2024, "R"),
            # Monaco
            "9626": ("Monaco", 2024, "R"),
            # Canada
            "9627": ("Canada", 2024, "R"),
            # Spain
            "9628": ("Spain", 2024, "R"),
            # Austria
            "9629": ("Austria", 2024, "R"),
            # United Kingdom
            "9630": ("United Kingdom", 2024, "R"),
            # Hungary
            "9631": ("Hungary", 2024, "R"),
            # Belgium
            "9632": ("Belgium", 2024, "R"),
            # Netherlands
            "9633": ("Netherlands", 2024, "R"),
            # Italy
            "9634": ("Italy", 2024, "R"),
            # Singapore
            "9635": ("Singapore", 2024, "R"),
            # Las Vegas
            "9636": ("Las Vegas", 2024, "R"),
            # Qatar
            "9645": ("Qatar", 2024, "FP1"),
            "9646": ("Qatar", 2024, "Q"),
            "9655": ("Qatar", 2024, "R"),
            "9637": ("Qatar", 2024, "R"),
        }

        # Get GP name, year, and session type from session key
        if session_key not in SESSION_KEY_MAPPING:
            return {"drivers": {}, "session_key": session_key, "data_points": 0}

        gp_name, year, session_type = SESSION_KEY_MAPPING[session_key]

        # Get session from FastF1
        try:
            session = fastf1.get_session(year, gp_name, session_type)
        except:
            # Fallback to Race if session type not found
            session = fastf1.get_session(year, gp_name, 'R')
        if session is None:
            return {"drivers": {}, "session_key": session_key, "data_points": 0}

        # Load telemetry data (car_data includes X, Y, Speed, etc.)
        session.load(telemetry=True, weather=False)

        # Get driver info
        drivers_info = session.drivers
        if not drivers_info:
            return {"drivers": {}, "session_key": session_key, "data_points": 0}

        # Calculate transformation using track bounds as reference
        # Collect all coordinates to find bounds
        all_x_coords = []
        all_y_coords = []

        for driver_number in drivers_info:
            try:
                pos_data = session.pos_data.get(driver_number)
                if pos_data is not None and not pos_data.empty:
                    for _, point in pos_data.iterrows():
                        x = float(point['X']) if pd.notna(point.get('X')) else None
                        y = float(point['Y']) if pd.notna(point.get('Y')) else None
                        if x is not None and y is not None and not isnan(x) and not isnan(y):
                            all_x_coords.append(x)
                            all_y_coords.append(y)
            except:
                pass

        # Calculate bounds
        if all_x_coords and all_y_coords:
            driver_min_x = min(all_x_coords)
            driver_max_x = max(all_x_coords)
            driver_min_y = min(all_y_coords)
            driver_max_y = max(all_y_coords)
            driver_range_x = driver_max_x - driver_min_x if driver_max_x > driver_min_x else 1
            driver_range_y = driver_max_y - driver_min_y if driver_max_y > driver_min_y else 1
        else:
            driver_min_x = driver_min_y = 0
            driver_max_x = driver_max_y = 1000
            driver_range_x = driver_range_y = 1000

        # Reference visualization bounds (matches f1-tracks.js expected scale)
        viz_min_x, viz_max_x = 0, 1000
        viz_min_y, viz_max_y = 0, 1000
        viz_range_x = viz_max_x - viz_min_x
        viz_range_y = viz_max_y - viz_min_y

        # Build driver color map and drivers data
        drivers_data = {}

        for driver_number in drivers_info:
            try:
                driver_num_str = str(driver_number)

                # Get driver details
                driver_obj = session.get_driver(driver_number)
                driver_code = driver_obj['Abbreviation'] if 'Abbreviation' in driver_obj else f"DRV{driver_number}"
                driver_name = driver_obj.get('Surname', f"DRV{driver_number}")
                team = driver_obj.get('TeamName', "Unknown")

                # Get driver's position data (real track coordinates)
                pos_data = session.pos_data.get(driver_number)
                car_data = session.car_data.get(driver_number)

                if pos_data is None or pos_data.empty:
                    continue

                # Extract telemetry points - use pos_data for real track positions
                telemetry = []
                # Subsample every Nth point to keep data size reasonable
                subsample_rate = max(1, len(pos_data) // 2000)  # Target ~2000 points per driver

                for idx, (_, point) in enumerate(pos_data.iterrows()):
                    if idx % subsample_rate != 0:
                        continue
                    try:
                        # Extract real position data and transform to visualization space
                        x_raw = float(point['X']) if pd.notna(point.get('X')) else 0.0
                        y_raw = float(point['Y']) if pd.notna(point.get('Y')) else 0.0

                        # Affine transformation: map driver coordinates to visualization bounds
                        # Formula: viz_coord = viz_min + (raw_coord - raw_min) / raw_range * viz_range
                        x = viz_min_x + (x_raw - driver_min_x) / driver_range_x * viz_range_x
                        y = viz_min_y + (y_raw - driver_min_y) / driver_range_y * viz_range_y

                        # Clamp to visualization bounds
                        x = max(viz_min_x, min(viz_max_x, x))
                        y = max(viz_min_y, min(viz_max_y, y))

                        time_val = float(idx) / subsample_rate

                        telemetry_point = {
                            "time": time_val,
                            "x": x,
                            "y": y,
                            "speed": 0,
                            "gear": 3,
                            "throttle": 0.5,
                            "brake": 0.0,
                            "drs": False,
                            "lapNumber": 1
                        }
                        telemetry.append(telemetry_point)
                    except:
                        continue

                if telemetry:
                    # Generate color based on driver number
                    color = f"hsl({(int(driver_number) * 47) % 360}, 70%, 50%)"

                    drivers_data[driver_num_str] = {
                        "name": driver_name,
                        "code": driver_code,
                        "number": int(driver_number),
                        "team": team,
                        "color": color,
                        "telemetry": telemetry
                    }
            except:
                continue

        # Cache and return the result
        response = {
            "drivers": drivers_data,
            "session_key": session_key,
            "data_points": sum(len(d["telemetry"]) for d in drivers_data.values())
        }
        _set_cached_telemetry(session_key, response)
        return response

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Server error: {str(e)}"})


@app.get("/api/animation-sessions")
def get_animation_sessions():
    """
    Get list of available sessions for animation
    Returns recent races sorted by date
    """
    try:
        # Fetch recent meetings
        meetings = fetch_data("meetings", {"year": 2024})

        sessions_list = []
        for _, meeting in meetings.iterrows():
            try:
                meeting_key = meeting.get("meeting_key")
                sessions = fetch_data("sessions", {"meeting_key": meeting_key})

                for _, session in sessions.iterrows():
                    if session.get("session_name") in ["Practice 1", "Practice 2", "Qualifying", "Race"]:
                        sessions_list.append({
                            "session_key": session.get("session_key"),
                            "session_name": session.get("session_name"),
                            "meeting_name": meeting.get("meeting_name", ""),
                            "country": meeting.get("country_name", ""),
                            "date": session.get("date_start", "")
                        })
            except:
                pass

        return {"sessions": sorted(sessions_list, key=lambda x: x.get("date", ""), reverse=True)[:20]}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/text-to-speech")
def text_to_speech(text: str = None):
    """Convert text to speech using ElevenLabs API."""
    try:
        if not text:
            return JSONResponse(status_code=400, content={"error": "Text is required"})

        ELEVENLABS_API_KEY = "378360509e31179f09b7aff18b43842842bb5246814f05cf87fc56a12f939dfa"
        VOICE_ID = "FmTodAVOYAC5llerS0KD"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            return JSONResponse(status_code=500, content={"error": f"ElevenLabs API error: {response.text}"})

        return StreamingResponse(
            iter([response.content]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=commentary.mp3"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
