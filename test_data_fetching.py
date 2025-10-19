#!/usr/bin/env python3
"""Test script to debug historical Austin race data fetching"""

from app.data_loader import fetch_data, fetch_laps, fetch_sessions
import pandas as pd

def test_fetch_austin_data():
    """Test fetching Austin race data from OpenF1 API"""
    print("🔍 Testing OpenF1 API data fetching...\n")

    for year in [2022, 2023, 2024, 2025]:
        print(f"--- Testing Year {year} ---")
        try:
            # Fetch meetings for the year
            print(f"  Fetching meetings for {year}...")
            meetings = fetch_data("meetings", {"year": year})

            if meetings.empty:
                print(f"  ❌ No meetings found for {year}")
                continue

            # Show available columns
            print(f"  Available columns: {list(meetings.columns)}")

            # Look for Austin/USA
            print(f"  Total meetings: {len(meetings)}")
            print(f"  All meetings:")
            for idx, row in meetings.iterrows():
                print(f"    - {row.get('meeting_name', 'N/A')} | Country: {row.get('country_name', 'N/A')} | Location: {row.get('location', 'N/A')}")

            # Find Austin race - search by location first, then country
            austin = None
            if "location" in meetings.columns:
                austin = meetings[
                    (meetings["location"].str.contains("Austin", case=False, na=False)) |
                    (meetings["location"].str.contains("Circuit of Americas", case=False, na=False))
                ]

            if austin is None or austin.empty:
                # Fallback: search by country
                if "country_name" in meetings.columns:
                    austin = meetings[meetings["country_name"].str.contains("United States", case=False, na=False)]
                    # Filter to only Austin if multiple US races
                    if not austin.empty and "location" in austin.columns:
                        austin = austin[austin["location"].str.contains("Austin", case=False, na=False)]

            if austin is not None and not austin.empty:
                print(f"  ✅ Found Austin race!")
                meeting_key = austin.iloc[0]["meeting_key"]
                print(f"     Meeting Key: {meeting_key}")

                # Fetch sessions
                print(f"  Fetching sessions...")
                sessions = fetch_data("sessions", {"meeting_key": meeting_key})
                print(f"  Sessions found: {len(sessions)}")
                if not sessions.empty:
                    print(f"  Available sessions:")
                    for _, row in sessions.iterrows():
                        print(f"    - {row.get('session_name', 'N/A')} ({row.get('session_key', 'N/A')})")

                    # Fetch race session
                    race_session = sessions[sessions["session_name"] == "Race"]
                    if not race_session.empty:
                        session_key = race_session.iloc[0]["session_key"]
                        print(f"  ✅ Found Race session: {session_key}")

                        # Fetch lap data
                        print(f"  Fetching laps...")
                        laps = fetch_laps(session_key)
                        print(f"  ✅ Laps fetched: {len(laps)} laps")
                        if not laps.empty:
                            print(f"     Columns: {list(laps.columns)}")
                            print(f"     Drivers: {laps['driver_number'].nunique()}")
                    else:
                        print(f"  ❌ No Race session found")
            else:
                print(f"  ❌ Austin race not found")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

        print()

if __name__ == "__main__":
    test_fetch_austin_data()
    print("\n✅ Test complete!")
