import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def create_track_outline():
    """
    Create a simplified 2D track layout for Austin Circuit of the Americas.
    Returns (x_coords, y_coords) for track outline.
    """
    # Simplified COTA track outline (normalized coordinates)
    track_x = [
        0, 10, 20, 30, 35, 40, 45, 50, 55, 60, 65, 70,
        75, 80, 85, 85, 80, 75, 70, 60, 50, 40, 30, 20, 10, 0
    ]
    track_y = [
        0, 5, 8, 10, 15, 18, 20, 22, 23, 22, 20, 18,
        15, 12, 10, 0, -5, -10, -12, -15, -18, -20, -22, -20, -10, 0
    ]
    return track_x, track_y


def calculate_car_position_on_track(lap_progress, num_laps=56):
    """
    Calculate (x, y) position of car on track based on lap progress (0-1).
    lap_progress: float between 0 and 1 representing progress through lap
    """
    track_x, track_y = create_track_outline()
    total_points = len(track_x)
    position_idx = int(lap_progress * total_points) % total_points

    x = track_x[position_idx]
    y = track_y[position_idx]

    return x, y


def create_race_visualization(positions_df, selected_drivers, lap_number=1):
    """
    Create 2D visualization of race state at a given lap.
    positions_df: DataFrame with lap_number, driver_number, position, lap_time
    selected_drivers: list of driver numbers to display
    lap_number: current lap to visualize
    """
    fig = go.Figure()

    # Draw track outline
    track_x, track_y = create_track_outline()
    fig.add_trace(go.Scatter(
        x=track_x, y=track_y,
        mode='lines',
        name='Track',
        line=dict(color='gray', width=3),
        hoverinfo='skip'
    ))

    # Get lap data for current lap
    lap_data = positions_df[positions_df["lap_number"] == lap_number]

    # Color map for positions
    position_colors = {
        1: '#FFD700',  # Gold
        2: '#C0C0C0',  # Silver
        3: '#CD7F32',  # Bronze
    }

    # Plot cars
    for _, row in lap_data.iterrows():
        driver_num = str(row["driver_number"])

        if driver_num not in selected_drivers:
            continue

        # Calculate position on track (based on position in race)
        # Use position as proxy for progress
        progress = (row["position"] - 1) / max(len(lap_data), 1)
        car_x, car_y = calculate_car_position_on_track(progress)

        position = int(row["position"])
        color = position_colors.get(position, f'hsl({position * 10}, 70%, 50%)')
        lap_time = row["lap_time"]

        # Use driver_name if available, otherwise use number
        driver_display = row.get("driver_name", driver_num)

        fig.add_trace(go.Scatter(
            x=[car_x], y=[car_y],
            mode='markers+text',
            marker=dict(size=15, color=color),
            text=[f"{driver_display}<br>P{position}<br>{lap_time:.2f}s"],
            textposition="top center",
            name=f"Driver {driver_display}",
            hovertemplate=f"<b>{driver_display}</b><br>Position: P{position}<br>Lap Time: {lap_time:.2f}s<extra></extra>"
        ))

    fig.update_layout(
        title=f"Race Simulation - Lap {lap_number}",
        xaxis_title="Track X",
        yaxis_title="Track Y",
        hovermode='closest',
        height=600,
        showlegend=True,
        xaxis=dict(scaleanchor="y", scaleratio=1),
        yaxis=dict(scaleanchor="x", scaleratio=1)
    )

    return fig


def create_leaderboard(positions_df, lap_number):
    """
    Create a leaderboard table showing current positions.
    """
    lap_data = positions_df[positions_df["lap_number"] == lap_number].copy()
    lap_data = lap_data.sort_values("position")

    # Use driver_name if available, otherwise driver_number
    driver_display = []
    for _, row in lap_data.iterrows():
        if "driver_name" in row and pd.notna(row["driver_name"]):
            driver_display.append(row["driver_name"])
        else:
            driver_display.append(str(row["driver_number"]))

    leaderboard = lap_data[["position", "lap_time"]].copy()
    leaderboard["Driver"] = driver_display
    leaderboard.columns = ["Position", "Lap Time (s)", "Driver"]
    leaderboard = leaderboard[["Position", "Driver", "Lap Time (s)"]]
    leaderboard["Lap Time (s)"] = leaderboard["Lap Time (s)"].apply(lambda x: f"{x:.3f}")

    return leaderboard


def create_speed_telemetry(simulated_df, selected_drivers):
    """
    Create a line chart showing speed/lap time progression for selected drivers.
    """
    fig = go.Figure()

    for driver_num in selected_drivers:
        driver_data = simulated_df[simulated_df["driver_number"] == driver_num].copy()
        driver_data = driver_data.sort_values("lap_number")

        # Use driver_name if available, otherwise driver_number
        if not driver_data.empty and "driver_name" in driver_data.columns:
            driver_display = driver_data.iloc[0].get("driver_name", driver_num)
        else:
            driver_display = driver_num

        fig.add_trace(go.Scatter(
            x=driver_data["lap_number"],
            y=driver_data["lap_duration"],
            mode='lines+markers',
            name=driver_display,
            hovertemplate="Lap %{x}<br>Time: %{y:.3f}s<extra></extra>"
        ))

    fig.update_layout(
        title="Lap Time Progression (Simulated Race)",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        height=400,
        hovermode='x unified'
    )

    return fig
