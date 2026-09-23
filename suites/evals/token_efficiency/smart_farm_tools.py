from typing import Any, List


def get_sensor_data(farm_zone: str, sensor_type: str, start_time: str, end_time: str) -> dict[str, Any]:
    """
    Get sensor data from a specific farm zone within a time range.

    Parameters:
        farm_zone (str): [Required] Farm zone identifier (e.g., 'greenhouse_a', 'greenhouse_b', 'field_c', 'nursery_d')
        sensor_type (str): [Required] Type of sensor (e.g., 'soil_moisture', 'air_temp', 'air_humidity', 'light_intensity', 'ph_level', 'co2_level')
        start_time (str): [Required] Start time in YYYY-MM-DD HH:MM format (e.g., '2024-01-15 08:00')
        end_time (str): [Required] End time in YYYY-MM-DD HH:MM format (e.g., '2024-01-15 18:00')
    
    Returns:
        dict: {
            "farm_zone": str,
            "sensor_type": str,
            "time_range": {"start": str, "end": str},
            "readings": [
                {"timestamp": str, "value": float, "unit": str, "status": str}
            ],
            "average": float,
            "min": float,
            "max": float
        }
    
    Example:
        get_sensor_data("greenhouse_a", "soil_moisture", "2024-01-15 08:00", "2024-01-15 12:00")
        # Returns soil moisture readings for greenhouse A from 8AM to 12PM
    
    Raises:
        ValueError: If farm zone, sensor type not found, or invalid time format
    """
    # Simulated sensor data
    sensor_database = {
        "greenhouse_a": {
            "soil_moisture": [
                {"timestamp": "2024-01-15 08:00", "value": 45.2, "unit": "%", "status": "low"},
                {"timestamp": "2024-01-15 10:00", "value": 48.1, "unit": "%", "status": "low"},
                {"timestamp": "2024-01-15 12:00", "value": 42.3, "unit": "%", "status": "low"}
            ],
            "air_humidity": [
                {"timestamp": "2024-01-15 08:00", "value": 68.5, "unit": "%", "status": "normal"},
                {"timestamp": "2024-01-15 10:00", "value": 72.1, "unit": "%", "status": "normal"},
                {"timestamp": "2024-01-15 12:00", "value": 65.3, "unit": "%", "status": "normal"}
            ],
            "air_temp": [
                {"timestamp": "2024-01-15 08:00", "value": 24.5, "unit": "°C", "status": "normal"},
                {"timestamp": "2024-01-15 10:00", "value": 28.2, "unit": "°C", "status": "normal"},
                {"timestamp": "2024-01-15 12:00", "value": 32.1, "unit": "°C", "status": "high"}
            ]
        },
        "greenhouse_b": {
            "soil_moisture": [
                {"timestamp": "2024-01-15 08:00", "value": 72.4, "unit": "%", "status": "normal"},
                {"timestamp": "2024-01-15 10:00", "value": 68.9, "unit": "%", "status": "normal"},
                {"timestamp": "2024-01-15 12:00", "value": 64.1, "unit": "%", "status": "normal"}
            ],
            "air_humidity": [
                {"timestamp": "2024-01-15 08:00", "value": 78.5, "unit": "%", "status": "high"},
                {"timestamp": "2024-01-15 10:00", "value": 82.1, "unit": "%", "status": "high"},
                {"timestamp": "2024-01-15 12:00", "value": 85.3, "unit": "%", "status": "critical"}
            ],
            "air_temp": [
                {"timestamp": "2024-01-15 08:00", "value": 34.5, "unit": "°C", "status": "high"},
                {"timestamp": "2024-01-15 10:00", "value": 32.2, "unit": "°C", "status": "high"},
                {"timestamp": "2024-01-15 12:00", "value": 32.1, "unit": "°C", "status": "high"}
            ]
        }
    }
    
    if farm_zone not in sensor_database:
        raise ValueError(f"Farm zone '{farm_zone}' not found. Available zones: {list(sensor_database.keys())}")
    
    if sensor_type not in sensor_database[farm_zone]:
        raise ValueError(f"Sensor type '{sensor_type}' not found in {farm_zone}")
    
    readings = sensor_database[farm_zone][sensor_type]
    values = [r["value"] for r in readings]
    
    return {
        "farm_zone": farm_zone,
        "sensor_type": sensor_type,
        "time_range": {"start": start_time, "end": end_time},
        "readings": readings,
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values)
    }


