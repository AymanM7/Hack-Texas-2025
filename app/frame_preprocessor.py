"""Frame preprocessing for smooth race animation."""
import numpy as np
from typing import Dict, List, Tuple


def preprocess_race_frames(drivers_data: Dict, sample_rate: int = 5) -> Tuple[List[Dict], int]:
    """
    Preprocess all frames for smooth animation.

    Args:
        drivers_data: Raw telemetry data from API
        sample_rate: Sample every Nth point (lower = more frames, smoother but slower)

    Returns:
        (frames, total_frames) where frames is list of dicts with all driver positions per frame
    """
    # Find max telemetry length across all drivers
    max_length = max(len(data["telemetry"]) for data in drivers_data.values())

    # Sample frames
    num_frames = max_length // sample_rate
    frames = []

    for frame_idx in range(num_frames):
        telemetry_idx = frame_idx * sample_rate
        frame_data = {}

        for driver_num, driver_data in drivers_data.items():
            telemetry = driver_data["telemetry"]

            # Get telemetry point for this frame (or last available if past end)
            point_idx = min(telemetry_idx, len(telemetry) - 1)

            if point_idx >= 0 and point_idx < len(telemetry):
                point = telemetry[point_idx]
                frame_data[driver_num] = {
                    "x": point["x"],
                    "y": point["y"],
                    "speed": point["speed"],
                    "lap": point["lapNumber"],
                    "code": driver_data["code"],
                    "name": driver_data["name"],
                    "team": driver_data["team"],
                    "color": driver_data["color"]
                }

        frames.append(frame_data)

    return frames, num_frames


def generate_test_telemetry(num_drivers: int = 5, num_laps: int = 3) -> Dict:
    """
    Generate synthetic test telemetry data for validation.
    Creates drivers that move around a circular track.

    Args:
        num_drivers: Number of test drivers
        num_laps: Number of laps to simulate

    Returns:
        drivers_data dict in same format as real API
    """
    drivers_data = {}
    points_per_lap = 100
    total_points = points_per_lap * num_laps

    # Driver info
    driver_codes = ["VER", "HAM", "LEC", "NOR", "PER", "SAI", "RUS", "ALO", "OCO", "GAS"]
    driver_names = ["Verstappen", "Hamilton", "Leclerc", "Norris", "Perez", "Sainz", "Russell", "Alonso", "Ocon", "Gasly"]
    teams = ["Red Bull", "Mercedes", "Ferrari", "McLaren", "Red Bull", "Ferrari", "Mercedes", "Aston Martin", "Alpine", "Alpine"]
    colors = ["#0600EF", "#00D2BE", "#DC0000", "#FF8700", "#0600EF", "#DC0000", "#00D2BE", "#006F62", "#0090FF", "#0090FF"]

    for i in range(num_drivers):
        driver_num = str(i + 1)
        telemetry = []

        # Offset each driver slightly so they don't overlap
        lap_offset = i * 0.2

        for point_idx in range(total_points):
            # Calculate position on circular track
            angle = (point_idx / points_per_lap + lap_offset) * 2 * np.pi

            # Circular track centered at (500, 500) with radius 400
            x = 500 + 400 * np.cos(angle)
            y = 500 + 400 * np.sin(angle)

            # Simulate speed variation
            speed = 200 + 50 * np.sin(angle * 3)  # Varies between 150-250 km/h

            # Calculate current lap
            current_lap = int((point_idx + lap_offset * points_per_lap) / points_per_lap) + 1

            telemetry.append({
                "time": point_idx * 0.1,
                "x": x,
                "y": y,
                "speed": speed,
                "gear": 5,
                "throttle": 0.8,
                "brake": 0.0,
                "drs": False,
                "lapNumber": current_lap
            })

        drivers_data[driver_num] = {
            "name": driver_names[i],
            "code": driver_codes[i],
            "number": i + 1,
            "team": teams[i],
            "color": colors[i],
            "telemetry": telemetry
        }

    return drivers_data


def validate_frames(frames: List[Dict], expected_num_frames: int) -> bool:
    """
    Validate preprocessed frames.

    Returns:
        True if validation passes
    """
    if len(frames) != expected_num_frames:
        print(f"❌ Frame count mismatch: {len(frames)} != {expected_num_frames}")
        return False

    if len(frames) == 0:
        print("❌ No frames generated")
        return False

    # Check first frame has data
    first_frame = frames[0]
    if len(first_frame) == 0:
        print("❌ First frame has no driver data")
        return False

    # Check all frames have driver data
    for i, frame in enumerate(frames):
        if len(frame) == 0:
            print(f"❌ Frame {i} has no driver data")
            return False

        # Validate each driver in frame
        for driver_num, driver_data in frame.items():
            required_keys = ["x", "y", "speed", "lap", "code", "name", "team", "color"]
            for key in required_keys:
                if key not in driver_data:
                    print(f"❌ Frame {i}, Driver {driver_num} missing key: {key}")
                    return False

    print(f"✅ All {len(frames)} frames validated successfully")
    return True


def test_frame_preprocessing():
    """Run tests on frame preprocessing."""
    print("=" * 60)
    print("Testing Frame Preprocessing System")
    print("=" * 60)

    # Test 1: Generate test telemetry
    print("\n📋 Test 1: Generating test telemetry...")
    test_data = generate_test_telemetry(num_drivers=5, num_laps=3)
    assert len(test_data) == 5, "Should generate 5 drivers"
    assert all(len(d["telemetry"]) == 300 for d in test_data.values()), "Each driver should have 300 points (3 laps * 100 points)"
    print("✅ Test telemetry generated: 5 drivers, 3 laps, 300 points each")

    # Test 2: Preprocess frames
    print("\n📋 Test 2: Preprocessing frames...")
    frames, num_frames = preprocess_race_frames(test_data, sample_rate=5)
    assert num_frames == 60, f"Should generate 60 frames (300/5), got {num_frames}"
    assert len(frames) == num_frames, "Frames list length should match num_frames"
    print(f"✅ Preprocessed {num_frames} frames")

    # Test 3: Validate frames
    print("\n📋 Test 3: Validating frames...")
    is_valid = validate_frames(frames, num_frames)
    assert is_valid, "Frame validation should pass"

    # Test 4: Check driver movement
    print("\n📋 Test 4: Checking driver movement...")
    driver1_frame0 = frames[0]["1"]
    driver1_frame30 = frames[30]["1"]

    # Drivers should have moved
    distance = np.sqrt(
        (driver1_frame30["x"] - driver1_frame0["x"])**2 +
        (driver1_frame30["y"] - driver1_frame0["y"])**2
    )
    assert distance > 100, f"Driver should have moved significantly, distance: {distance}"
    print(f"✅ Driver 1 moved {distance:.1f} units in 30 frames")

    # Test 5: Check lap progression
    print("\n📋 Test 5: Checking lap progression...")
    assert driver1_frame0["lap"] == 1, "Should start at lap 1"
    last_frame = frames[-1]["1"]
    assert last_frame["lap"] >= 2, f"Should complete at least 2 laps, got {last_frame['lap']}"
    print(f"✅ Lap progression: Lap 1 → Lap {last_frame['lap']}")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_frame_preprocessing()
