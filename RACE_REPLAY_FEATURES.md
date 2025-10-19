# 🏎️ F1 Race Replay System - Features

## Overview
Interactive telemetry-based race replay system that visualizes actual race data from the Austin 2024 Grand Prix, similar to F1nsight's approach.

## Key Features

### 🎬 Race Replay Animation
- **Real Telemetry Data**: Uses actual FastF1 telemetry from Austin 2024 Race (session 9618)
- **Interactive Canvas**: Plotly-based visualization showing all drivers moving simultaneously
- **Smooth Playback**: 30 FPS animation with configurable playback speeds (0.5x to 20x)
- **Live Positions**: All drivers animate in real-time based on actual race positions

### 🎮 Playback Controls
- **▶️ Play/⏸️ Pause**: Start and stop race replay
- **⏮️ Reset**: Jump back to start
- **Timeline Slider**: Scrub through any point in the race
- **Speed Control**: 0.5x, 1.0x, 2.0x, 5.0x, 10.0x, 20.0x (default: 5x)
- **Progress Indicator**: Shows % completion

### 🏁 Track Visualization
- **Circuit Outline**: Full COTA track layout rendered in dark gray
- **Driver Markers**: Color-coded circles with driver codes (VER, HAM, LEC, etc.)
- **Motion Trails**: 5-frame trail showing recent path (semi-transparent)
- **Team Colors**: Authentic F1 team colors for each driver
- **Dark Theme**: Professional racing aesthetic (#050505 background)

### 📊 Live Race Leaderboard
- **Real-Time Positions**: Calculated based on lap + track progress
- **Driver Info**: Code, team, speed, lap number
- **Auto-Sorting**: Updates every frame to show current standings
- **Clean Display**: Compact table format

### ⚡ Performance Optimizations
1. **Frame Preprocessing**: All frames computed upfront (sample_rate=10)
2. **Track Caching**: Circuit outline pre-computed once
3. **Reduced Trails**: 5 frames instead of 10 for faster rendering
4. **Fast Animation**: 33ms per frame (30 FPS)
5. **Instant Playback**: No generation lag during animation

## Technical Implementation

### Data Pipeline
```
FastF1 API → api_server.py (affine transformation)
→ Frame Preprocessor (sample_rate=10)
→ Session State Cache
→ Plotly Animation
```

### Frame Structure
Each frame contains:
```python
{
    "driver_num": {
        "x": float,        # Track X coordinate
        "y": float,        # Track Y coordinate
        "speed": float,    # Speed in km/h
        "lap": int,        # Current lap number
        "code": str,       # Driver code (e.g., "VER")
        "name": str,       # Full driver name
        "team": str,       # Team name
        "color": str       # Team hex color
    }
}
```

### Animation Loop
1. User clicks **Play**
2. `st.session_state.anim_playing = True`
3. On each rerun:
   - Increment `st.session_state.anim_frame`
   - Lookup frame from preprocessed cache
   - Render Plotly chart with current positions
   - Sleep 33ms / playback_speed
   - `st.rerun()`
4. Stay on Race Animator tab (radio button maintains state)

## User Experience

### What You See
1. **Select Drivers**: Choose which drivers to watch (default: first 5)
2. **Auto-Preprocessing**: System generates all frames (2-5 seconds)
3. **Interactive Canvas**: Dark-themed track with colored driver markers
4. **Smooth Movement**: Cars glide around COTA lap by lap
5. **Live Updates**: Leaderboard shows current positions
6. **Speed Control**: Watch at your preferred pace

### Similar to F1nsight
- ✅ Interactive telemetry visualization
- ✅ Lap-by-lap race replay
- ✅ Actual race data from OpenF1/FastF1
- ✅ Real-time position tracking
- ✅ Detailed speed and lap information
- ✅ Professional racing aesthetic

## Performance Metrics

### Preprocessing Speed
- **5 drivers, ~2000 frames**: 3-5 seconds
- **Sample rate 10**: 50% fewer frames than rate 5
- **Track caching**: Instant (pre-computed)

### Playback Performance
- **Frame Rate**: 30 FPS
- **Default Speed**: 5x (completes race in ~1/5 real time)
- **Maximum Speed**: 20x (ultra-fast mode)
- **Responsiveness**: No lag, instant frame lookup

### Memory Usage
- **Frame Cache**: ~500KB-2MB depending on driver count
- **Track Outline**: ~50KB (X/Y coordinate arrays)
- **Session State**: Persistent across reruns

## Future Enhancements

Potential improvements:
1. **Multiple Camera Views**: Follow specific drivers
2. **Speed Heatmap**: Color track by speed zones
3. **Overtake Detection**: Highlight position changes
4. **Sector Times**: Show mini-sectors on track
5. **3D Visualization**: Use plotly 3D for elevation
6. **Video Export**: Render animation to MP4
7. **Multiple Races**: Select any GP, not just Austin 2024

## Files Modified

- `main.py`: Race Animator tab (lines 621-920)
- `app/frame_preprocessor.py`: Frame generation system
- `api_server.py`: FastF1 telemetry endpoint with affine transform

## Usage

1. Navigate to http://localhost:3000
2. Select **🎬 Race Animator** radio button
3. Wait for telemetry to load (~10-15 seconds first time)
4. Choose drivers (default: first 5)
5. Click **▶️ Play** and watch the race replay!

---

**Built with**: Python, Streamlit, Plotly, FastF1, OpenF1 API
**Inspired by**: F1nsight's interactive race replay approach