def control_irrigation_system(farm_zone: str, action: str, duration_minutes: int = None, water_amount_liters: int = None) -> dict[str, Any]:
    """
    Control the irrigation system in a specific farm zone.

    Parameters:
        farm_zone (str): [Required] Farm zone identifier (e.g., 'greenhouse_a', 'greenhouse_b', 'field_c', 'nursery_d')
        action (str): [Required] Action to perform ('start', 'stop', 'status')
        duration_minutes (int): [Optional] Duration in minutes for irrigation (required for 'start' actions, e.g., 30)
        water_amount_liters (int): [Optional] Amount of water in liters (e.g., 500, auto-calculated if not provided)
    
    Returns:
        dict: {
            "farm_zone": str,
            "action": str,
            "status": str,
            "duration_minutes": int,
            "water_amount_liters": int,
            "estimated_completion": str,
            "valve_status": str
        }
    
    Example:
        control_irrigation_system("greenhouse_a", "start", duration_minutes=45, water_amount_liters=300)
        # Starts irrigation in greenhouse A for 45 minutes with 300 liters
    
    Raises:
        ValueError: If farm zone not found, invalid action, or missing required parameters
    """
    valid_zones = ["greenhouse_a", "greenhouse_b", "field_c", "nursery_d"]
    valid_actions = ["start", "stop", "status"]
    
    if farm_zone not in valid_zones:
        raise ValueError(f"Invalid farm zone. Available zones: {valid_zones}")
    
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Available actions: {valid_actions}")
    
    if action in ["start"] and duration_minutes is None:
        raise ValueError(f"Duration is required for '{action}' action")
    
    # Auto-calculate water amount if not provided
    if action in ["start"] and water_amount_liters is None:
        # Default: 10 liters per minute
        water_amount_liters = duration_minutes * 10
    
    
    return {
        "farm_zone": farm_zone,
        "action": action,
        "status": "success" if action != "status" else "active",
        "duration_minutes": duration_minutes or 0,
        "water_amount_liters": water_amount_liters or 0,
        "estimated_completion": "2024-01-15 15:15" if duration_minutes else None,
        "valve_status": "open" if action == "start" else "closed"
    }


def control_climate_system(farm_zone: str, device_type: str, action: str, intensity: int = None, temperature: float = None) -> dict[str, Any]:
    """
    Control climate devices (fans, lights, heaters) in a specific farm zone.

    Parameters:
        farm_zone (str): [Required] Farm zone identifier (e.g., 'greenhouse_a', 'greenhouse_b', 'field_c', 'nursery_d')
        device_type (str): [Required] Device type ('ventilation_fan', 'led_light', 'heater', 'humidifier', 'co2_generator')
        action (str): [Required] Action to perform ('on', 'off', 'adjust', 'status')
        intensity (int): [Optional] Intensity level 1-10 (required for 'adjust' action, e.g., 7)
        temperature (float): [Optional] Target temperature in Celsius for heaters (e.g., 26.5)
    
    Returns:
        dict: {
            "farm_zone": str,
            "device_type": str,
            "action": str,
            "status": str,
            "intensity": int,
            "target_temperature": float,
            "power_consumption_watts": int,
            "estimated_runtime_hours": float
        }
    
    Example:
        control_climate_system("greenhouse_a", "ventilation_fan", "adjust", intensity=8)
        # Sets ventilation fan in greenhouse A to intensity level 8
    
    Raises:
        ValueError: If farm zone, device type not found, or invalid parameters
    """
    valid_zones = ["greenhouse_a", "greenhouse_b", "field_c", "nursery_d"]
    valid_devices = ["ventilation_fan", "led_light", "heater", "humidifier", "co2_generator"]
    valid_actions = ["on", "off", "adjust", "status"]
    
    if farm_zone not in valid_zones:
        raise ValueError(f"Invalid farm zone. Available zones: {valid_zones}")
    
    if device_type not in valid_devices:
        raise ValueError(f"Invalid device type. Available devices: {valid_devices}")
    
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Available actions: {valid_actions}")
    
    if action == "adjust" and intensity is None:
        raise ValueError("Intensity level (1-10) is required for 'adjust' action")
    
    # Device power consumption mapping
    power_mapping = {
        "ventilation_fan": 150,
        "led_light": 200,
        "heater": 500,
        "humidifier": 80,
        "co2_generator": 120
    }
    
    base_power = power_mapping.get(device_type, 100)
    actual_power = base_power * (intensity or 5) / 10 if action != "off" else 0
    
    return {
        "farm_zone": farm_zone,
        "device_type": device_type,
        "action": action,
        "status": "active" if action in ["on", "adjust"] else "inactive",
        "intensity": intensity or (5 if action == "on" else 0),
        "target_temperature": temperature,
        "power_consumption_watts": int(actual_power),
        "estimated_runtime_hours": 8.0 if action in ["on", "adjust"] else 0.0
    }


