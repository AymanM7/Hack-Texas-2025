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

# Race Predictor & Simulator
st.markdown("---")
with st.expander(f"🎮 Race Predictor - Simulated Race for {selected_country} {selected_year}", expanded=False):
    st.markdown("**Predictive race simulation based on historical Austin F1 data**")

    try:
        with st.spinner("Loading historical Austin race data..."):
            # Fetch historical data
            historical_races = fetch_historical_austin_races([2022, 2023, 2024, 2025])

        if historical_races:
            with st.spinner("Building perfect lap profile..."):
                # Build profile
                perfect_profile = build_perfect_lap_profile(historical_races)

                # Build driver name map from multiple years to get all drivers
                # Prioritize recent years but backfill with older years
                driver_name_map = {}

                for year in [2025, 2024, 2023]:  # Try 2025 first, then 2024, then 2023
                    if year in historical_races:
                        try:
                            drivers_df = fetch_drivers(historical_races[year]["session_key"])
                            drivers_added = 0
                            for _, driver_row in drivers_df.iterrows():
                                driver_num = str(int(driver_row["driver_number"]))
                                # Only add if not already in map (prioritize recent years)
                                if driver_num not in driver_name_map:
                                    driver_name_map[driver_num] = {
                                        "name": driver_row.get("name_acronym", f"DRV{driver_num}"),
                                        "team": driver_row.get("team_name", "Unknown"),
                                    }
                                    drivers_added += 1
                            if drivers_added > 0:
                                st.write(f"📊 Added {drivers_added} drivers from {year} Austin race")
                        except Exception as e:
                            pass

                st.success(f"✅ Loaded {len(driver_name_map)} total drivers from historical data")

                # Generate simulated race with driver names
                simulated_df = generate_simulated_race(perfect_profile, driver_name_map=driver_name_map, num_laps=56)
                positions_df = calculate_race_positions(simulated_df)

                st.info(f"🏁 Simulated race: {len(simulated_df)} total laps across {simulated_df['driver_number'].nunique()} drivers")

            if not simulated_df.empty:
                # Interactive Controls
                col1, col2, col3 = st.columns(3)

                with col1:
                    playback_speed = st.slider("Playback Speed", 0.25, 4.0, 1.0, 0.25)

                with col2:
                    current_lap = st.slider("Select Lap", 1, 56, 20)

                with col3:
                    st.write("")  # Spacing

                # Driver selection with names
                all_drivers = sorted(simulated_df["driver_number"].unique())

                # Create mapping of driver number to display name
                driver_display_map = {}
                driver_reverse_map = {}  # name -> number for selected drivers
                for driver_num in all_drivers:
                    driver_num_str = str(driver_num)
                    driver_name = driver_name_map.get(driver_num_str, {}).get("name", driver_num_str)
                    driver_display_map[driver_num_str] = driver_name
                    driver_reverse_map[driver_name] = driver_num_str

                # Display names in multiselect
                display_options = [driver_display_map[str(d)] for d in all_drivers]
                default_display = display_options[:2] if len(display_options) > 1 else display_options[:1]

                selected_drivers_display = st.multiselect(
                    "Select drivers to display",
                    display_options,
                    default=default_display
                )

                # Convert back to driver numbers for internal logic
                selected_drivers_sim = [driver_reverse_map[name] for name in selected_drivers_display]

                if selected_drivers_sim:
                    # Show race visualization
                    race_fig = create_race_visualization(
                        positions_df,
                        selected_drivers_sim,
                        lap_number=current_lap
                    )
                    st.plotly_chart(race_fig, use_container_width=True)

                    # Show leaderboard
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"#### Leaderboard - Lap {current_lap}")
                        leaderboard = create_leaderboard(positions_df, current_lap)
                        st.dataframe(leaderboard, hide_index=True)

                    with col2:
                        # Quick stats
                        lap_data = positions_df[positions_df["lap_number"] == current_lap]
                        if not lap_data.empty:
                            fastest_lap = lap_data.loc[lap_data["lap_time"].idxmin()]
                            driver_num_str = str(fastest_lap['driver_number'])
                            driver_display_name = driver_display_map.get(driver_num_str, driver_num_str)
                            st.metric("Fastest Lap", driver_display_name)
                            st.metric("Time", f"{fastest_lap['lap_time']:.3f}s")

                    # Telemetry chart
                    st.markdown("#### Lap Time Progression")
                    telemetry_fig = create_speed_telemetry(
                        simulated_df,
                        selected_drivers_sim
                    )
                    st.plotly_chart(telemetry_fig, use_container_width=True)

                    # Podium Prediction
                    st.markdown("---")
                    st.markdown("### 🏆 Final Podium Prediction")
                    podium_df = predict_podium(simulated_df, driver_name_map)
                    if not podium_df.empty:
                        col1, col2, col3 = st.columns([1, 1, 1])
                        for idx, (col, row) in enumerate(zip([col1, col2, col3], podium_df.iterrows())):
                            with col:
                                row_data = row[1]
                                st.markdown(f"<div style='text-align: center'><h3>{row_data['Position']}</h3></div>", unsafe_allow_html=True)
                                st.metric("Driver", f"{row_data['Driver']} #{row_data['Driver #']}")
                                st.metric("Team", row_data['Team'])
                                st.metric("Best Lap", row_data['Best Lap'])

                    # Tire Strategy from historical data
                    st.markdown("---")
                    st.markdown("### 🛞 Tire Strategy Analysis (Historical)")
                    tire_strategy = get_tire_strategy_summary(historical_races, selected_drivers_sim)
                    if tire_strategy:
                        strategy_data = []
                        for driver_num, compounds in tire_strategy.items():
                            compound_str = ", ".join([f"{comp}: {count} laps" for comp, count in sorted(compounds.items())])
                            driver_name = driver_map.get(driver_num, {}).get("name", f"DRV{driver_num}")
                            strategy_data.append({"Driver": f"{driver_name} #{driver_num}", "Tire Strategy": compound_str})

                        if strategy_data:
                            strategy_df = pd.DataFrame(strategy_data)
                            st.dataframe(strategy_df, hide_index=True, use_container_width=True)

                else:
                    st.info("Select at least one driver to visualize the race.")
            else:
                st.error("Failed to generate simulated race data.")
        else:
            st.warning("No historical Austin race data found. Make sure years 2022-2025 have available data.")

    except Exception as e:
        st.error(f"Error loading race predictor: {str(e)}")

if processed_df.empty:
    st.info("Lap data is not available for this session.")
