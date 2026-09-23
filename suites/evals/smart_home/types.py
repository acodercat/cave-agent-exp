from typing import Dict, Any, Optional
from datetime import datetime

# ============================================================================
# SMART DEVICE CLASSES
# ============================================================================

class SmartDevice:
    """Base class for all smart home devices."""

    def __init__(self, name: str, location: str, is_on: bool = False):
        self.name = name
        self.location = location
        self.is_on = is_on
        self.power_watts = 0  # Power consumption when on

    def turn_on(self):
        """Turn the device on."""
        self.is_on = True

    def turn_off(self):
        """Turn the device off."""
        self.is_on = False

    def toggle(self):
        """Toggle device on/off state."""
        self.is_on = not self.is_on

    def get_status(self) -> Dict[str, Any]:
        """
        Get current device status.

        Returns:
            dict: {
                "name": str,
                "location": str,
                "is_on": bool,
                "power_watts": int
            }
        """
        return {
            "name": self.name,
            "location": self.location,
            "is_on": self.is_on,
            "power_watts": self.power_watts if self.is_on else 0
        }

    def __repr__(self):
        status = "ON" if self.is_on else "OFF"
        return f"{self.name} ({self.location}): {status}"


class Light(SmartDevice):
    """Smart light with brightness and color temperature control."""

    def __init__(self, name: str, location: str, is_on: bool = False,
                 brightness: int = 100, color_temp: int = 4000):
        super().__init__(name, location, is_on)
        self.brightness = brightness  # 0-100
        self.color_temp = color_temp  # Kelvin (2700-6500)
        self.max_power_watts = 10  # LED bulb max power

    def set_brightness(self, brightness: int):
        """Set brightness level (0-100)."""
        self.brightness = max(0, min(100, brightness))
        if self.brightness > 0:
            self.is_on = True
        else:
            self.is_on = False
        self._update_power()

    def set_color_temp(self, kelvin: int):
        """Set color temperature in Kelvin (2700-6500)."""
        self.color_temp = max(2700, min(6500, kelvin))

    def dim(self, amount: int = 20):
        """Dim the light by specified amount."""
        self.set_brightness(self.brightness - amount)

    def brighten(self, amount: int = 20):
        """Brighten the light by specified amount."""
        self.set_brightness(self.brightness + amount)

    def _update_power(self):
        """Update power consumption based on brightness."""
        if self.is_on:
            self.power_watts = (self.brightness / 100) * self.max_power_watts
        else:
            self.power_watts = 0

    def turn_on(self):
        """Turn the light on at current brightness."""
        self.is_on = True
        if self.brightness == 0:
            self.brightness = 100
        self._update_power()

    def turn_off(self):
        """Turn the light off."""
        self.is_on = False
        self._update_power()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current light status.

        Returns:
            dict: {
                "brightness": int,
                "color_temp": int,
                "name": str,
                "location": str,
                "is_on": bool,
                "power_watts": int
            }
        """
        return {
            **super().get_status(),
            "brightness": self.brightness,
            "color_temp": self.color_temp
        }

    def __repr__(self):
        if self.is_on:
            return f"{self.name} ({self.location}): ON @ {self.brightness}% brightness"
        else:
            return f"{self.name} ({self.location}): OFF"


class Thermostat(SmartDevice):
    """Smart thermostat with temperature and mode control."""

    def __init__(self, name: str, location: str, current_temp: int = 22,
                 target_temp: int = 22, mode: str = "auto"):
        super().__init__(name, location, is_on=True)
        self.current_temp = current_temp  # Current temperature in Celsius
        self.target_temp = target_temp    # Target temperature
        self.mode = mode  # "heat", "cool", "auto", "eco", "off"
        self.is_heating = False
        self.is_cooling = False

    def set_temperature(self, temp: int):
        """Set target temperature."""
        self.target_temp = temp
        self._update_hvac_state()

    def set_mode(self, mode: str):
        """Set thermostat mode: heat, cool, auto, eco, off."""
        self.mode = mode
        if mode == "off":
            self.is_on = False
            self.is_heating = False
            self.is_cooling = False
        else:
            self.is_on = True
            self._update_hvac_state()

    def _update_hvac_state(self):
        """Update heating/cooling state based on current conditions."""
        if not self.is_on or self.mode == "off":
            self.is_heating = False
            self.is_cooling = False
            self.power_watts = 0
            return

        temp_diff = self.target_temp - self.current_temp

        # Eco mode has wider tolerance (±3 degrees)
        tolerance = 3 if self.mode == "eco" else 1

        if self.mode == "heat":
            self.is_heating = temp_diff > tolerance
            self.is_cooling = False
        elif self.mode == "cool":
            self.is_heating = False
            self.is_cooling = temp_diff < -tolerance
        elif self.mode in ["auto", "eco"]:
            if temp_diff > tolerance:
                self.is_heating = True
                self.is_cooling = False
            elif temp_diff < -tolerance:
                self.is_heating = False
                self.is_cooling = True
            else:
                self.is_heating = False
                self.is_cooling = False

        # Update power consumption
        if self.is_heating or self.is_cooling:
            self.power_watts = 3000  # 3 kW for HVAC
        else:
            self.power_watts = 5  # Idle power

    def simulate_temperature_change(self, minutes: int):
        """Simulate temperature change over time."""
        # Heating/cooling: 0.5°C per 10 minutes
        # Natural drift: towards outside temp
        if self.is_heating:
            degrees = minutes / 20  # 0.5°C per 10 minutes = 1°C per 20 minutes
            self.current_temp = min(self.target_temp, self.current_temp + degrees)
        elif self.is_cooling:
            degrees = minutes / 20
            self.current_temp = max(self.target_temp, self.current_temp - degrees)

        self._update_hvac_state()

    def get_status(self) -> Dict[str, Any]:
        """Get current thermostat status.

        Returns:
            dict: {
                "current_temp": int,
                "target_temp": int,
                "mode": str,
                "is_heating": bool,
                "is_cooling": bool,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "current_temp": self.current_temp,
            "target_temp": self.target_temp,
            "mode": self.mode,
            "is_heating": self.is_heating,
            "is_cooling": self.is_cooling
        }

    def __repr__(self):
        action = "HEATING" if self.is_heating else "COOLING" if self.is_cooling else "IDLE"
        return f"{self.name} ({self.location}): {self.current_temp}°C → {self.target_temp}°C [{action}]"