def get_crop_status(farm_zone: str, crop_type: str) -> dict[str, Any]:
    """
    Get current status and health information of crops in a specific zone.

    Parameters:
        farm_zone (str): [Required] Farm zone identifier (e.g., 'greenhouse_a', 'greenhouse_b', 'field_c', 'nursery_d')
        crop_type (str): [Required] Type of crop ('tomato', 'cucumber', 'corn', 'lettuce', 'pepper')
    
    Returns:
        dict: {
            "farm_zone": str,
            "crop_type": str,
            "growth_stage": str,
            "health_status": str,
            "days_to_harvest": int,
            "estimated_yield": {"value": float, "unit": str},
            "pest_risk": str,
            "disease_risk": str,
            "recommendations": [str]
        }
    
    Example:
        get_crop_status("greenhouse_a", "tomato")
        # Returns current status of tomato crops in greenhouse A
    
    Raises:
        ValueError: If farm zone or crop type not found
    """
    crop_database = {
        "greenhouse_a": {
            "tomato": {
                "growth_stage": "flowering",
                "health_status": "good",
                "days_to_harvest": 35,
                "estimated_yield": {"value": 4.2, "unit": "kg/m²"},
                "pest_risk": "low",
                "disease_risk": "medium",
                "recommendations": [
                    "Increase ventilation to prevent fungal diseases",
                    "Monitor calcium levels for blossom end rot prevention",
                    "Consider pruning lower leaves"
                ]
            }
        },
        "greenhouse_b": {
            "cucumber": {
                "growth_stage": "fruiting",
                "health_status": "excellent",
                "days_to_harvest": 12,
                "estimated_yield": {"value": 3.8, "unit": "kg/m²"},
                "pest_risk": "low",
                "disease_risk": "low",
                "recommendations": [
                    "Maintain high humidity for optimal growth",
                    "Support heavy fruiting vines",
                    "Regular harvesting to encourage production"
                ]
            }
        }
    }
    
    valid_zones = list(crop_database.keys())
    if farm_zone not in valid_zones:
        raise ValueError(f"Farm zone '{farm_zone}' not found. Available zones: {valid_zones}")
    
    valid_crops = list(crop_database[farm_zone].keys())
    if crop_type not in valid_crops:
        raise ValueError(f"Crop type '{crop_type}' not found in {farm_zone}. Available crops: {valid_crops}")
    
    crop_data = crop_database[farm_zone][crop_type]
    
    return {
        "farm_zone": farm_zone,
        "crop_type": crop_type,
        **crop_data
    }


def generate_farm_report(report_type: str, time_period: str, zones: List[str] = None) -> dict[str, Any]:
    """
    Generate comprehensive farm management reports.

    Parameters:
        report_type (str): [Required] Type of report ('daily_summary', 'resource_usage', 'crop_performance', 'alert_summary')
        time_period (str): [Required] Time period for report ('today', 'yesterday', 'last_7_days', 'last_30_days')
        zones (List[str]): [Optional] Specific zones to include (e.g., ['greenhouse_a', 'greenhouse_b']), all zones if not specified
    
    Returns:
        dict: {
            "report_type": str,
            "time_period": str,
            "zones": List[str],
            "generated_at": str,
            "summary": dict,
            "details": dict,
            "recommendations": List[str],
            "alerts": List[dict]
        }
    
    Example:
        generate_farm_report("daily_summary", "today", ["greenhouse_a", "greenhouse_b"])
        # Generates today's summary report for greenhouse A and B
    
    Raises:
        ValueError: If invalid report type or time period
    """
    valid_report_types = ["daily_summary", "resource_usage", "crop_performance", "alert_summary"]
    valid_time_periods = ["today", "yesterday", "last_7_days", "last_30_days"]
    
    if report_type not in valid_report_types:
        raise ValueError(f"Invalid report type. Available types: {valid_report_types}")
    
    if time_period not in valid_time_periods:
        raise ValueError(f"Invalid time period. Available periods: {valid_time_periods}")
    
    all_zones = ["greenhouse_a", "greenhouse_b", "field_c", "nursery_d"]
    report_zones = zones or all_zones
    
    # Simulated report data
    report_data = {
        "daily_summary": {
            "summary": {
                "total_water_used": 1250,
                "total_power_consumed": 45.6,
                "average_temperature": 26.8,
                "irrigation_cycles": 8,
                "alerts_triggered": 3
            },
            "recommendations": [
                "Reduce irrigation frequency in greenhouse_b due to high humidity",
                "Increase ventilation in greenhouse_a to prevent overheating",
                "Schedule pest inspection for field_c"
            ],
            "alerts": [
                {"zone": "greenhouse_a", "type": "high_temperature", "severity": "medium", "time": "2024-01-15 14:20"},
                {"zone": "greenhouse_b", "type": "high_humidity", "severity": "high", "time": "2024-01-15 15:45"}
            ]
        }
    }
    
    base_data = report_data.get(report_type, report_data["daily_summary"])
    
    return {
        "report_type": report_type,
        "time_period": time_period,
        "zones": report_zones,
        "generated_at": "2024-01-15 16:00",
        "summary": base_data["summary"],
        "details": {"zones_analyzed": len(report_zones), "data_points": 156},
        "recommendations": base_data["recommendations"],
        "alerts": base_data["alerts"]
    }

tools = [
    get_sensor_data,
    control_irrigation_system,
    control_climate_system,
    get_crop_status,
    generate_farm_report
]