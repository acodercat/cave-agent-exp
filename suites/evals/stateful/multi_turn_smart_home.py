"""
Smart Home: 24-Hour Day Cycle - 20-Turn Multi-Turn Benchmark

A complete day simulation controlling smart home devices:
- Lights (living room, bedroom) with brightness levels
- Thermostat with temperature and mode settings
- Blinds with position control
- Speaker with volume control
- Security (door lock, camera)

Checkpoints: Turn 5, 10, 15, 20
"""

from typing import List
from cave_agent import Variable, IPythonRuntime, Type
from core.validation import ValidatorResult
from core.types import Turn, ToolCall
from evals.smart_home.types import (
    Light, Thermostat, Lock, Camera, Speaker, Blinds, TemperatureSensor
)


# ============================================================================
# INITIAL DEVICE STATE - Start of day (6:00 AM)
# ============================================================================

# Sensors
outdoor_sensor = TemperatureSensor("Outdoor Sensor", "Outside", temperature=8.0, humidity=75)
indoor_sensor = TemperatureSensor("Indoor Sensor", "Living Room", temperature=18.0, humidity=45)

# Climate
thermostat = Thermostat("Thermostat", "Hallway", current_temp=18, target_temp=18)

# Lights
living_room_light = Light("Living Room Light", "Living Room", is_on=False, brightness=0)
bedroom_light = Light("Bedroom Light", "Bedroom", is_on=False, brightness=0)

# Blinds
living_room_blinds = Blinds("Living Room Blinds", "Living Room", position=0)

# Entertainment
speaker = Speaker("Speaker", "Living Room", is_on=False)

# Security
front_door = Lock("Front Door", "Entrance", is_locked=True)
camera = Camera("Security Camera", "Front Door", is_on=True)
camera.is_recording = True


# ============================================================================
# HELPER
# ============================================================================

def _check(runtime: IPythonRuntime, expected: dict) -> list:
    """Validate runtime state against expected values."""
    errors = []
    for key, exp_val in expected.items():
        actual = runtime.retrieve(key)
        if isinstance(exp_val, float):
            if not isinstance(actual, (int, float)) or abs(actual - exp_val) > 0.5:
                errors.append(f"{key}={actual} (expected {exp_val})")
        elif isinstance(exp_val, list):
            if actual != exp_val:
                errors.append(f"{key}={actual} (expected {exp_val})")
        else:
            if actual != exp_val:
                errors.append(f"{key}={actual} (expected {exp_val})")
    return errors


# ============================================================================
# VALIDATORS - 20 TURNS
# ============================================================================

