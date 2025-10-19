import os
import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def calculate_lap_statistics(lap_df: pd.DataFrame) -> dict:
    """
    Calculate performance statistics for a driver's laps.
    Returns metrics like best lap, worst lap, average, consistency.
    """
    if lap_df.empty:
        return {}

    lap_times = lap_df["lap_duration"].dropna()
    q_low = lap_df["lap_duration"].quantile(0.01)
    q_hi  = lap_df["lap_duration"].quantile(0.90)
    lap_times = lap_times[(lap_times < q_hi) & (lap_times > q_low)]
    if len(lap_times) == 0:
        return {}

    best_lap = lap_times.min()
    worst_lap = lap_times.max()
    avg_lap = lap_times.mean()
    std_dev = lap_times.std()

    return {
        "best_lap": format_lap_time_for_analysis(best_lap),
        "worst_lap": format_lap_time_for_analysis(worst_lap),
        "average_lap": format_lap_time_for_analysis(avg_lap),
        "std_dev": f"{std_dev:.3f}s",
        "total_laps_completed": len(lap_times),
    }


def build_pit_stop_context(lap_df: pd.DataFrame) -> str:
    """
    Build context about pit stops from lap data.
    """
    pit_laps = lap_df[lap_df["is_pit_out_lap"] == True]
    if pit_laps.empty:
        return "No pit stops during race."

    pit_info = []
    for _, row in pit_laps.iterrows():
        lap_num = int(row["lap_number"])
        pit_info.append(f"Lap {lap_num}")

    return f"Pit stops: {', '.join(pit_info)}"


def detect_anomalies(lap_df: pd.DataFrame) -> str:
    """
    Detect laps with issues (crashes, DNF, safety car, etc).
    """
    anomalies = []

    # Check for missing lap durations (might indicate issues)
    missing_laps = lap_df[lap_df["lap_duration"].isna()]
    if not missing_laps.empty:
        missing_nums = missing_laps["lap_number"].tolist()
        anomalies.append(f"Missing data for laps: {missing_nums} (possible incident or DNF)")

    # Check for unusually high variance (might indicate safety car)
    lap_times = lap_df["lap_duration"].dropna()
    if len(lap_times) > 1:
        avg = lap_times.mean()
        high_variance_laps = lap_df[lap_df["lap_duration"] > avg * 1.15]
        if len(high_variance_laps) > 0:
            anomaly_laps = high_variance_laps["lap_number"].tolist()
            anomalies.append(f"Laps with significantly slower times: {anomaly_laps} (possible safety car or traffic)")

    return "\n".join(anomalies) if anomalies else "No significant anomalies detected."


def analyze_driver_laps(driver_number: str, driver_name: str, lap_df: pd.DataFrame, final_position: str = None) -> dict:
    """
    Analyze a driver's lap performance using Gemini API.

    Args:
        driver_number (str): Driver number
        driver_name (str): Driver name/acronym
        lap_df (pd.DataFrame): Lap data for the driver (should be pre-filtered)
        final_position (str): Final podium position (e.g., "1st", "2nd", "3rd", "DNF")

    Returns:
        dict: Contains lap_analyses (list of per-lap analysis) and overall_feedback
    """
    if lap_df.empty:
        return {
            "lap_analyses": [],
            "overall_feedback": "No lap data available.",
        }

    if not GEMINI_API_KEY:
        return {
            "lap_analyses": [],
            "overall_feedback": "⚠️ Gemini API key not configured. Please add GEMINI_API_KEY to your .env file.",
        }

    # Prepare lap data summary for Gemini
    lap_summary = []
    for _, row in lap_df.iterrows():
        lap_summary.append({
            "lap_number": int(row["lap_number"]),
            "lap_duration": float(row["lap_duration"]),
            "is_pit_out_lap": bool(row.get("is_pit_out_lap", False)),
            "lap_time_str": format_lap_time_for_analysis(row["lap_duration"]) if pd.notna(row["lap_duration"]) else "DNF/Crashed",
        })

    # Calculate performance statistics
    stats = calculate_lap_statistics(lap_df)
    pit_context = build_pit_stop_context(lap_df)
    anomalies = detect_anomalies(lap_df)

    # Build context for Gemini
    lap_data_text = format_lap_data_for_prompt(lap_summary)

    # Convert statistics to English format
    best_lap_english = format_lap_time_english(lap_df["lap_duration"].min()) if not lap_df["lap_duration"].empty else "N/A"
    worst_lap_english = format_lap_time_english(lap_df["lap_duration"].max()) if not lap_df["lap_duration"].empty else "N/A"
    avg_lap_english = format_lap_time_english(lap_df["lap_duration"].mean()) if not lap_df["lap_duration"].empty else "N/A"

    # Build position context
    position_context = f"\nFinal Position: {final_position}" if final_position else ""

    context = f"""
Driver: {driver_name} (#{driver_number})
Total Laps Completed: {len(lap_summary)}{position_context}

PERFORMANCE STATISTICS:
- Best Lap: {best_lap_english}
- Worst Lap: {worst_lap_english}
- Average Lap: {avg_lap_english}
- Consistency (Std Dev): {stats.get('std_dev', 'N/A')}

PIT STOP INFORMATION:
{pit_context}

RACE ANOMALIES:
{anomalies}

Lap Data (first 15 laps):
{lap_data_text}
"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Per-lap analysis - analyze only first lap
        lap_analyses = []

        # Analyze only the first lap
        for lap in lap_summary[:1]:
            prompt = f"""{context}

