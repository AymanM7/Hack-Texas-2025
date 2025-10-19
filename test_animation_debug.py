#!/usr/bin/env python3
"""Debug script to test animation frames."""

import requests
from app.frame_preprocessor import preprocess_race_frames

print("=" * 60)
print("Animation Frame Debug Test")
print("=" * 60)

# Test API connection
print("\n1. Testing API connection...")
try:
    response = requests.get("http://localhost:8000/api/animation-telemetry/9618", timeout=30)
    if response.status_code == 200:
        data = response.json()
        drivers_data = data.get("drivers", {})
        print(f"✓ API connected: {len(drivers_data)} drivers loaded")
        print(f"✓ Total data points: {data.get('data_points', 0)}")

        # Check first driver
        first_driver = list(drivers_data.keys())[0]
        first_driver_data = drivers_data[first_driver]
        print(f"✓ First driver: {first_driver_data['code']} - {len(first_driver_data['telemetry'])} points")

        # Test frame preprocessing
        print("\n2. Testing frame preprocessing (sample_rate=3)...")
        frames, num_frames = preprocess_race_frames(drivers_data, sample_rate=3)
        print(f"✓ Generated {num_frames} frames")
        print(f"✓ Frames list length: {len(frames)}")

        # Check frame structure
        print("\n3. Checking frame structure...")
        if frames:
            first_frame = frames[0]
            print(f"✓ First frame has {len(first_frame)} drivers")

            if first_driver in first_frame:
                driver_in_frame = first_frame[first_driver]
                print(f"✓ Driver data keys: {list(driver_in_frame.keys())}")
                print(f"✓ Position: ({driver_in_frame['x']:.1f}, {driver_in_frame['y']:.1f})")
                print(f"✓ Speed: {driver_in_frame['speed']:.1f} km/h")
                print(f"✓ Lap: {driver_in_frame['lap']}")

            # Check position changes
            if len(frames) > 100:
                frame_100 = frames[100]
                if first_driver in frame_100:
                    dx = frame_100[first_driver]['x'] - first_frame[first_driver]['x']
                    dy = frame_100[first_driver]['y'] - first_frame[first_driver]['y']
                    distance = (dx**2 + dy**2)**0.5
                    print(f"\n4. Position change test:")
                    print(f"✓ Frame 0 position: ({first_frame[first_driver]['x']:.1f}, {first_frame[first_driver]['y']:.1f})")
                    print(f"✓ Frame 100 position: ({frame_100[first_driver]['x']:.1f}, {frame_100[first_driver]['y']:.1f})")
                    print(f"✓ Distance moved: {distance:.1f} units")

                    if distance > 10:
                        print("✅ Cars ARE moving!")
                    else:
                        print("❌ Cars NOT moving - positions too similar")

        print("\n" + "=" * 60)
        print("✅ Debug test complete!")
        print("=" * 60)

    else:
        print(f"❌ API returned status {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")