class Lock(SmartDevice):
    """Smart door lock."""

    def __init__(self, name: str, location: str, is_locked: bool = True):
        super().__init__(name, location, is_on=True)
        self.is_locked = is_locked
        self.auto_lock = True
        self.power_watts = 2  # Low power consumption

    def lock(self):
        """Lock the door."""
        self.is_locked = True

    def unlock(self):
        """Unlock the door."""
        self.is_locked = False

    def toggle_lock(self):
        """Toggle lock state."""
        self.is_locked = not self.is_locked

    def get_status(self) -> Dict[str, Any]:
        """
        Get current lock status.

        Returns:
            dict: {
                "is_locked": bool,
                "auto_lock": bool,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "is_locked": self.is_locked,
            "auto_lock": self.auto_lock
        }

    def __repr__(self):
        status = "LOCKED" if self.is_locked else "UNLOCKED"
        return f"{self.name} ({self.location}): {status}"


class Camera(SmartDevice):
    """Security camera with motion detection."""

    def __init__(self, name: str, location: str, is_on: bool = True):
        super().__init__(name, location, is_on)
        self.is_recording = False
        self.motion_detected = False
        self.night_vision = True
        self.power_watts = 5

    def start_recording(self):
        """Start recording."""
        if self.is_on:
            self.is_recording = True

    def stop_recording(self):
        """Stop recording."""
        self.is_recording = False

    def detect_motion(self, detected: bool):
        """Set motion detection state."""
        self.motion_detected = detected
        if detected and self.is_on:
            self.is_recording = True  # Auto-record on motion

    def get_status(self) -> Dict[str, Any]:
        """Get current camera status.

        Returns:
            dict: {
                "is_recording": bool,
                "motion_detected": bool,
                "night_vision": bool,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "is_recording": self.is_recording,
            "motion_detected": self.motion_detected,
            "night_vision": self.night_vision
        }

    def __repr__(self):
        recording = "RECORDING" if self.is_recording else "STANDBY"
        motion = " [MOTION]" if self.motion_detected else ""
        return f"{self.name} ({self.location}): {recording}{motion}"


