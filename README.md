# Formula 1 Interactive Dashboard & Race Animator

A comprehensive Formula 1 analytics platform combining real-time race data visualization, AI-powered lap analysis, and interactive race animation. Built with Streamlit, FastAPI, OpenF1 API, FastF1, and Google Gemini AI.

---

## 🏎️ Features

### Analysis Dashboard
- **Lap Time Visualization**: Interactive line charts showing lap-by-lap performance with pit stop indicators.
- **Tire Strategy Analysis**: Horizontal bar charts displaying tire compound usage across race distance.
- **Pit Stop Comparison**: Side-by-side comparison of pit stop durations.
- **AI-Powered Analysis**: **Google Gemini 2.5 Flash** provides intelligent lap-by-lap insights and performance feedback.

### Race Animator
- **Real-Time Race Replay**: Animated visualization of driver positions using FastF1 telemetry data.
- **Track-Accurate Rendering**: Precise X/Y coordinate mapping with affine transformation.
- **Multi-Session Support**: Practice, Qualifying, and Race sessions from the 2024 season.
- **Performance Optimized**: Intelligent caching and data subsampling for smooth playback.

---

## 🛠️ Technologies

- **Frontend**: Streamlit (dashboard), React (animator)
- **Backend**: FastAPI (REST API server)
- **Data Sources**: OpenF1 API, FastF1
- **AI/ML**: Google Gemini 2.5 Flash
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Voice**: ElevenLabs Text-to-Speech (optional)

---

## 📁 Project Structure


---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone [https://github.com/Garyxue213/F1.git](https://github.com/Garyxue213/F1.git)
cd F1


python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

BASE_API_URL=[https://api.openf1.org/v1/](https://api.openf1.org/v1/)
GEMINI_API_KEY=your_gemini_api_key_here

uvicorn api_server:app --reload --port 8000

streamlit run main.py --server.port 3000


---

### 📊 Dashboard Sections

### Analysis Tab

#### Session Selection
- Year picker (**2020-2025**)
- Country/Grand Prix selector
- Session type filter (Practice, Qualifying, Race)

#### Lap Time Chart
- Color-coded by driver/team
- Pit out-laps marked with 🔧 icon
- Hover for detailed lap information
- Dynamic MM:SS time formatting

#### Tire Strategy
- Stint-by-stint tire compound visualization
- Standard F1 color coding:
    - **SOFT (red)**, **MEDIUM (yellow)**, **HARD (white)**
    - **INTERMEDIATE (green)**, **WET (blue)**
- Lap range display per stint

#### Pit Stop Analysis
- Grouped bar chart comparison
- Duration in seconds
- Chronologically sorted

#### AI Lap Analysis
- Select any driver from the session
- Choose specific lap or comprehensive report
- **Gemini-powered insights** including:
    - Performance analysis
    - Pit stop strategy evaluation
    - Sector-by-sector breakdown
    - Race context and positioning

### Race Animator Tab
- Embedded interactive race visualization
- **Real-time position tracking**
- FastF1 telemetry integration
- Supports **2024 season sessions**

---

## 🔧 API Endpoints

The **FastAPI server** (`api_server.py`) provides:

### Session Data
- `GET /api/sessions/{year}/{country}` - Get available sessions
- `GET /api/animation-sessions` - List animator-compatible sessions

### Telemetry
- `GET /api/animation-telemetry/{session_key}` - **FastF1 telemetry data**
    - Cached responses for performance
    - Automatic cache warming for popular races
    - **Affine coordinate transformation** for accurate rendering

### Simulation
- `POST /api/race-simulator/{session_key}` - Race simulation and prediction

### Health
- `GET /api/health` - Server status check

---

## 🎯 Key Features Explained

### Data Caching Strategy
- **OpenF1 API calls**: Cached at loader level with `@st.cache_data`
- **FastF1 telemetry**: Server-side caching with automatic warm-up
- **Gemini AI analysis**: Cached per driver/session to minimize API costs

### Coordinate Transformation
Race Animator uses **affine transformation** to map FastF1 coordinates to visualization space:

```python
viz_coord = viz_min + (raw_coord - raw_min) / raw_range * viz_range