def validate_turn_1(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """
    Turn 1: Morning Wake-up (6:00 AM)
    Check outdoor temp: if < 10°C set thermostat to 22°C, else 20°C.
    Turn on bedroom light gently (30%).
    """
    thermo = runtime.retrieve("thermostat")
    bedroom = runtime.retrieve("bedroom_light")

    errors = []
    if thermo.target_temp != 22:
        errors.append(f"thermostat should be 22 (outdoor 8<10), got {thermo.target_temp}")
    if not bedroom.is_on or bedroom.brightness != 30:
        errors.append(f"bedroom_light should be 30%, got {bedroom.brightness}%")

    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 1 passed")


def validate_turn_2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 2: Open Blinds (6:30 AM) - blinds fully open, living room light medium."""
    blinds = runtime.retrieve("living_room_blinds")
    lr_light = runtime.retrieve("living_room_light")

    errors = []
    if blinds.position != 100:
        errors.append(f"blinds should be 100, got {blinds.position}")
    if not lr_light.is_on or lr_light.brightness != 50:
        errors.append(f"living_room_light should be 50%, got {lr_light.brightness}%")

    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 2 passed")


def validate_turn_3(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 3: Breakfast - bedroom off, living room bright."""
    bedroom = runtime.retrieve("bedroom_light")
    lr_light = runtime.retrieve("living_room_light")
    errors = []
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if lr_light.brightness != 80:
        errors.append(f"living_room_light should be 80%, got {lr_light.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 3 passed")


def validate_turn_4(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 4: Leaving Home - lights off, blinds privacy, door locked, thermostat eco."""
    lr_light = runtime.retrieve("living_room_light")
    blinds = runtime.retrieve("living_room_blinds")
    door = runtime.retrieve("front_door")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if blinds.position != 20:
        errors.append(f"blinds should be 20%, got {blinds.position}")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if thermo.mode != "eco" or thermo.target_temp != 18:
        errors.append(f"thermostat should be eco at 18, got {thermo.mode} at {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 4 passed")


def validate_turn_5(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 1 - Turn 5: Midday Check - camera recording."""
    camera = runtime.retrieve("camera")
    errors = []
    if not camera.is_recording:
        errors.append("camera should be recording")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 1 (Turn 5) passed")


def validate_turn_6(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 6: Return Home - door unlocked, light on, blinds partial, thermostat auto."""
    door = runtime.retrieve("front_door")
    lr_light = runtime.retrieve("living_room_light")
    blinds = runtime.retrieve("living_room_blinds")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if door.is_locked:
        errors.append("front_door should be unlocked")
    if not lr_light.is_on or lr_light.brightness != 60:
        errors.append(f"living_room_light should be 60%, got {lr_light.brightness}%")
    if blinds.position != 50:
        errors.append(f"blinds should be 50%, got {blinds.position}")
    if thermo.mode != "auto" or thermo.target_temp != 21:
        errors.append(f"thermostat should be auto at 21, got {thermo.mode} at {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 6 passed")


def validate_turn_7(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 7: Evening Relaxation - speaker on, light dimmed, blinds more closed."""
    speaker = runtime.retrieve("speaker")
    lr_light = runtime.retrieve("living_room_light")
    blinds = runtime.retrieve("living_room_blinds")
    errors = []
    # "medium volume" = medium=40 (explicit term)
    if not speaker.is_playing or speaker.volume != 40:
        errors.append(f"speaker should be playing at 40%, got {speaker.volume}%")
    # "dim the light" - check it decreased from Turn 6's default_on (60)
    if lr_light.brightness >= 60:
        errors.append(f"living_room_light should be dimmed (below 60), got {lr_light.brightness}%")
    # "close blinds more" = more_closed=30 (explicit term)
    if blinds.position != 30:
        errors.append(f"blinds should be 30%, got {blinds.position}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 7 passed")


def validate_turn_8(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 8: Dinner Time - light bright, speaker stopped, blinds closed."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    blinds = runtime.retrieve("living_room_blinds")
    errors = []
    if lr_light.brightness != 80:
        errors.append(f"living_room_light should be 80%, got {lr_light.brightness}%")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if blinds.position != 0:
        errors.append(f"blinds should be 0%, got {blinds.position}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 8 passed")


def validate_turn_9(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 9: After Dinner - light dimmed, speaker quiet."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    errors = []
    # "Dim the lights" - check it decreased from Turn 8's bright (80)
    if lr_light.brightness >= 80:
        errors.append(f"living_room_light should be dimmed (below 80), got {lr_light.brightness}%")
    # "quiet music" = quiet=30 (explicit term)
    if not speaker.is_playing or speaker.volume != 30:
        errors.append(f"speaker should be playing at 30%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 9 passed")


def validate_turn_10(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 2 - Turn 10: Security Check - door locked, camera recording."""
    door = runtime.retrieve("front_door")
    camera = runtime.retrieve("camera")
    errors = []
    if not door.is_locked:
        errors.append("front_door should be locked")
    if not camera.is_recording:
        errors.append("camera should be recording")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 2 (Turn 10) passed")


def validate_turn_11(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 11: Pre-Bedtime - speaker stopped, living room way down, bedroom on."""
    speaker = runtime.retrieve("speaker")
    lr_light = runtime.retrieve("living_room_light")
    bedroom = runtime.retrieve("bedroom_light")
    errors = []
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if lr_light.brightness != 20:
        errors.append(f"living_room_light should be 20%, got {lr_light.brightness}%")
    if not bedroom.is_on or bedroom.brightness != 40:
        errors.append(f"bedroom_light should be 40%, got {bedroom.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 11 passed")


def validate_turn_12(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 12: Bedtime Prep - living room off, bedroom dim for reading, thermostat sleep."""
    lr_light = runtime.retrieve("living_room_light")
    bedroom = runtime.retrieve("bedroom_light")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if bedroom.brightness != 20:
        errors.append(f"bedroom_light should be 20%, got {bedroom.brightness}%")
    if thermo.target_temp != 19:
        errors.append(f"thermostat should be 19, got {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 12 passed")


def validate_turn_13(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 13: Sleep Mode - bedroom off."""
    bedroom = runtime.retrieve("bedroom_light")
    errors = []
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 13 passed")


def validate_turn_14(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 14: Night Motion - camera recording, thermostat unchanged (outdoor >= 5°C)."""
    camera = runtime.retrieve("camera")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if not camera.is_recording:
        errors.append("camera should be recording")
    if thermo.target_temp != 19:
        errors.append(f"thermostat should remain 19, got {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 14 passed")


def validate_turn_15(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 3 - Turn 15: Pre-warm - thermostat 21, lights off, door locked."""
    thermo = runtime.retrieve("thermostat")
    lr_light = runtime.retrieve("living_room_light")
    bedroom = runtime.retrieve("bedroom_light")
    door = runtime.retrieve("front_door")
    errors = []
    if thermo.target_temp != 21:
        errors.append(f"thermostat should be 21, got {thermo.target_temp}")
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 3 (Turn 15) passed")


def validate_turn_16(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 16: Day 2 Wake Up - bedroom gentle, blinds partial."""
    bedroom = runtime.retrieve("bedroom_light")
    blinds = runtime.retrieve("living_room_blinds")
    errors = []
    if not bedroom.is_on or bedroom.brightness != 30:
        errors.append(f"bedroom_light should be 30%, got {bedroom.brightness}%")
    if blinds.position != 50:
        errors.append(f"blinds should be 50%, got {blinds.position}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 16 passed")


def validate_turn_17(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 17: Day 2 Morning - living room on, blinds full, bedroom off."""
    lr_light = runtime.retrieve("living_room_light")
    blinds = runtime.retrieve("living_room_blinds")
    bedroom = runtime.retrieve("bedroom_light")
    errors = []
    if not lr_light.is_on or lr_light.brightness != 60:
        errors.append(f"living_room_light should be 60%, got {lr_light.brightness}%")
    if blinds.position != 100:
        errors.append(f"blinds should be 100%, got {blinds.position}")
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 17 passed")


def validate_turn_18(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 18: Day 2 Breakfast - bright light, morning music."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    errors = []
    if lr_light.brightness != 80:
        errors.append(f"living_room_light should be 80%, got {lr_light.brightness}%")
    if not speaker.is_playing or speaker.volume != 35:
        errors.append(f"speaker should be playing at 35%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 18 passed")


def validate_turn_19(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Turn 19: Day 2 Leaving - lights off, speaker off, blinds privacy, door locked, eco mode."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    blinds = runtime.retrieve("living_room_blinds")
    door = runtime.retrieve("front_door")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if blinds.position != 20:
        errors.append(f"blinds should be 20%, got {blinds.position}")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if thermo.mode != "eco" or thermo.target_temp != 18:
        errors.append(f"thermostat should be eco at 18, got {thermo.mode} at {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 19 passed")


def validate_turn_20(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 4 - Turn 20: Final - all off, secure, eco mode."""
    lr_light = runtime.retrieve("living_room_light")
    bedroom = runtime.retrieve("bedroom_light")
    speaker = runtime.retrieve("speaker")
    door = runtime.retrieve("front_door")
    camera = runtime.retrieve("camera")
    blinds = runtime.retrieve("living_room_blinds")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if not camera.is_recording:
        errors.append("camera should be recording")
    if blinds.position != 20:
        errors.append(f"blinds should be 20%, got {blinds.position}")
    if thermo.mode != "eco" or thermo.target_temp != 18:
        errors.append(f"thermostat should be eco at 18")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 4 (Turn 20) passed - CYCLE COMPLETE")


# ============================================================================
# VALIDATORS - WEEKEND PARTY (Conversation 2)
# ============================================================================

def validate_party_turn_1(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 1: Weekend Morning - thermostat 22 (cold outside), blinds let in light, light low."""
    thermo = runtime.retrieve("thermostat")
    blinds = runtime.retrieve("living_room_blinds")
    lr_light = runtime.retrieve("living_room_light")
    errors = []
    if thermo.target_temp != 22:
        errors.append(f"thermostat should be 22 (outdoor 8<15), got {thermo.target_temp}")
    if blinds.position != 80:
        errors.append(f"blinds should be 80%, got {blinds.position}")
    if not lr_light.is_on or lr_light.brightness != 30:
        errors.append(f"living_room_light should be 30%, got {lr_light.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 1 passed")


def validate_party_turn_2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 2: Brunch - light brighten, background music."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    errors = []
    if lr_light.brightness != 70:
        errors.append(f"living_room_light should be 70%, got {lr_light.brightness}%")
    if not speaker.is_playing or speaker.volume != 25:
        errors.append(f"speaker should be playing at 25%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 2 passed")


def validate_party_turn_3(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 3: Party Prep - guest comfort temp, medium music, full blinds, bright lights."""
    thermo = runtime.retrieve("thermostat")
    speaker = runtime.retrieve("speaker")
    blinds = runtime.retrieve("living_room_blinds")
    lr_light = runtime.retrieve("living_room_light")
    errors = []
    if thermo.target_temp != 21:
        errors.append(f"thermostat should be 21, got {thermo.target_temp}")
    if speaker.volume != 40:
        errors.append(f"speaker should be 40%, got {speaker.volume}%")
    if blinds.position != 100:
        errors.append(f"blinds should be 100%, got {blinds.position}")
    if lr_light.brightness != 80:
        errors.append(f"living_room_light should be 80%, got {lr_light.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 3 passed")


def validate_party_turn_4(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 4: Guests Arriving - door unlocked, music up."""
    door = runtime.retrieve("front_door")
    speaker = runtime.retrieve("speaker")
    errors = []
    if door.is_locked:
        errors.append("front_door should be unlocked")
    if speaker.volume != 50:
        errors.append(f"speaker should be 50%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 4 passed")


def validate_party_turn_5(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 1 - Party Turn 5: Party Mode - speaker 60%, light very bright, camera recording."""
    speaker = runtime.retrieve("speaker")
    lr_light = runtime.retrieve("living_room_light")
    camera = runtime.retrieve("camera")
    errors = []
    if speaker.volume != 60:
        errors.append(f"speaker should be 60%, got {speaker.volume}%")
    if lr_light.brightness != 90:
        errors.append(f"living_room_light should be 90%, got {lr_light.brightness}%")
    if not camera.is_recording:
        errors.append("camera should be recording")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 1 (Party Turn 5) passed")


def validate_party_turn_6(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 6: Sunset - blinds partial, bedroom gentle for guests."""
    blinds = runtime.retrieve("living_room_blinds")
    bedroom = runtime.retrieve("bedroom_light")
    errors = []
    if blinds.position != 50:
        errors.append(f"blinds should be 50%, got {blinds.position}")
    if not bedroom.is_on or bedroom.brightness != 30:
        errors.append(f"bedroom_light should be 30%, got {bedroom.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 6 passed")


def validate_party_turn_7(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 7: Evening Party - blinds closed, mood lighting, speaker 70%."""
    blinds = runtime.retrieve("living_room_blinds")
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    errors = []
    if blinds.position != 0:
        errors.append(f"blinds should be 0%, got {blinds.position}")
    if lr_light.brightness != 60:
        errors.append(f"living_room_light should be 60%, got {lr_light.brightness}%")
    if speaker.volume != 70:
        errors.append(f"speaker should be 70%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 7 passed")


def validate_party_turn_8(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 8: Party Peak - speaker max, dance floor mood (dim)."""
    speaker = runtime.retrieve("speaker")
    lr_light = runtime.retrieve("living_room_light")
    errors = []
    if speaker.volume != 80:
        errors.append(f"speaker should be 80%, got {speaker.volume}%")
    if lr_light.brightness != 50:
        errors.append(f"living_room_light should be 50%, got {lr_light.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 8 passed")


def validate_party_turn_9(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 9: Winding Down - lower music, brighten lights a bit."""
    speaker = runtime.retrieve("speaker")
    lr_light = runtime.retrieve("living_room_light")
    errors = []
    # "Lower the music" is vague - just check it decreased from Turn 8's max (80)
    if speaker.volume >= 80:
        errors.append(f"speaker should be lowered from 80, got {speaker.volume}%")
    # "brighten a bit" - check it increased from Turn 8's ambiance (50)
    if lr_light.brightness <= 50:
        errors.append(f"living_room_light should be brightened (above 50), got {lr_light.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 9 passed")


def validate_party_turn_10(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 2 - Party Turn 10: Guests Leaving - speaker lowered more, door locked, bedroom off."""
    speaker = runtime.retrieve("speaker")
    door = runtime.retrieve("front_door")
    bedroom = runtime.retrieve("bedroom_light")
    errors = []
    # "Lower music more" is vague - check it's reasonably low after being lowered twice (< 60)
    if speaker.volume >= 60:
        errors.append(f"speaker should be lowered more (below 60), got {speaker.volume}%")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 2 (Party Turn 10) passed")


def validate_party_turn_11(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 11: Cleanup Start - full brightness, speaker stopped."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    errors = []
    if lr_light.brightness != 100:
        errors.append(f"living_room_light should be 100%, got {lr_light.brightness}%")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 11 passed")


def validate_party_turn_12(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 12: Cleanup Done - dim light, thermostat sleep."""
    lr_light = runtime.retrieve("living_room_light")
    thermo = runtime.retrieve("thermostat")
    errors = []
    # "Dim the lights" - check it decreased from Turn 11's full (100)
    if lr_light.brightness >= 100:
        errors.append(f"living_room_light should be dimmed (below 100), got {lr_light.brightness}%")
    # "lower thermostat for night" = night=19 (explicit term)
    if thermo.target_temp != 19:
        errors.append(f"thermostat should be 19, got {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 12 passed")


def validate_party_turn_13(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 13: Relax - dim more, soft music."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    errors = []
    # "Dim lights more" - check it decreased from Turn 12's dim (40)
    if lr_light.brightness >= 40:
        errors.append(f"living_room_light should be dimmed more (below 40), got {lr_light.brightness}%")
    # "soft relaxation music" = soft/relaxation=20 (explicit term)
    if not speaker.is_playing or speaker.volume != 20:
        errors.append(f"speaker should be playing at 20%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 13 passed")


def validate_party_turn_14(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 14: Bedtime - living room off, speaker stopped, bedroom gentle."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    bedroom = runtime.retrieve("bedroom_light")
    errors = []
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if not bedroom.is_on or bedroom.brightness != 30:
        errors.append(f"bedroom_light should be 30%, got {bedroom.brightness}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 14 passed")


def validate_party_turn_15(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 3 - Party Turn 15: Sleep - bedroom off, door locked, camera recording."""
    bedroom = runtime.retrieve("bedroom_light")
    door = runtime.retrieve("front_door")
    camera = runtime.retrieve("camera")
    errors = []
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if not camera.is_recording:
        errors.append("camera should be recording")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 3 (Party Turn 15) passed")


def validate_party_turn_16(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 16: Late Sleep - all lights remain off."""
    bedroom = runtime.retrieve("bedroom_light")
    lr_light = runtime.retrieve("living_room_light")
    errors = []
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 16 passed")


def validate_party_turn_17(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 17: Lazy Morning - bedroom on, blinds open, thermostat comfort."""
    bedroom = runtime.retrieve("bedroom_light")
    blinds = runtime.retrieve("living_room_blinds")
    thermo = runtime.retrieve("thermostat")
    errors = []
    if not bedroom.is_on or bedroom.brightness != 40:
        errors.append(f"bedroom_light should be 40%, got {bedroom.brightness}%")
    if blinds.position != 70:
        errors.append(f"blinds should be 70%, got {blinds.position}")
    if thermo.target_temp != 21:
        errors.append(f"thermostat should be 21, got {thermo.target_temp}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 17 passed")


def validate_party_turn_18(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 18: Recovery Brunch - living room on, bedroom off, blinds full, gentle music."""
    lr_light = runtime.retrieve("living_room_light")
    bedroom = runtime.retrieve("bedroom_light")
    blinds = runtime.retrieve("living_room_blinds")
    speaker = runtime.retrieve("speaker")
    errors = []
    if not lr_light.is_on or lr_light.brightness != 60:
        errors.append(f"living_room_light should be 60%, got {lr_light.brightness}%")
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if blinds.position != 100:
        errors.append(f"blinds should be 100%, got {blinds.position}")
    if not speaker.is_playing or speaker.volume != 30:
        errors.append(f"speaker should be playing at 30%, got {speaker.volume}%")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 18 passed")


def validate_party_turn_19(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Party Turn 19: Afternoon Rest - dim light, speaker stopped, blinds partial."""
    lr_light = runtime.retrieve("living_room_light")
    speaker = runtime.retrieve("speaker")
    blinds = runtime.retrieve("living_room_blinds")
    errors = []
    # "Dim lights" - check it decreased from Turn 18's default_on (60)
    if lr_light.brightness >= 60:
        errors.append(f"living_room_light should be dimmed (below 60), got {lr_light.brightness}%")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    # "close blinds partially" = partial=50 (explicit term)
    if blinds.position != 50:
        errors.append(f"blinds should be 50%, got {blinds.position}")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Party Turn 19 passed")


def validate_party_turn_20(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """CHECKPOINT 4 - Party Turn 20: Weekend Complete - eco mode, all off, secure."""
    thermo = runtime.retrieve("thermostat")
    lr_light = runtime.retrieve("living_room_light")
    bedroom = runtime.retrieve("bedroom_light")
    blinds = runtime.retrieve("living_room_blinds")
    speaker = runtime.retrieve("speaker")
    door = runtime.retrieve("front_door")
    camera = runtime.retrieve("camera")
    errors = []
    if thermo.mode != "eco":
        errors.append(f"thermostat should be eco mode, got {thermo.mode}")
    if thermo.target_temp != 18:
        errors.append(f"thermostat should be 18, got {thermo.target_temp}")
    if lr_light.is_on:
        errors.append("living_room_light should be off")
    if bedroom.is_on:
        errors.append("bedroom_light should be off")
    if blinds.position != 30:
        errors.append(f"blinds should be 30%, got {blinds.position}")
    if speaker.is_playing:
        errors.append("speaker should be stopped")
    if not door.is_locked:
        errors.append("front_door should be locked")
    if not camera.is_recording:
        errors.append("camera should be recording")
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 4 (Party Turn 20) passed - WEEKEND COMPLETE")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    # Sensors
    Variable("outdoor_sensor", outdoor_sensor, "Outdoor temperature sensor. Read .temperature to check weather conditions."),
    Variable("indoor_sensor", indoor_sensor, "Indoor temperature sensor."),

    # Climate
    Variable("thermostat", thermostat, "Thermostat. Methods: set_temperature(int), set_mode('heat'/'cool'/'auto'/'eco'). Temperature guide: cold(<10°C)=22, mild=20, comfort/auto=21, sleep/night=19, eco/away=18."),

    # Lights
    Variable("living_room_light", living_room_light, "Living room light. Methods: set_brightness(0-100), turn_on(), turn_off(). Brightness: way_down=20, gentle/low=30, dim=40, medium/ambiance=50, default_on/mood=60, brighten=70, bright=80, very_bright=90, full=100."),
    Variable("bedroom_light", bedroom_light, "Bedroom light. Methods: set_brightness(0-100), turn_on(), turn_off(). Brightness: reading=20, gentle=30, default_on=40."),

    # Blinds
    Variable("living_room_blinds", living_room_blinds, "Living room blinds. Method: set_position(0-100). Positions: closed=0, privacy/mostly_closed=20, more_closed=30, partial/partially=50, open=70, let_in_light=80, fully_open=100."),

    # Entertainment
    Variable("speaker", speaker, "Speaker. Methods: play(), stop(), set_volume(0-100). Volume: soft/relaxation=20, background=25, gentle/quiet=30, morning=35, medium=40, turn_up_more=50, party=60, turn_up_music_more=70, maximum=80."),

    # Security
    Variable("front_door", front_door, "Front door lock. Methods: lock(), unlock()."),
    Variable("camera", camera, "Security camera. Property: is_recording (bool)."),
]

types = [
    Type(Light),
    Type(Thermostat),
    Type(Lock),
    Type(Camera),
    Type(Speaker),
    Type(Blinds),
    Type(TemperatureSensor),
]

validators = {
    # Day Cycle conversation
    "validate_turn_1": validate_turn_1,
    "validate_turn_2": validate_turn_2,
    "validate_turn_3": validate_turn_3,
    "validate_turn_4": validate_turn_4,
    "validate_turn_5": validate_turn_5,
    "validate_turn_6": validate_turn_6,
    "validate_turn_7": validate_turn_7,
    "validate_turn_8": validate_turn_8,
    "validate_turn_9": validate_turn_9,
    "validate_turn_10": validate_turn_10,
    "validate_turn_11": validate_turn_11,
    "validate_turn_12": validate_turn_12,
    "validate_turn_13": validate_turn_13,
    "validate_turn_14": validate_turn_14,
    "validate_turn_15": validate_turn_15,
    "validate_turn_16": validate_turn_16,
    "validate_turn_17": validate_turn_17,
    "validate_turn_18": validate_turn_18,
    "validate_turn_19": validate_turn_19,
    "validate_turn_20": validate_turn_20,
    # Weekend Party conversation
    "validate_party_turn_1": validate_party_turn_1,
    "validate_party_turn_2": validate_party_turn_2,
    "validate_party_turn_3": validate_party_turn_3,
    "validate_party_turn_4": validate_party_turn_4,
    "validate_party_turn_5": validate_party_turn_5,
    "validate_party_turn_6": validate_party_turn_6,
    "validate_party_turn_7": validate_party_turn_7,
    "validate_party_turn_8": validate_party_turn_8,
    "validate_party_turn_9": validate_party_turn_9,
    "validate_party_turn_10": validate_party_turn_10,
    "validate_party_turn_11": validate_party_turn_11,
    "validate_party_turn_12": validate_party_turn_12,
    "validate_party_turn_13": validate_party_turn_13,
    "validate_party_turn_14": validate_party_turn_14,
    "validate_party_turn_15": validate_party_turn_15,
    "validate_party_turn_16": validate_party_turn_16,
    "validate_party_turn_17": validate_party_turn_17,
    "validate_party_turn_18": validate_party_turn_18,
    "validate_party_turn_19": validate_party_turn_19,
    "validate_party_turn_20": validate_party_turn_20,
}
