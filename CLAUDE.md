# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a comprehensive Formula 1 analytics platform combining real-time race data visualization, AI-powered lap analysis, and interactive race animation. The system consists of:
- **Streamlit Dashboard** (port 3000): Analysis and visualization frontend
- **FastAPI Server** (port 8000): Backend API for race animation and simulation
- **Data Sources**: OpenF1 API and FastF1 telemetry
- **AI Integration**: Google Gemini 2.5 Flash for lap analysis

## Project Architecture

The codebase follows a clean separation of concerns:

**main.py** - Streamlit app entry point that handles:
- Year and country selection UI
- Session filtering (FP1, Qualifying, Race)
- Orchestrating data fetching and processing pipeline
- Rendering three main visualizations through expanders

**app/data_loader.py** - OpenF1 API wrapper layer:
- Generic `fetch_data()` function that handles URL encoding and API calls
- Cached wrapper functions for specific endpoints: `fetch_meetings()`, `fetch_sessions()`, `fetch_laps()`, `fetch_stints()`, `fetch_pit_stop()`, `fetch_drivers()`
- All functions use `@st.cache_data` to minimize network calls
- Uses `requests.Request` to properly format query parameters for the OpenF1 API

**app/data_processor.py** - Data cleaning and transformation:
- `process_lap_data()` - Filters invalid laps, sorts by driver/lap number
- `process_stints()` - Prepares tire strategy data, calculates lap counts per stint
- `process_pit_stops()` - Filters pit stops with duration, sorts chronologically
- `build_driver_color_map()` - Maps driver acronyms to team colors for consistent visualization

**app/visualizer.py** - Interactive Plotly charts:
- `plot_lap_times()` - Line chart with markers showing lap duration over race distance, highlights pit out-laps
- `plot_tire_strategy()` - Horizontal stacked bar chart showing tire compound by lap range per driver
- `plot_pit_stop()` - Grouped bar chart comparing pit stop durations across drivers
- Utility formatters: `format_lap_time()` and `format_seconds_to_mmss()` for readable timestamps

**app/lap_analyzer.py** - AI-powered lap analysis with Gemini API:
- `analyze_driver_laps()` - Sends lap data to Google Gemini for AI analysis, returns per-lap insights and overall feedback
- `analyze_single_lap()` - Detailed analysis of a specific lap
- `create_timestamp_link()` - Generates clickable timestamps in format `session_key:lap_number` for simulation navigation
- Uses `@st.cache_data` to minimize expensive Gemini API calls
- Formats lap data into readable context for AI analysis

**app/race_predictor.py** - Race simulation and prediction:
- `fetch_historical_austin_races()` - Fetches historical lap data for Austin/COTA races
- `build_perfect_lap_profile()` - Analyzes historical data to determine ideal lap times
- `generate_simulated_race()` - Runs Monte Carlo race simulation with pit strategies
- `predict_podium()` - Predicts final race positions based on simulation
- `calculate_race_positions()` - Tracks position changes throughout race

**app/race_simulator.py** - Visual race animation components:
- `create_track_outline()` - Generates simplified 2D track layout for COTA
- `calculate_car_position_on_track()` - Maps lap progress to X/Y coordinates
- `create_race_visualization()` - Plotly-based race state visualization

**api_server.py** - FastAPI backend server:
- `GET /api/sessions/{year}/{country}` - Available sessions for a GP
- `GET /api/animation-sessions` - List of animator-compatible sessions
- `GET /api/animation-telemetry/{session_key}` - FastF1 telemetry with affine transformation
- `POST /api/race-simulator/{session_key}` - Race simulation endpoint
- `GET /api/health` - Health check endpoint
- Server-side caching with `_telemetry_cache` dictionary
- Automatic cache warming for popular sessions on startup

## Setup & Development

### Install dependencies
```bash
pip install -r requirements.txt
```

### Environment configuration
Create a `.env` file with:
```
BASE_API_URL=https://api.openf1.org/v1/
GEMINI_API_KEY=your_api_key_here
```

**IMPORTANT**: See `GEMINI_SETUP.md` for secure Gemini API key configuration. Never commit API keys to the repository.

### Run the application

**Terminal 1 - FastAPI Server (required for Race Animator):**
```bash
uvicorn api_server:app --reload --port 8000
```

**Terminal 2 - Streamlit Dashboard:**
```bash
streamlit run main.py --server.port 3000
```

The dashboard opens at `http://localhost:3000`. The API server runs at `http://localhost:8000`.

## Key Integration Points

### Data Sources
- **OpenF1 API**: `meetings`, `sessions`, `laps`, `stints`, `pit`, `drivers` endpoints
- **FastF1**: Telemetry data with precise X/Y coordinates for race animation
- **Google Gemini API**: AI-powered lap analysis and insights

### Data Flow
1. **Analysis Tab**: OpenF1 → data_loader → data_processor → visualizer → Streamlit UI
2. **Race Animator**: FastF1 → api_server (with affine transformation) → Frontend visualization
3. **AI Analysis**: Lap data → lap_analyzer → Gemini API → Cached results

### Caching Strategy
- **Streamlit (`@st.cache_data`)**: All data_loader functions, Gemini API calls
- **FastAPI (in-memory dict)**: Telemetry data with automatic warm-up for popular sessions
- **Cache Keys**: Based on function parameters (session_key, driver_number, etc.)

## Dashboard Features

### Analysis Tab
- **Lap Time Visualization**: Interactive line charts with pit stop indicators (🔧)
- **Tire Strategy**: Horizontal bars showing SOFT (red), MEDIUM (yellow), HARD (white), INTERMEDIATE (green), WET (blue)
- **Pit Stop Comparison**: Grouped bar charts with duration in seconds
- **AI Lap Analysis**: Driver-specific or lap-specific Gemini-powered insights

### Race Animator Tab
- **FastF1 Integration**: Real-time race replay using telemetry data from localhost:8000 API
- **Interactive Controls**: Play/Pause, speed control (0.5x-10x), reset, and timeline slider
- **Multi-Driver Visualization**: Select and track multiple drivers simultaneously
- **Track Rendering**: Full circuit outline with driver trails and real-time positions
- **Coordinate Transformation**: Affine mapping of FastF1 coordinates to visualization space
- **Live Telemetry Table**: Real-time Speed, Gear, Throttle, Brake, DRS data
- **2024 Season Support**: Practice, Qualifying, and Race sessions
- **Performance**: Cached telemetry with automatic warm-up for popular races (Abu Dhabi, Las Vegas, Singapore)

## Important Notes

### Performance Considerations
- **First Load**: FastF1 initial session load takes 30-60 seconds (downloading telemetry)
- **Cache Warming**: API server pre-loads Abu Dhabi, Las Vegas, Singapore on startup
- **Rate Limits**: Gemini free tier has quotas; results are cached per driver/session

### Data Formatting
- Y-axis uses dynamic MM:SS formatting for lap times
- Driver colors normalized with `#` prefix for consistency
- Timestamps format: `session_key:lap_number` for simulation links
- Session selection cascades from country → Grand Prix → Session Type

### API Dependencies
- OpenF1 API requires valid `BASE_API_URL` in `.env`
- Gemini API requires `GEMINI_API_KEY` (see `GEMINI_SETUP.md`)
- FastF1 data availability varies by session; check logs for errors