class Speaker(SmartDevice):
    """Smart speaker with volume control."""

    def __init__(self, name: str, location: str, is_on: bool = False):
        super().__init__(name, location, is_on)
        self.volume = 50
        self.is_playing = False
        self.current_source = None
        self.max_power_watts = 20

    def turn_on(self):
        """Turn the speaker on."""
        self.is_on = True
        self._update_power()

    def turn_off(self):
        """Turn the speaker off - also stops playback."""
        self.is_on = False
        self.is_playing = False
        self.current_source = None
        self._update_power()

    def set_volume(self, volume: int):
        """Set volume level (0-100)."""
        self.volume = max(0, min(100, volume))
        self._update_power()

    def play(self, source: str = "music"):
        """Start playing."""
        self.is_on = True
        self.is_playing = True
        self.current_source = source
        self._update_power()

    def pause(self):
        """Pause playback."""
        self.is_playing = False
        self._update_power()

    def stop(self):
        """Stop playback."""
        self.is_playing = False
        self.current_source = None
        self._update_power()

    def _update_power(self):
        """Update power consumption."""
        if self.is_on and self.is_playing:
            self.power_watts = (self.volume / 100) * self.max_power_watts
        else:
            self.power_watts = 2 if self.is_on else 0

    def get_status(self) -> Dict[str, Any]:
        """Get current speaker status.

        Returns:
            dict: {
                "volume": int,
                "is_playing": bool,
                "current_source": str,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "volume": self.volume,
            "is_playing": self.is_playing,
            "current_source": self.current_source
        }

    def __repr__(self):
        if self.is_playing:
            return f"{self.name} ({self.location}): PLAYING {self.current_source} @ {self.volume}%"
        else:
            status = "ON" if self.is_on else "OFF"
            return f"{self.name} ({self.location}): {status}"


class Blinds(SmartDevice):
    """Smart blinds/curtains with position control."""

    def __init__(self, name: str, location: str, position: int = 100):
        super().__init__(name, location, is_on=True)
        self.position = position  # 0 = fully closed, 100 = fully open
        self.power_watts = 5

    def set_position(self, position: int):
        """Set blinds position (0=closed, 100=open)."""
        self.position = max(0, min(100, position))

    def open(self):
        """Fully open the blinds."""
        self.position = 100

    def close(self):
        """Fully close the blinds."""
        self.position = 0

    def get_status(self) -> Dict[str, Any]:
        """Get current blinds status.

        Returns:
            dict: {
                "position": int,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "position": self.position
        }

    def __repr__(self):
        return f"{self.name} ({self.location}): {self.position}% open"


class TemperatureSensor(SmartDevice):
    """Temperature and humidity sensor."""

    def __init__(self, name: str, location: str, temperature: float = 22.0, 
                 humidity: int = 45):
        super().__init__(name, location, is_on=True)
        self.temperature = temperature  # Celsius
        self.humidity = humidity  # Percentage
        self.power_watts = 1

    def get_reading(self) -> Dict[str, Any]:
        """Get current sensor reading.

        Returns:
            dict: {
                "temperature": float,
                "humidity": int
            }
        """
        return {
            "temperature": self.temperature,
            "humidity": self.humidity
        }

    def set_reading(self, temperature: float = None, humidity: int = None):
        """Simulate sensor reading (for testing)."""
        if temperature is not None:
            self.temperature = temperature
        if humidity is not None:
            self.humidity = humidity

    def get_status(self) -> Dict[str, Any]:
        """Get current sensor status.

        Returns:
            dict: {
                "temperature": float,
                "humidity": int,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "temperature": self.temperature,
            "humidity": self.humidity
        }

    def __repr__(self):
        return f"{self.name} ({self.location}): {self.temperature}°C, {self.humidity}% humidity"


class MotionSensor(SmartDevice):
    """Motion detection sensor."""

    def __init__(self, name: str, location: str, motion_detected: bool = False):
        super().__init__(name, location, is_on=True)
        self.motion_detected = motion_detected
        self.last_motion_time: Optional[datetime] = None
        self.power_watts = 1

    def detect_motion(self):
        """Trigger motion detection."""
        self.motion_detected = True
        self.last_motion_time = datetime.now()

    def clear_motion(self):
        """Clear motion detection."""
        self.motion_detected = False

    def get_status(self) -> Dict[str, Any]:
        """Get current motion sensor status.

        Returns:
            dict: {
                "motion_detected": bool,
                "last_motion_time": str,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "motion_detected": self.motion_detected,
            "last_motion_time": str(self.last_motion_time) if self.last_motion_time else None
        }

    def __repr__(self):
        status = "MOTION DETECTED" if self.motion_detected else "No motion"
        return f"{self.name} ({self.location}): {status}"


