# (TelemetryX2) A Formula 1 Interactive Dashboard & Race Animator

A comprehensive Formula 1 analytics platform combining real-time race data visualization, AI-powered lap analysis, and interactive race animation. Built with Streamlit, FastAPI, ElevenLabs OpenF1 API, FastF1, and Google Gemini AI.

## 🏎️ Features

### Analysis Dashboard
- **Lap Time Visualization**: Interactive line charts showing lap-by-lap performance with pit stop indicators
- **Tire Strategy Analysis**: Horizontal bar charts displaying tire compound usage across race distance
- **Pit Stop Comparison**: Side-by-side comparison of pit stop durations
- **AI-Powered Analysis**: Google Gemini 2.5 Flash provides intelligent lap-by-lap insights and performance feedback

### Race Animator
- **Real-Time Race Replay**: Animated visualization of driver positions using FastF1 telemetry data
- **Track-Accurate Rendering**: Precise X/Y coordinate mapping with affine transformation
- **Multi-Session Support**: Practice, Qualifying, and Race sessions from the 2024 season
- **Performance Optimized**: Intelligent caching and data subsampling for smooth playback

## 🛠️ Technologies

- **Frontend**: Streamlit (dashboard), React (animator)
- **Backend**: FastAPI (REST API server)
- **Data Sources**: OpenF1 API, FastF1
- **AI/ML**: Google Gemini 2.5 Flash
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Voice**: ElevenLabs Text-to-Speech (optional)

  ## Link to Devpost Submission + Demo
  https://devpost.com/software/hacktx-5gti1y?ref_content=user-portfolio&ref_feature=in_progress

## 📁 Project Structure

```
F1/
├── main.py                    # Streamlit dashboard (port 3000)
├── api_server.py              # FastAPI server (port 8000)
├── app/
│   ├── data_loader.py         # OpenF1 API wrapper with caching
│   ├── data_processor.py      # Data cleaning and transformation
│   ├── visualizer.py          # Plotly chart generators
│   ├── lap_analyzer.py        # Gemini AI lap analysis
│   ├── race_predictor.py      # Race outcome prediction
│   └── race_simulator.py      # Race simulation engine
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (API keys)
├── CLAUDE.md                  # Development guidelines
└── GEMINI_SETUP.md           # Gemini API setup instructions
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Garyxue213/F1.git
cd F1
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
BASE_API_URL=https://api.openf1.org/v1/
GEMINI_API_KEY=your_gemini_api_key_here
```

**Getting API Keys:**
- **Gemini API**: Free tier available at [Google AI Studio](https://aistudio.google.com/app/apikey)
- See `GEMINI_SETUP.md` for detailed configuration instructions

### 5. Run the Application

**Terminal 1 - API Server (Required for Race Animator):**
```bash
uvicorn api_server:app --reload --port 8000
```

**Terminal 2 - Streamlit Dashboard:**
```bash
streamlit run main.py --server.port 3000
```

**Access the Dashboard:**
```
http://localhost:3000
```

The dashboard will load with the Analysis tab active. Switch to the **Race Animator** tab to view animated race replays.

## 📊 Dashboard Sections

### Analysis Tab

1. **Session Selection**
   - Year picker (2020-2025)
   - Country/Grand Prix selector
   - Session type filter (Practice, Qualifying, Race)

2. **Lap Time Chart**
   - Color-coded by driver/team
   - Pit out-laps marked with 🔧 icon
   - Hover for detailed lap information
   - Dynamic MM:SS time formatting

3. **Tire Strategy**
   - Stint-by-stint tire compound visualization
   - Standard F1 color coding:
     - SOFT (red), MEDIUM (yellow), HARD (white)
     - INTERMEDIATE (green), WET (blue)
   - Lap range display per stint

4. **Pit Stop Analysis**
   - Grouped bar chart comparison
   - Duration in seconds
   - Chronologically sorted

5. **AI Lap Analysis**
   - Select any driver from the session
   - Choose specific lap or comprehensive report
   - Gemini-powered insights including:
     - Performance analysis
     - Pit stop strategy evaluation
     - Sector-by-sector breakdown
     - Race context and positioning

### Race Animator Tab

- Embedded interactive race visualization
- Real-time position tracking
- FastF1 telemetry integration
- Supports 2024 season sessions

## 🔧 API Endpoints

The FastAPI server (`api_server.py`) provides:

### Session Data
- `GET /api/sessions/{year}/{country}` - Get available sessions
- `GET /api/animation-sessions` - List animator-compatible sessions

### Telemetry
- `GET /api/animation-telemetry/{session_key}` - FastF1 telemetry data
  - Cached responses for performance
  - Automatic cache warming for popular races
  - Affine coordinate transformation for accurate rendering

### Simulation
- `POST /api/race-simulator/{session_key}` - Race simulation and prediction

### Health
- `GET /api/health` - Server status check

## 🎯 Key Features Explained

### Data Caching Strategy
- **OpenF1 API calls**: Cached at loader level with `@st.cache_data`
- **FastF1 telemetry**: Server-side caching with automatic warm-up
- **Gemini AI analysis**: Cached per driver/session to minimize API costs

### Coordinate Transformation
Race Animator uses affine transformation to map FastF1 coordinates to visualization space:
```python
viz_coord = viz_min + (raw_coord - raw_min) / raw_range * viz_range
```
This ensures accurate track representation across different circuits.

### AI Analysis Format
Gemini receives structured context including:
- Lap times and sector splits
- Tire compound and age
- Pit stop data
- Track position and gaps
- Weather conditions

Responses include clickable timestamps in format `session_key:lap_number` for simulation navigation.

## 📦 Requirements

Core dependencies (see `requirements.txt` for full list):
- `streamlit>=1.31.0`
- `fastapi>=0.109.0`
- `uvicorn>=0.27.0`
- `pandas>=2.2.0`
- `plotly>=5.18.0`
- `fastf1>=3.3.0`
- `google-generativeai>=0.4.0`
- `python-dotenv>=1.0.0`
- `requests>=2.31.0`

## 🎨 Color Scheme

Driver/team colors are sourced from OpenF1 API and normalized with `#` prefix for consistency across all visualizations.

## ⚠️ Important Notes

- **FastF1 Initial Load**: First session load may take 30-60 seconds as FastF1 downloads telemetry data
- **Gemini Rate Limits**: Free tier has usage quotas - analysis results are cached to minimize API calls
- **Session Keys**: Not all 2024 sessions may have complete FastF1 data - check logs for availability
- **Cache Warming**: API server pre-loads popular sessions (Abu Dhabi, Las Vegas, Singapore) on startup

## 🔮 Future Enhancements

Potential extensions:
- Live timing integration
- Comparative driver performance analysis
- Weather impact visualization
- Sector time heatmaps
- Qualifying lap analysis
- Championship standings tracker

## 📝 Development

See `CLAUDE.md` for:
- Architecture overview
- Component responsibilities
- Integration points
- Development guidelines

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- [OpenF1 API](https://openf1.org/) for comprehensive F1 data
- [FastF1](https://github.com/theOehrly/Fast-F1) for telemetry processing
- [Google Gemini](https://ai.google.dev/) for AI-powered analysis
- Formula 1 for the amazing sport


---

**Built with ❤️ for F1 fans and data enthusiasts**