Analyze lap {lap['lap_number']} for {driver_name}:
- Lap Time: {lap['lap_time_str']}
- Pit Out-lap: {'Yes' if lap['is_pit_out_lap'] else 'No'}
- Context: This is the first lap. Consider cold tires and race start conditions.

Brief analysis (2 sentences max) of what happened this lap."""

            try:
                response = model.generate_content(prompt)
                lap_analyses.append({
                    "lap_number": lap["lap_number"],
                    "lap_time": lap["lap_time_str"],
                    "analysis": response.text,
                })
            except Exception as lap_error:
                st.warning(f"Lap {lap['lap_number']} analysis failed: {str(lap_error)}")
                continue

        # Overall race feedback - commentating style
        position_mention = f" finishing in {final_position} place" if final_position else ""
        overall_prompt = f"""{context}

Provide an exciting F1 race commentary analysis (3-4 sentences) for {driver_name}'s performance{position_mention}. Use commentating tone like "And there's {driver_name}..." or "What a performance..." Highlight:
- Racing pace and consistency with dramatic flair
- Any incidents, pit stops, or strategic moments
- Performance relative to expectations{' - their final podium placement' if final_position else ''}
- Stand-out moments or driving highlights"""

        overall_response = model.generate_content(overall_prompt)

        return {
            "lap_analyses": lap_analyses,
            "overall_feedback": overall_response.text,
        }

    except Exception as e:
        st.error(f"🚨 Gemini API Error: {str(e)}")
        return {
            "lap_analyses": [],
            "overall_feedback": f"Error analyzing laps: {str(e)}",
        }


def format_lap_time_for_analysis(seconds: float) -> str:
    """Format lap time in MM:SS.mmm format."""
    if pd.isna(seconds) or seconds is None:
        return "DNF/Crashed"

    seconds = float(seconds)
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{minutes:02}:{sec:02}.{millis:03}"


def format_lap_time_english(seconds: float) -> str:
    """Format lap time in plain English (e.g., '1 min 17 seconds')."""
    if pd.isna(seconds) or seconds is None:
        return "DNF/Crashed"

    seconds = float(seconds)
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    if minutes > 0:
        return f"{minutes} min {secs} seconds"
    else:
        return f"{secs}.{millis//10} seconds"


def format_lap_data_for_prompt(lap_summary: list) -> str:
    """Format lap data for Gemini prompt."""
    lines = []
    for lap in lap_summary:
        pit_flag = " [PIT OUT-LAP]" if lap["is_pit_out_lap"] else ""
        lines.append(f"Lap {lap['lap_number']}: {lap['lap_time_str']}{pit_flag}")
    return "\n".join(lines[:10])  # Show first 10 laps for context


def analyze_single_lap(driver_number: str, driver_name: str, lap_df: pd.DataFrame, lap_number: int) -> dict:
    """
    Analyze a specific lap at runtime.

    Args:
        driver_number (str): Driver number
        driver_name (str): Driver name/acronym
        lap_df (pd.DataFrame): All lap data for the driver
        lap_number (int): Specific lap to analyze

    Returns:
        dict: Contains lap analysis or error message
    """
    if not GEMINI_API_KEY:
        return {
            "error": "⚠️ Gemini API key not configured",
            "analysis": None
        }

    # Filter for specific lap
    lap_row = lap_df[lap_df["lap_number"] == lap_number]
    if lap_row.empty:
        return {
            "error": f"Lap {lap_number} not found",
            "analysis": None
        }

    lap_data = lap_row.iloc[0]

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Format lap data
        lap_time_str = format_lap_time_for_analysis(lap_data["lap_duration"]) if pd.notna(lap_data["lap_duration"]) else "DNF/Crashed"
        pit_flag = " [PIT OUT-LAP]" if lap_data.get("is_pit_out_lap") else ""

        # Build context with all laps for reference
        all_laps_summary = []
        for _, row in lap_df.iterrows():
            all_laps_summary.append({
                "lap_number": int(row["lap_number"]),
                "lap_duration": float(row["lap_duration"]),
                "is_pit_out_lap": bool(row.get("is_pit_out_lap", False)),
                "lap_time_str": format_lap_time_for_analysis(row["lap_duration"]) if pd.notna(row["lap_duration"]) else "DNF/Crashed",
            })

        # Calculate performance statistics
        stats = calculate_lap_statistics(lap_df)
        pit_context = build_pit_stop_context(lap_df)
        anomalies = detect_anomalies(lap_df)

        # Convert statistics to English format
        best_lap_english = format_lap_time_english(lap_df["lap_duration"].min()) if not lap_df["lap_duration"].empty else "N/A"
        worst_lap_english = format_lap_time_english(lap_df["lap_duration"].max()) if not lap_df["lap_duration"].empty else "N/A"
        avg_lap_english = format_lap_time_english(lap_df["lap_duration"].mean()) if not lap_df["lap_duration"].empty else "N/A"

        lap_data_text = format_lap_data_for_prompt(all_laps_summary)

        context = f"""