class SmartPlug(SmartDevice):
    """Smart plug with power monitoring."""

    def __init__(self, name: str, location: str, is_on: bool = False,
                 connected_device: str = "Unknown", power_draw: float = 0):
        super().__init__(name, location, is_on)
        self.connected_device = connected_device
        self.power_draw = power_draw  # Watts when on
        self.total_energy_kwh = 0.0  # Cumulative energy usage

    def turn_on(self):
        self.is_on = True
        self.power_watts = self.power_draw

    def turn_off(self):
        self.is_on = False
        self.power_watts = 0

    def get_power_usage(self) -> float:
        """Get current power draw in watts."""
        return self.power_watts if self.is_on else 0

    def add_energy_usage(self, hours: float):
        """Add energy usage for given hours of operation."""
        if self.is_on:
            self.total_energy_kwh += (self.power_draw * hours) / 1000

    def get_status(self) -> Dict[str, Any]:
        """Get current smart plug status.

        Returns:
            dict: {
                "connected_device": str,
                "power_draw": float,
                "current_power": float,
                "total_energy_kwh": float,
                "name": str,
                "location": str,
                "is_on": bool,
                "power_watts": int
            }
        """
        return {
            **super().get_status(),
            "connected_device": self.connected_device,
            "power_draw": self.power_draw,
            "current_power": self.power_watts,
            "total_energy_kwh": self.total_energy_kwh
        }

    def __repr__(self):
        status = "ON" if self.is_on else "OFF"
        return f"{self.name} ({self.location}): {status} - {self.connected_device} @ {self.power_watts}W"


