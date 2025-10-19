import os
import streamlit as st
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def analyze_driver_laps(driver_number: str, driver_name: str, lap_df: pd.DataFrame) -> dict:
    """
    Analyze a driver's lap performance using Gemini API.

    Args:
        driver_number (str): Driver number
        driver_name (str): Driver name/acronym
        lap_df (pd.DataFrame): Lap data for the driver (should be pre-filtered)

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
            "lap_time_str": format_lap_time_for_analysis(row["lap_duration"]),
        })

    # Build context for Gemini
    lap_data_text = format_lap_data_for_prompt(lap_summary)
    context = f"""
Driver: {driver_name} (#{driver_number})
Total Laps: {len(lap_summary)}

Lap Data (first 15 laps):
{lap_data_text}
"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Per-lap analysis - analyze all laps
        lap_analyses = []

        # Analyze all laps
        for lap in lap_summary:
            prompt = f"""{context}

Analyze lap {lap['lap_number']} for {driver_name}:
- Lap Time: {lap['lap_time_str']}
- Pit Out-lap: {'Yes' if lap['is_pit_out_lap'] else 'No'}

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

        # Overall race feedback
        overall_prompt = f"""{context}

Provide brief overall feedback (3 sentences max) for {driver_name}'s race:
- Consistency
- Key moments
- Performance summary"""

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
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{minutes:02}:{sec:02}.{millis:03}"


def format_lap_data_for_prompt(lap_summary: list) -> str:
    """Format lap data for Gemini prompt."""
    lines = []
    for lap in lap_summary:
        pit_flag = " [PIT OUT-LAP]" if lap["is_pit_out_lap"] else ""
        lines.append(f"Lap {lap['lap_number']}: {lap['lap_time_str']}{pit_flag}")
    return "\n".join(lines[:10])  # Show first 10 laps for context


def create_timestamp_link(lap_number: int, session_key: str) -> str:
    """
    Create a reference for jumping to a specific lap in simulation.
    Format: session_key:lap_number (can be used to navigate video/replay)
    """
    return f"{session_key}:lap_{lap_number}"
