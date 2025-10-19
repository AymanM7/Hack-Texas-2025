import streamlit as st
import pandas as pd
import numpy as np
from app.data_loader import fetch_data, fetch_laps, fetch_drivers


@st.cache_data
def fetch_historical_austin_races(years=[2022, 2023, 2024, 2025]):
    """
    Fetch lap data for all Austin F1 races (historical data).
    Returns dict: {year: lap_dataframe}
    """
    austin_races = {}

    for year in years:
        try:
            # Fetch meetings for the year
            meetings = fetch_data("meetings", {"year": year})

            if meetings.empty:
                continue

            # Find Austin race - check various possible field names
            austin = None
            if "country_name" in meetings.columns:
                austin = meetings[meetings["country_name"] == "USA"]
            elif "country" in meetings.columns:
                austin = meetings[meetings["country"] == "USA"]
            elif "location" in meetings.columns:
                austin = meetings[meetings["location"].str.contains("Austin", case=False, na=False)]

            if austin is None or austin.empty:
                continue

            meeting_key = austin.iloc[0]["meeting_key"]

            # Fetch race session (filter for race, not practice/quali)
            sessions = fetch_data("sessions", {"meeting_key": meeting_key})
            race_session = sessions[sessions["session_name"] == "Race"]

            if race_session.empty:
                continue

            session_key = race_session.iloc[0]["session_key"]

            # Fetch lap data
            laps = fetch_laps(session_key)
            if not laps.empty:
                austin_races[year] = {
                    "laps": laps,
                    "session_key": session_key,
                    "meeting_key": meeting_key
                }
        except Exception as e:
            continue

    return austin_races


def build_perfect_lap_profile(historical_races):
    """
    Build a "perfect lap" profile from historical Austin races.
    Returns dict: {driver_number: perfect_lap_time, best_lap_times, consistency}
    """
    if not historical_races:
        return {}

    driver_performances = {}

    for year, race_data in historical_races.items():
        laps_df = race_data["laps"]

        # Filter valid laps (with duration, not pit out-laps on first pass)
        valid_laps = laps_df[laps_df["lap_duration"].notna()].copy()

        for driver_num in valid_laps["driver_number"].unique():
            driver_laps = valid_laps[valid_laps["driver_number"] == driver_num]

            if driver_num not in driver_performances:
                driver_performances[driver_num] = {
                    "best_lap": float('inf'),
                    "all_lap_times": [],
                    "years_raced": []
                }

            # Extract lap times
            lap_times = driver_laps["lap_duration"].values
            best_lap = lap_times.min()

            driver_performances[driver_num]["all_lap_times"].extend(lap_times)
            driver_performances[driver_num]["best_lap"] = min(
                driver_performances[driver_num]["best_lap"],
                best_lap
            )
            driver_performances[driver_num]["years_raced"].append(year)

    # Calculate statistics per driver
    perfect_profile = {}
    for driver_num, perf in driver_performances.items():
        lap_times = np.array(perf["all_lap_times"])

        perfect_profile[str(driver_num)] = {
            "best_lap": float(perf["best_lap"]),
            "average_lap": float(np.mean(lap_times)),
            "std_dev": float(np.std(lap_times)),
            "median_lap": float(np.median(lap_times)),
            "races_count": len(perf["years_raced"]),
        }

    return perfect_profile