class CoffeeMaker(SmartDevice):
    """Smart coffee maker."""

    def __init__(self, name: str, location: str, water_level: int = 100,
                 beans_level: int = 100):
        super().__init__(name, location, is_on=False)
        self.water_level = water_level  # 0-100%
        self.beans_level = beans_level  # 0-100%
        self.is_brewing = False
        self.cups_ready = 0
        self.power_watts = 0
        self.brew_power = 1200  # Watts while brewing

    def brew(self, cups: int = 1):
        """Start brewing coffee."""
        if self.water_level < cups * 10:
            return "Not enough water"
        if self.beans_level < cups * 5:
            return "Not enough beans"
        
        self.is_on = True
        self.is_brewing = True
        self.power_watts = self.brew_power
        self.water_level -= cups * 10
        self.beans_level -= cups * 5
        self.cups_ready = cups
        return f"Brewing {cups} cup(s) of coffee"

    def finish_brewing(self):
        """Complete the brewing process."""
        self.is_brewing = False
        self.power_watts = 100  # Keep warm

    def turn_off(self):
        self.is_on = False
        self.is_brewing = False
        self.power_watts = 0
        self.cups_ready = 0

    def refill_water(self):
        """Refill water tank."""
        self.water_level = 100

    def refill_beans(self):
        """Refill bean hopper."""
        self.beans_level = 100

    def get_status(self) -> Dict[str, Any]:
        """Get current coffee maker status.

        Returns:
            dict: {
                "water_level": int,
                "beans_level": int,
                "is_brewing": bool,
                "cups_ready": int,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "water_level": self.water_level,
            "beans_level": self.beans_level,
            "is_brewing": self.is_brewing,
            "cups_ready": self.cups_ready
        }

    def __repr__(self):
        if self.is_brewing:
            return f"{self.name}: BREWING"
        elif self.cups_ready > 0:
            return f"{self.name}: {self.cups_ready} cup(s) ready"
        else:
            return f"{self.name}: Idle (Water: {self.water_level}%, Beans: {self.beans_level}%)"


class RobotVacuum(SmartDevice):
    """Robot vacuum cleaner."""

    def __init__(self, name: str, location: str, battery_level: int = 100,
                 dustbin_level: int = 0):
        super().__init__(name, location, is_on=False)
        self.battery_level = battery_level  # 0-100%
        self.dustbin_level = dustbin_level  # 0-100%
        self.is_cleaning = False
        self.is_docked = True
        self.current_room: Optional[str] = None
        self.cleaning_mode = "auto"  # auto, spot, edge, quiet
        self.power_watts = 0

    def start_cleaning(self, room: str = None, mode: str = "auto"):
        """Start cleaning."""
        if self.battery_level < 20:
            return "Battery too low"
        if self.dustbin_level >= 100:
            return "Dustbin full"
        
        self.is_on = True
        self.is_cleaning = True
        self.is_docked = False
        self.current_room = room
        self.cleaning_mode = mode
        self.power_watts = 40
        return f"Started cleaning {room if room else 'all rooms'}"

    def pause(self):
        """Pause cleaning."""
        self.is_cleaning = False
        self.power_watts = 5

    def resume(self):
        """Resume cleaning."""
        if self.battery_level > 10:
            self.is_cleaning = True
            self.power_watts = 40

    def return_to_dock(self):
        """Return to charging dock."""
        self.is_cleaning = False
        self.is_docked = True
        self.current_room = None
        self.is_on = False
        self.power_watts = 0

    def empty_dustbin(self):
        """Empty the dustbin."""
        self.dustbin_level = 0

    def simulate_cleaning(self, minutes: int):
        """Simulate cleaning progress."""
        if self.is_cleaning:
            self.battery_level = max(0, self.battery_level - minutes // 2)
            self.dustbin_level = min(100, self.dustbin_level + minutes // 3)
            if self.battery_level < 20:
                self.return_to_dock()

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the robot vacuum.
        Returns:
            dict: {
                "battery_level": int,
                "dustbin_level": int,
                "is_cleaning": bool,
                "is_docked": bool,
                "current_room": str,
                "cleaning_mode": str,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "battery_level": self.battery_level,
            "dustbin_level": self.dustbin_level,
            "is_cleaning": self.is_cleaning,
            "is_docked": self.is_docked,
            "current_room": self.current_room,
            "cleaning_mode": self.cleaning_mode
        }

    def __repr__(self):
        if self.is_cleaning:
            return f"{self.name}: CLEANING {self.current_room or 'home'} (Battery: {self.battery_level}%)"
        elif self.is_docked:
            return f"{self.name}: DOCKED (Battery: {self.battery_level}%)"
        else:
            return f"{self.name}: PAUSED (Battery: {self.battery_level}%)"


class TV(SmartDevice):
    """Smart TV."""

    def __init__(self, name: str, location: str, is_on: bool = False):
        super().__init__(name, location, is_on)
        self.volume = 30  # 0-100
        self.channel: Optional[str] = None
        self.input_source = "HDMI1"  # HDMI1, HDMI2, Netflix, YouTube, etc.
        self.brightness = 50
        self.power_watts = 0
        self.on_power = 100

    def turn_on(self):
        self.is_on = True
        self.power_watts = self.on_power

    def turn_off(self):
        self.is_on = False
        self.power_watts = 0

    def set_volume(self, volume: int):
        """Set volume (0-100)."""
        self.volume = max(0, min(100, volume))

    def mute(self):
        """Mute the TV."""
        self._previous_volume = self.volume
        self.volume = 0

    def unmute(self):
        """Unmute the TV."""
        if hasattr(self, '_previous_volume'):
            self.volume = self._previous_volume

    def set_input(self, source: str):
        """Set input source."""
        self.input_source = source

    def set_brightness(self, brightness: int):
        """Set screen brightness (0-100)."""
        self.brightness = max(0, min(100, brightness))

    def get_status(self) -> Dict[str, Any]:
        """Get current TV status.

        Returns:
            dict: {
                "volume": int,
                "input_source": str,
                "brightness": int,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "volume": self.volume,
            "input_source": self.input_source,
            "brightness": self.brightness
        }

    def __repr__(self):
        if self.is_on:
            return f"{self.name} ({self.location}): ON - {self.input_source} @ Vol {self.volume}"
        return f"{self.name} ({self.location}): OFF"


