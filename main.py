import streamlit as st
import requests
import os
import base64
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from app.data_loader import (
    fetch_data,
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers
)
from app.data_processor import (
    process_lap_data,
    process_stints,
    process_pit_stops,
    build_driver_color_map
)
from app.visualizer import (
    plot_lap_times,
    plot_tire_strategy,
    plot_pit_stop
)
from app.lap_analyzer import (
    analyze_driver_laps,
    create_timestamp_link
)
from app.race_predictor import (
    fetch_historical_austin_races,
    build_perfect_lap_profile,
    generate_simulated_race,
    calculate_race_positions,
    predict_podium,
    get_tire_strategy_summary
)
from app.race_simulator import (
    create_race_visualization,
    create_leaderboard,
    create_speed_telemetry
)

st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide", initial_sidebar_state="collapsed")

load_dotenv()

# Helper function to convert image to base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def get_base64_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode()

# F1-Themed CSS
banner_base64 = get_base64_image("qqvtKbFoWb54LN_XI4j-Q2g0oae0kRKfZ6hy84QatI8.jpg.jpg")
verstappen_base64 = get_base64_image("max-emilian-verstappen-stubble-removebg-preview.png")
verstappen_audio_base64 = get_base64_audio("du-du-du-du-max-verstappen-made-with-Voicemod.mp3")

st.markdown(f"""
<style>
    /* F1 Color Scheme */
    :root {{
        --f1-red: #E10600;
        --f1-black: #15151E;
        --f1-white: #FFFFFF;
        --f1-gold: #FFC500;
        --f1-silver: #C0C0C0;
    }}

    /* Main App Background */
    .stApp {{
        background: linear-gradient(135deg, #15151E 0%, #2d2d3d 100%);
        color: #FFFFFF;
    }}

    /* Banner at top */
    .f1-banner {{
        width: 100%;
        height: 250px;
        background-image: url('data:image/jpeg;base64,{banner_base64}');
        background-size: cover;
        background-position: center;
        border-bottom: 5px solid #E10600;
        margin-bottom: 20px;
        box-shadow: 0 5px 20px rgba(225, 6, 0, 0.5);
    }}

    /* Verstappen decorative images */
    .verstappen-corner-top {{
        position: fixed;
        top: 20px;
        right: 20px;
        width: 120px;
        height: 120px;
        background-image: url('data:image/png;base64,{verstappen_base64}');
        background-size: contain;
        background-repeat: no-repeat;
        z-index: 999;
        opacity: 0.15;
        animation: float 6s ease-in-out infinite;
    }}

    .verstappen-corner-bottom {{
        position: fixed;
        bottom: 20px;
        left: 20px;
        width: 150px;
        height: 150px;
        background-image: url('data:image/png;base64,{verstappen_base64}');
        background-size: contain;
        background-repeat: no-repeat;
        z-index: 999;
        opacity: 0.12;
        transform: scaleX(-1);
        animation: float 8s ease-in-out infinite;
    }}

    @keyframes float {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-20px); }}
    }}

    /* Title styling */
    h1 {{
        color: #E10600 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        font-weight: 900 !important;
        font-family: 'Arial Black', sans-serif !important;
    }}

    h2, h3 {{
        color: #FFC500 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background-color: #15151E;
        border-bottom: 3px solid #E10600;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: #2d2d3d;
        color: #FFFFFF;
        border-radius: 10px 10px 0 0;
        padding: 15px 30px;
        font-weight: bold;
        border: 2px solid #E10600;
    }}

    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, #E10600 0%, #c40500 100%);
        color: #FFFFFF;
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: linear-gradient(90deg, #E10600 0%, #2d2d3d 100%) !important;
        color: #FFFFFF !important;
        border-radius: 8px;
        font-weight: bold;
        border: 2px solid #FFC500;
    }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, #E10600 0%, #c40500 100%);
        color: #FFFFFF;
        border: 2px solid #FFC500;
        border-radius: 25px;
        font-weight: bold;
        padding: 10px 30px;
        transition: all 0.3s ease;
    }}

    .stButton > button:hover {{
        background: linear-gradient(135deg, #FFC500 0%, #E10600 100%);
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(225, 6, 0, 0.5);
    }}

    /* Select boxes */
    .stSelectbox > div > div {{
        background-color: #2d2d3d;
        color: #FFFFFF;
        border: 2px solid #E10600;
        border-radius: 8px;
    }}

    /* Metrics */
    [data-testid="stMetricValue"] {{
        color: #FFC500 !important;
        font-size: 28px !important;
        font-weight: bold !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: #FFFFFF !important;
    }}

    /* Info boxes */
    .stInfo {{
        background-color: rgba(45, 45, 61, 0.8);
        border-left: 5px solid #FFC500;
        color: #FFFFFF;
    }}

    /* Checkered flag pattern overlay */
    .checkered-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image:
            repeating-linear-gradient(
                45deg,
                transparent,
                transparent 10px,
                rgba(255, 255, 255, 0.01) 10px,
                rgba(255, 255, 255, 0.01) 20px
            );
        pointer-events: none;
        z-index: -1;
    }}

    /* Welcome page specific */
    .welcome-container {{
        text-align: center;
        padding: 50px 20px;
        background: rgba(21, 21, 30, 0.95);
        border-radius: 20px;
        border: 3px solid #E10600;
        box-shadow: 0 10px 40px rgba(225, 6, 0, 0.3);
        margin: 50px auto;
        max-width: 800px;
    }}

    .welcome-title {{
        font-size: 60px;
        color: #E10600;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.9);
        margin-bottom: 20px;
        font-weight: 900;
        animation: pulse 2s ease-in-out infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
    }}

    .welcome-subtitle {{
        font-size: 24px;
        color: #FFC500;
        margin-bottom: 30px;
    }}

    .welcome-verstappen {{
        width: 300px;
        margin: 30px auto;
        animation: bounce 2s ease-in-out infinite;
    }}

    @keyframes bounce {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-15px); }}
    }}
</style>

<!-- Verstappen decorative elements -->
<div class="verstappen-corner-top"></div>
<div class="verstappen-corner-bottom"></div>
<div class="checkered-overlay"></div>
""", unsafe_allow_html=True)