def generate_simulated_race(perfect_profile, num_laps=56):
    """
    Generate a simulated race with perfect laps for each driver.
    Returns DataFrame with simulated telemetry
    """
    if not perfect_profile:
        return pd.DataFrame()

    simulated_data = []

    for driver_num, profile in perfect_profile.items():
        best_lap = profile["best_lap"]
        std_dev = profile["std_dev"]

        # Generate realistic lap times (best lap + random variance)
        for lap_num in range(1, num_laps + 1):
            # First lap slower (cold tires), last few potentially slower
            lap_multiplier = 1.0
            if lap_num == 1:
                lap_multiplier = 1.02
            elif lap_num > num_laps - 5:
                lap_multiplier = 1.01

            # Add small random variance
            variance = np.random.normal(0, std_dev * 0.5)
            lap_time = (best_lap * lap_multiplier) + variance
            lap_time = max(lap_time, best_lap)  # Can't be faster than best

            simulated_data.append({
                "driver_number": driver_num,
                "lap_number": lap_num,
                "lap_duration": lap_time,
                "simulated": True
            })

    return pd.DataFrame(simulated_data)


def get_driver_names(session_key):
    """Get driver names and numbers for current session"""
    try:
        drivers = fetch_drivers(session_key)
        driver_map = {}
        for _, row in drivers.iterrows():
            driver_map[str(int(row["driver_number"]))] = {
                "name": row.get("name_acronym", f"DRV{row['driver_number']}"),
                "team": row.get("team_name", "Unknown"),
                "color": row.get("team_colour", "#FFFFFF")
            }
        return driver_map
    except:
        return {}


def predict_podium(simulated_df, driver_names):
    """
    Predict final podium based on simulated race.
    Returns DataFrame with top 3 finishers and stats.
    """
    if simulated_df.empty:
        return pd.DataFrame()

    # Get final race positions (last lap)
    final_lap = simulated_df["lap_number"].max()
    final_results = simulated_df[simulated_df["lap_number"] == final_lap].copy()
    final_results = final_results.sort_values("lap_duration")

    # Get top 3
    podium = []
    for idx, (position, (_, row)) in enumerate(zip(range(1, 4), final_results.head(3).iterrows()), 1):
        driver_num = str(row["driver_number"])
        driver_info = driver_names.get(driver_num, {})
        best_lap = simulated_df[simulated_df["driver_number"] == driver_num]["lap_duration"].min()

        podium.append({
            "Position": f"🥇 P{idx}" if idx == 1 else f"🥈 P{idx}" if idx == 2 else f"🥉 P{idx}",
            "Driver #": driver_num,
            "Driver": driver_info.get("name", f"DRV{driver_num}"),
            "Team": driver_info.get("team", "Unknown"),
            "Best Lap": f"{best_lap:.3f}s",
            "Final Lap Time": f"{row['lap_duration']:.3f}s"
        })

    return pd.DataFrame(podium)


def get_tire_strategy_summary(historical_races, selected_drivers=None):
    """
    Get tire strategy summary from historical races.
    Returns dict with tire compound usage per driver.
    """
    strategy = {}

    for year, race_data in historical_races.items():
        laps_df = race_data["laps"]

        if "compound" not in laps_df.columns:
            continue

        for driver_num in laps_df["driver_number"].unique():
            if selected_drivers and str(driver_num) not in selected_drivers:
                continue

            driver_laps = laps_df[laps_df["driver_number"] == driver_num]
            compounds = driver_laps["compound"].value_counts()

            if str(driver_num) not in strategy:
                strategy[str(driver_num)] = {}

            for compound, count in compounds.items():
                if compound not in strategy[str(driver_num)]:
                    strategy[str(driver_num)][compound] = 0
                strategy[str(driver_num)][compound] += count

    return strategy


def calculate_race_positions(simulated_df):
    """
    Calculate position changes throughout the simulated race.
    Returns DataFrame with position info per lap
    """
    positions = []

    for lap in simulated_df["lap_number"].unique():
        lap_data = simulated_df[simulated_df["lap_number"] == lap].copy()
        lap_data = lap_data.sort_values("lap_duration")
        lap_data["position"] = range(1, len(lap_data) + 1)

        for _, row in lap_data.iterrows():
            positions.append({
                "lap_number": lap,
                "driver_number": row["driver_number"],
                "position": row["position"],
                "lap_time": row["lap_duration"]
            })

    return pd.DataFrame(positions)
