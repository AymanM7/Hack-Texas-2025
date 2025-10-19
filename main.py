import streamlit as st
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

st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide")

st.title("🏎️ Formula 1 Strategy Dashboard")

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
with st.expander("📋 Session Details", expanded=False):
    st.write(f"**Meeting Key:** {selected_meeting_key}")
    st.write(f"**Session Key:** {selected_session_key}")

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

# Simulation Visualizer with Gemini Analysis
st.markdown("---")
with st.expander(f"🤖 Simulation Visualizer - AI Lap Analysis for {selected_session_type} at {selected_country} {selected_year}", expanded=False):
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
                    # Show loading indicator while analyzing
                    with st.spinner(f"🔍 Analyzing {selected_driver}'s performance with Gemini AI..."):
                        analysis_results = analyze_driver_laps(
                            driver_number=driver_number,
                            driver_name=selected_driver,
                            lap_df=driver_laps
                        )

                    # Display Overall Feedback First
                    st.markdown(f"### 📊 Overall Race Feedback - {selected_driver}")
                    st.info(analysis_results["overall_feedback"])

                    # Display Lap-by-Lap Analysis
                    st.markdown(f"### 📈 Lap-by-Lap Analysis - {selected_driver}")

                    if analysis_results["lap_analyses"]:
                        # Create tabs for each lap or use expanders
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
                        st.warning("No lap analysis available.")
                else:
                    st.warning(f"No lap data found for {selected_driver}")
        else:
            st.info("No drivers available in this session.")
    else:
        st.warning("No lap data available for analysis. Please ensure lap data is loaded above.")

if processed_df.empty:
    st.info("Lap data is not available for this session.")