Driver: {driver_name} (#{driver_number})
Total Laps: {len(all_laps_summary)}

PERFORMANCE STATISTICS:
- Best Lap: {best_lap_english}
- Worst Lap: {worst_lap_english}
- Average Lap: {avg_lap_english}
- Consistency (Std Dev): {stats.get('std_dev', 'N/A')}

PIT STOP INFORMATION:
{pit_context}

RACE ANOMALIES:
{anomalies}

Lap Data (for reference):
{lap_data_text}
"""

        # Format current lap time in English
        current_lap_time_english = format_lap_time_english(lap_data["lap_duration"]) if pd.notna(lap_data["lap_duration"]) else "DNF/Crashed"

        prompt = f"""{context}

Analyze lap {lap_number} for {driver_name}:
- Lap Time: {current_lap_time_english}{pit_flag}
- Current Position in Race: Lap {lap_number} of {len(all_laps_summary)}

Detailed analysis (3-4 sentences) of what happened this lap, including:
- How this lap compares to their average performance (considering pit stops and anomalies)
- Any notable issues or strengths (e.g., if it was a pit out-lap, safety car lap, etc.)
- Current lap position and performance trend relative to other laps"""

        response = model.generate_content(prompt)

        return {
            "error": None,
            "analysis": response.text,
            "lap_time": lap_time_str,
            "lap_number": lap_number
        }

    except Exception as e:
        return {
            "error": f"Analysis failed: {str(e)}",
            "analysis": None
        }


def create_timestamp_link(lap_number: int, session_key: str) -> str:
    """
    Create a reference for jumping to a specific lap in simulation.
    Format: session_key:lap_number (can be used to navigate video/replay)
    """
    return f"{session_key}:lap_{lap_number}"
