import streamlit as st
import requests
import os
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

st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide")

load_dotenv()

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

st.title("🏎️ Formula 1 Strategy Dashboard")

# Create top-level tabs
main_tabs = st.tabs(["📊 Analysis", "🎬 Race Animator"])

with main_tabs[0]:  # Analysis tab
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

with main_tabs[1]:  # Race Animator tab
    st.markdown("""
    <iframe src="http://localhost:3333/index.html" width="100%" height="900" frameborder="0" style="border:2px solid #00d4ff; border-radius:8px;"></iframe>
    """, unsafe_allow_html=True)

    st.info("💡 **Tip:** Click 'Load Session' in the animator to fetch real telemetry data. The animator runs on port 3333 with API backend on port 8001.")

if processed_df.empty:
    st.info("Lap data is not available for this session.")
