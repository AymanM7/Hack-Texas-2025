# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Formula 1 Strategy Dashboard built with Streamlit and Plotly, powered by the OpenF1 API. It enables interactive visualization of F1 race data including lap times, tire strategies, and pit stop analysis.

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
- `create_timestamp_link()` - Generates clickable timestamps in format `session_key:lap_number` for simulation navigation
- Uses `@st.cache_data` to minimize expensive Gemini API calls
- Formats lap data into readable context for AI analysis

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

### Run the app
```bash
streamlit run main.py
```

The dashboard opens at `http://localhost:8501` by default.

## Key Integration Points

- **OpenF1 API endpoints**: `meetings` (all races), `sessions` (FP1/Quali/Race), `laps` (telemetry), `stints` (tire data), `pit` (pit stops), `drivers` (metadata)
- **Data flow**: Fetch → Process → Color-map build → Visualization
- **Caching strategy**: All API calls cached at the loader level to prevent redundant requests during UI interactions
- **Color consistency**: Driver team colors from API are normalized with `#` prefix and mapped throughout visualizations

## Notes

- Pit out-laps are flagged with a 🔧 icon in lap time tooltips
- Tire compounds follow standard F1 naming: SOFT (red), MEDIUM (yellow), HARD (white), INTERMEDIATE (green), WET (blue)
- Y-axis in lap time chart dynamically formats based on data range using MM:SS format
- The session selection dropdown (Grand Prix) is intentionally disabled to cascade from country selection

## Gemini AI Integration

- **Simulation Visualizer** section uses Google Gemini to analyze lap-by-lap performance
- Analysis is cached to minimize API costs; same driver/session analysis uses cached results
- Timestamps use format `session_key:lap_number` for external simulation navigation
- Requires valid `GEMINI_API_KEY` in `.env` file (see `GEMINI_SETUP.md` for configuration)
- Free tier has rate limits; monitor usage when analyzing multiple drivers/sessions
