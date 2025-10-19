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