# ElevenLabs TTS Configuration
ELEVENLABS_API_KEY = "378360509e31179f09b7aff18b43842842bb5246814f05cf87fc56a12f939dfa"
VOICE_ID = "FmTodAVOYAC5llerS0KD"

def generate_tts_audio(text: str):
    """Generate audio from text using ElevenLabs API."""
    try:
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

        if response.status_code == 200:
            return response.content
        else:
            st.error(f"ElevenLabs API error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None

# Initialize session state for welcome page
if "entered" not in st.session_state:
    st.session_state.entered = False

# Welcome Page
if not st.session_state.entered:
    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-title">🏎️ dudududumaxverstappen</div>
        <div class="welcome-subtitle">STRATEGY DASHBOARD</div>
        <img src="data:image/png;base64,{verstappen_base64}" class="welcome-verstappen">
        <p style="font-size: 18px; color: #C0C0C0; margin: 20px 0;">
            Experience real-time race analytics, AI-powered insights, and interactive race animation.
        </p>
        <p style="font-size: 16px; color: #FFC500; margin-bottom: 30px;">
            🏁 Lap Times • 🛞 Tire Strategy • ⏱️ Pit Stops • 🤖 AI Analysis • 🎬 Race Animator
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Center the button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🏁 ENTER DASHBOARD", key="enter_btn", use_container_width=True):
            st.session_state.entered = True
            st.session_state.play_sound = True
            st.rerun()

    st.stop()

# Play Max Verstappen sound on entry
if st.session_state.get("play_sound", False):
    st.markdown(f"""
    <audio autoplay>
        <source src="data:audio/mp3;base64,{verstappen_audio_base64}" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)
    st.session_state.play_sound = False

# Banner at top of main dashboard
st.markdown('<div class="f1-banner"></div>', unsafe_allow_html=True)

st.title("🏎️ Formula 1 Strategy Dashboard")

# Create top-level navigation with session state
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Analysis"

# Radio button for tab selection (maintains state across reruns)
st.session_state.active_tab = st.radio(
    "Select View:",
    ["📊 Analysis", "🎬 Race Animator"],
    horizontal=True,
    index=0 if st.session_state.active_tab == "Analysis" else 1,
    key="tab_selector"
).split(" ", 1)[1]  # Extract just the name part

if st.session_state.active_tab == "Analysis":
    col1, col2 = st.columns(2)

    with col1:
        # Step 1: Select Year and Country dynamically
        available_years = [2023, 2024, 2025]
        selected_year = st.selectbox("Select Year", available_years, index=2)  # Default to 2025

        # Fetch all meetings for selected year
        all_meetings = fetch_data("meetings", {"year": selected_year})

        if all_meetings.empty:
            st.error("No meetings found for this year.")
            st.stop()

        available_countries = sorted(all_meetings["country_name"].dropna().unique())
        # Default to USA (Austin)
        default_country_idx = list(available_countries).index("USA") if "USA" in available_countries else 0
        selected_country = st.selectbox("Select Country", available_countries, index=default_country_idx)

        # Filter meetings for selected year and country
        filtered_meetings = all_meetings[all_meetings["country_name"] == selected_country].copy()
        filtered_meetings["label"] = filtered_meetings["meeting_name"] + " - " + filtered_meetings["location"]
        filtered_meetings = filtered_meetings.sort_values(by="meeting_key", ascending=False)

    with col2:
        # Auto-select first meeting (Austin)
        if not filtered_meetings.empty:
            selected_meeting = filtered_meetings.iloc[0]["label"]
            selected_meeting_key = filtered_meetings.iloc[0]["meeting_key"]
        else:
            st.error("No meetings found for this country and year.")
            st.stop()

        st.write(f"**Grand Prix:** {selected_meeting}")

        sessions = fetch_sessions(selected_meeting_key)
        selected_session = st.selectbox("Select Session", sessions["label"], key="session_select")
        sessions["session_type"] = sessions["label"].str.extract(r"^(.*?)\s\(")
        selected_session_type = sessions.loc[sessions["label"] == selected_session, "session_type"].values[0]
        selected_session_key = sessions.loc[sessions["label"] == selected_session, "session_key"].values[0]

    st.markdown(f"### 🏁 Session Overview: `{selected_session}`")

    # Fetch and preprocess driver info
    driver_df = fetch_drivers(selected_session_key)
    driver_df["driver_number"] = driver_df["driver_number"].astype(str)
    driver_color_map = build_driver_color_map(driver_df)
    driver_info = driver_df[["driver_number", "name_acronym"]]

    # Lap Times
    with st.expander(f"📈 Lap Time Chart for {selected_session_type} at {selected_country} {selected_year}",
                     expanded=True):
        lap_df = fetch_laps(selected_session_key)
        processed_df = process_lap_data(lap_df)

        # Merge name_acronym into the lap data
        processed_df["driver_number"] = processed_df["driver_number"].astype(str)
        processed_df = processed_df.merge(driver_info, on="driver_number", how="left")

        if processed_df.empty:
            st.warning("No lap time data found.")
        else:
            fig = plot_lap_times(processed_df, driver_color_map)
            st.plotly_chart(fig, use_container_width=True)

    # Tire Strategy
    with st.expander(f"🛞 Tire strategy for {selected_session_type} at {selected_country} {selected_year}", expanded=True):
        stints = fetch_stints(selected_session_key)
        stints_df = process_stints(stints)
        stints_df["driver_number"] = stints_df["driver_number"].astype(str)
        stints_df = stints_df.merge(driver_info, on="driver_number", how="left")

        if stints_df.empty:
            st.warning("No tire strategy data found.")
        else:
            fig = plot_tire_strategy(stints_df, driver_color_map)
            st.plotly_chart(fig, use_container_width=True)

    # Pit Stops
    with st.expander(f"⏱  Pit stop durations for {selected_session_type} at {selected_country} {selected_year}",
                     expanded=True):
        pit_stop = fetch_pit_stop(selected_session_key)
        pit_stop_df = process_pit_stops(pit_stop)
        pit_stop_df["driver_number"] = pit_stop_df["driver_number"].astype(str)
        pit_stop_df = pit_stop_df.merge(driver_info, on="driver_number", how="left")

        if pit_stop_df.empty:
            st.warning("No pit stop data found.")
        else:
            fig = plot_pit_stop(pit_stop_df, driver_color_map)
            st.plotly_chart(fig, use_container_width=True)

    # AI Lap Analysis
    st.markdown("---")
    with st.expander(f"🤖 AI Analysis for {selected_session_type} at {selected_country} {selected_year}", expanded=False):
        st.markdown("**AI-powered lap-by-lap analysis powered by Google Gemini**")

        if not processed_df.empty:
            # Get unique drivers from lap data
            available_drivers = sorted(processed_df["name_acronym"].dropna().unique())

            if available_drivers:
                # Driver selection dropdown
                selected_driver = st.selectbox(
                    "Select Driver for Lap Analysis",
                    available_drivers,
                    key="sim_driver_select"
                )

                # Get driver details
                driver_row = driver_df[driver_df["name_acronym"] == selected_driver]
                if not driver_row.empty:
                    driver_number = str(driver_row.iloc[0]["driver_number"])

                    # Filter lap data for selected driver
                    driver_laps = processed_df[processed_df["driver_number"] == driver_number].copy()
                    driver_laps = driver_laps.sort_values("lap_number")

                    if not driver_laps.empty:
                        # Calculate final position based on lap count
                        lap_counts = processed_df.groupby("driver_number")["lap_number"].max().sort_values(ascending=False)
                        final_position = None
                        for position, (drv_num, max_lap) in enumerate(lap_counts.items(), 1):
                            if str(drv_num) == driver_number:
                                final_position = position
                                break

                        # Convert position to ordinal
                        position_ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(final_position, f"{final_position}th") if final_position else None

                        # Show loading indicator while analyzing
                        with st.spinner(f"🔍 Analyzing {selected_driver}'s performance with Gemini AI..."):
                            analysis_results = analyze_driver_laps(
                                driver_number=driver_number,
                                driver_name=selected_driver,
                                lap_df=driver_laps,
                                final_position=position_ordinal
                            )

                        # Display Overall Feedback First
                        st.markdown(f"### 📊 Overall Race Feedback - {selected_driver}")

                        # Display position badge above the feedback
                        if position_ordinal:
                            cols = st.columns([1, 4])
                            with cols[0]:
                                st.metric("Final Position", position_ordinal)

                        st.info(analysis_results["overall_feedback"])

                        # TTS Button and Lap Selection in same row
                        st.markdown(f"### 📈 Lap Analysis - {selected_driver}")

                        col_btn, col_dropdown = st.columns([1, 2])

                        with col_btn:
                            if st.button("🎙️ Generate Commentary Audio", key="tts_button"):
                                with st.spinner("🎵 Generating audio commentary..."):
                                    audio_content = generate_tts_audio(analysis_results["overall_feedback"])
                                    if audio_content:
                                        st.audio(audio_content, format="audio/mp3")
                                        st.success("✅ Commentary generated!")

                        with col_dropdown:
                            # Get all available lap numbers from driver's actual lap data
                            all_lap_numbers = sorted(driver_laps["lap_number"].unique())

                            if all_lap_numbers:
                                # Create lap options: "Comprehensive Report" + all individual laps
                                lap_options = ["📋 Comprehensive Report"] + [f"Lap {int(ln)}" for ln in all_lap_numbers]
                                selected_lap_option = st.selectbox(
                                    "Select lap to analyze:",
                                    lap_options,
                                    key="lap_selector"
                                )

                                if selected_lap_option == "📋 Comprehensive Report":
                                    # Show pre-analyzed laps in expanders
                                    st.markdown("**Pre-analyzed Laps:**")
                                    if analysis_results["lap_analyses"]:
                                        for lap_analysis in analysis_results["lap_analyses"]:
                                            lap_num = lap_analysis["lap_number"]
                                            lap_time = lap_analysis["lap_time"]
                                            timestamp_link = create_timestamp_link(lap_num, selected_session_key)

                                            with st.expander(
                                                f"Lap {lap_num} | {lap_time} | 🔗 {timestamp_link}",
                                                expanded=False
                                            ):
                                                st.write(lap_analysis["analysis"])

                                                # Show lap metrics
                                                lap_row = driver_laps[driver_laps["lap_number"] == lap_num]
                                                if not lap_row.empty:
                                                    col1, col2, col3 = st.columns(3)
                                                    with col1:
                                                        st.metric("Lap Time", lap_time)
                                                    with col2:
                                                        pit_status = "🔧 Pit Out" if lap_row.iloc[0].get("is_pit_out_lap") else "Normal"
                                                        st.metric("Status", pit_status)
                                                    with col3:
                                                        st.metric("Lap #", lap_num)
                                    else:
                                        st.info("No pre-analyzed laps. Select a specific lap to analyze it.")
                                else:
                                    # Show specific lap - generate analysis at runtime
                                    selected_lap_num = int(selected_lap_option.split("Lap ")[1])

                                    with st.spinner(f"🔍 Analyzing Lap {selected_lap_num}..."):
                                        lap_result = analyze_single_lap(
                                            driver_number=driver_number,
                                            driver_name=selected_driver,
                                            lap_df=driver_laps,
                                            lap_number=selected_lap_num
                                        )

                                    if lap_result["error"]:
                                        st.error(f"❌ {lap_result['error']}")
                                    else:
                                        lap_num = lap_result["lap_number"]
                                        lap_time = lap_result["lap_time"]
                                        timestamp_link = create_timestamp_link(lap_num, selected_session_key)

                                        st.markdown(f"#### Lap {lap_num} - {lap_time}")
                                        st.markdown(f"[🔗 View on video timeline]({timestamp_link})")
                                        st.markdown(lap_result["analysis"])

                                        # Show lap metrics
                                        lap_row = driver_laps[driver_laps["lap_number"] == lap_num]
                                        if not lap_row.empty:
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.metric("Lap Time", lap_time)
                                            with col2:
                                                pit_status = "🔧 Pit Out" if lap_row.iloc[0].get("is_pit_out_lap") else "Normal"
                                                st.metric("Status", pit_status)
                                            with col3:
                                                st.metric("Lap #", lap_num)
                            else:
                                st.warning("No lap data available for analysis.")
                    else:
                        st.warning(f"No lap data found for {selected_driver}")
            else:
                st.info("No drivers available in this session.")
        else:
            st.warning("No lap data available for analysis. Please ensure lap data is loaded above.")

elif st.session_state.active_tab == "Race Animator":
    st.markdown("### 🏎️ F1 Race Replay - Austin 2024 Grand Prix")
    st.markdown("**🏁 United States Grand Prix - Circuit of the Americas**")

    # Embed HTML canvas animation
    html_content = """
    <style>
        #canvas-container {
            position: relative;
            background: #1a1a1a;
            border: 2px solid #E10600;
            border-radius: 8px;
            margin: 20px auto;
            width: fit-content;
        }

        canvas {
            display: block;
        }

        #controls {
            display: flex;
            gap: 15px;
            align-items: center;
            justify-content: center;
            margin: 20px 0;
            padding: 15px;
            background: #1a1a1a;
            border-radius: 8px;
        }

        button {
            background: #E10600;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }

        button:hover {
            background: #ff0800;
        }

        button:disabled {
            background: #555;
            cursor: not-allowed;
        }

        #speed-control {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        #info {
            display: flex;
            gap: 30px;
            justify-content: center;
            padding: 10px;
            background: #1a1a1a;
            border-radius: 8px;
            color: white;
        }

        .info-item {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .info-label {
            font-size: 12px;
            color: #999;
        }

        .info-value {
            font-size: 20px;
            font-weight: bold;
            color: #E10600;
        }

        #loading {
            text-align: center;
            font-size: 20px;
            color: #E10600;
            padding: 40px;
        }
    </style>

    <div id="loading">Loading telemetry data...</div>

    <div id="canvas-container" style="display: none;">
        <canvas id="raceCanvas" width="1000" height="700"></canvas>
    </div>

    <div id="controls" style="display: none;">
        <button id="playBtn">▶️ Play</button>
        <button id="pauseBtn" disabled>⏸️ Pause</button>
        <button id="resetBtn">⏮️ Reset</button>

        <div id="speed-control">
            <label style="color: white;">Speed:</label>
            <input type="range" id="speedSlider" min="1" max="100" value="20" step="1">
            <span id="speedValue" style="color: white;">0.05x</span>
        </div>
    </div>

    <div id="info" style="display: none;">
        <div class="info-item">
            <span class="info-label">Frame</span>
            <span class="info-value" id="frameNum">0</span>
        </div>
        <div class="info-item">
            <span class="info-label">Lap</span>
            <span class="info-value" id="lapNum">1</span>
        </div>
        <div class="info-item">
            <span class="info-label">Progress</span>
            <span class="info-value" id="progress">0%</span>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('raceCanvas');
        const ctx = canvas.getContext('2d');

        let telemetryData = null;
        let frames = [];
        let currentFrame = 0;
        let isPlaying = false;
        let animationId = null;
        let playbackSpeed = 0.05;
        let lastFrameTime = 0;
        const targetFPS = 60;
        const frameInterval = 1000 / targetFPS;

        async function loadTelemetry() {
            try {
                const response = await fetch('http://localhost:8000/api/animation-telemetry/9618');
                const data = await response.json();
                telemetryData = data.drivers;

                preprocessFrames();

                document.getElementById('loading').style.display = 'none';
                document.getElementById('canvas-container').style.display = 'block';
                document.getElementById('controls').style.display = 'flex';
                document.getElementById('info').style.display = 'flex';

                drawFrame(0);
                console.log('Loaded', Object.keys(telemetryData).length, 'drivers,', frames.length, 'frames');
            } catch (error) {
                document.getElementById('loading').textContent = 'Error: API server not running on port 8000';
                console.error('Error:', error);
            }
        }

        function preprocessFrames() {
            const drivers = Object.keys(telemetryData);
            const maxLength = Math.max(...drivers.map(d => telemetryData[d].telemetry.length));
            const sampleRate = 3;
            const numFrames = Math.floor(maxLength / sampleRate);

            for (let i = 0; i < numFrames; i++) {
                const frameData = {};
                const telemetryIdx = i * sampleRate;

                drivers.forEach(driverNum => {
                    const driver = telemetryData[driverNum];
                    const pointIdx = Math.min(telemetryIdx, driver.telemetry.length - 1);

                    if (pointIdx >= 0 && pointIdx < driver.telemetry.length) {
                        const point = driver.telemetry[pointIdx];
                        frameData[driverNum] = {
                            x: point.x,
                            y: point.y,
                            speed: point.speed,
                            lap: point.lapNumber,
                            code: driver.code,
                            color: driver.color
                        };
                    }
                });

                frames.push(frameData);
            }
        }

        function drawFrame(frameIndex) {
            if (frameIndex >= frames.length) return;

            const frame = frames[frameIndex];

            ctx.fillStyle = '#1a1a1a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw track outline
            ctx.strokeStyle = '#666666';
            ctx.lineWidth = 6;
            ctx.globalAlpha = 0.4;
            ctx.beginPath();

            const firstDriver = Object.keys(frames[0])[0];
            frames.forEach((f, idx) => {
                if (firstDriver in f) {
                    if (idx === 0) {
                        ctx.moveTo(f[firstDriver].x, f[firstDriver].y);
                    } else {
                        ctx.lineTo(f[firstDriver].x, f[firstDriver].y);
                    }
                }
            });
            ctx.stroke();
            ctx.globalAlpha = 1.0;

            // Draw drivers
            Object.keys(frame).forEach(driverNum => {
                const driver = frame[driverNum];

                ctx.fillStyle = driver.color;
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(driver.x, driver.y, 14, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();

                ctx.fillStyle = 'white';
                ctx.font = 'bold 10px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(driver.code, driver.x, driver.y);
            });

            const firstDriverData = Object.values(frame)[0];
            if (firstDriverData) {
                document.getElementById('frameNum').textContent = frameIndex;
                document.getElementById('lapNum').textContent = firstDriverData.lap;
                document.getElementById('progress').textContent =
                    ((frameIndex / frames.length) * 100).toFixed(1) + '%';
            }
        }

        function animate(currentTime) {
            if (!isPlaying) return;

            const deltaTime = currentTime - lastFrameTime;

            if (deltaTime >= frameInterval / playbackSpeed) {
                currentFrame = (currentFrame + 1) % frames.length;
                drawFrame(currentFrame);
                lastFrameTime = currentTime;
            }

            animationId = requestAnimationFrame(animate);
        }

        document.getElementById('playBtn').addEventListener('click', () => {
            isPlaying = true;
            document.getElementById('playBtn').disabled = true;
            document.getElementById('pauseBtn').disabled = false;
            lastFrameTime = performance.now();
            animate(lastFrameTime);
        });

        document.getElementById('pauseBtn').addEventListener('click', () => {
            isPlaying = false;
            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            if (animationId) cancelAnimationFrame(animationId);
        });

        document.getElementById('resetBtn').addEventListener('click', () => {
            isPlaying = false;
            currentFrame = 0;
            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            if (animationId) cancelAnimationFrame(animationId);
            drawFrame(0);
        });

        document.getElementById('speedSlider').addEventListener('input', (e) => {
            const sliderValue = parseInt(e.target.value);
            playbackSpeed = 1 / sliderValue;
            document.getElementById('speedValue').textContent = playbackSpeed.toFixed(2) + 'x';
        });

        loadTelemetry();
    </script>
    """

    import streamlit.components.v1 as components
    components.html(html_content, height=1000, scrolling=False)