class GarageDoor(SmartDevice):
    """Smart garage door."""

    def __init__(self, name: str, location: str, is_open: bool = False):
        super().__init__(name, location, is_on=True)
        self.is_open = is_open
        self.is_moving = False
        self.position = 0 if not is_open else 100  # 0=closed, 100=open
        self.power_watts = 2

    def open(self):
        """Open the garage door."""
        if not self.is_open:
            self.is_moving = True
            self.is_open = True
            self.position = 100
            self.is_moving = False
            self.power_watts = 200  # Motor power

    def close(self):
        """Close the garage door."""
        if self.is_open:
            self.is_moving = True
            self.is_open = False
            self.position = 0
            self.is_moving = False
            self.power_watts = 200

    def stop(self):
        """Stop door movement."""
        self.is_moving = False
        self.power_watts = 2

    def get_status(self) -> Dict[str, Any]:
        """Get current garage door status.

        Returns:
            dict: {
                "is_open": bool,
                "is_moving": bool,
                "position": int,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "is_open": self.is_open,
            "is_moving": self.is_moving,
            "position": self.position
        }

    def __repr__(self):
        status = "OPEN" if self.is_open else "CLOSED"
        if self.is_moving:
            status = "MOVING"
        return f"{self.name} ({self.location}): {status}"


class Doorbell(SmartDevice):
    """Smart doorbell with camera."""

    def __init__(self, name: str, location: str):
        super().__init__(name, location, is_on=True)
        self.is_ringing = False
        self.is_recording = False
        self.motion_detected = False
        self.do_not_disturb = False
        self.power_watts = 3

    def ring(self):
        """Trigger doorbell ring."""
        self.is_ringing = True
        if not self.do_not_disturb:
            self.is_recording = True

    def stop_ringing(self):
        """Stop ringing."""
        self.is_ringing = False

    def enable_dnd(self):
        """Enable do not disturb."""
        self.do_not_disturb = True

    def disable_dnd(self):
        """Disable do not disturb."""
        self.do_not_disturb = False

    def start_recording(self):
        """Start recording."""
        self.is_recording = True

    def stop_recording(self):
        """Stop recording."""
        self.is_recording = False

    def get_status(self) -> Dict[str, Any]:
        """Get current doorbell status.

        Returns:
            dict: {
                "is_ringing": bool,
                "is_recording": bool,
                "motion_detected": bool,
                "do_not_disturb": bool,
                "power_watts": int,
                "name": str,
                "location": str,
                "is_on": bool
            }
        """
        return {
            **super().get_status(),
            "is_ringing": self.is_ringing,
            "is_recording": self.is_recording,
            "motion_detected": self.motion_detected,
            "do_not_disturb": self.do_not_disturb
        }

    def __repr__(self):
        status = "RINGING" if self.is_ringing else "Idle"
        dnd = " [DND]" if self.do_not_disturb else ""
        return f"{self.name} ({self.location}): {status}{dnd}"

# ============================================================================
# SCENE AND AUTOMATION CLASSES
# ============================================================================

class Room:
    """Represents a room with devices."""

    def __init__(self, name: str):
        self.name = name
        self.devices = []

    def add_device(self, device: SmartDevice):
        """Add a device to the room."""
        self.devices.append(device)

    def turn_all_off(self):
        """Turn off all devices in the room."""
        for device in self.devices:
            device.turn_off()

    def turn_all_on(self):
        """Turn on all devices in the room."""
        for device in self.devices:
            device.turn_on()

    def get_total_power(self) -> float:
        """Get total power consumption of all devices."""
        return sum(d.power_watts for d in self.devices if d.is_on)

    def __repr__(self):
        return f"Room({self.name}): {len(self.devices)} devices"