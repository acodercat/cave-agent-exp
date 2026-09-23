"""
Multi-Variable (25) - Stateful Benchmark

Tests: Managing 25 variables of diverse types modified in each turn.
"""

from typing import List
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE - 25 variables with diverse types
# ============================================================================

# Strings (5)
hospital_name = ""
director = ""
address = ""
specialty = ""
license_number = ""

# Integers (5)
beds = 0
doctors = 0
nurses = 0
patients = 0
founded_year = 0

# Floats (5)
budget = 0.0
revenue = 0.0
occupancy_rate = 0.0
satisfaction_score = 0.0
avg_stay_days = 0.0

# Booleans (5)
accredited = False
emergency_services = False
research_facility = False
teaching_hospital = False
nonprofit = False

# Collections (5)
departments = []
equipment = []
services = []
staff_roles = {}
contacts = {}


# ============================================================================
# VALIDATORS
# ============================================================================

# Validation Strategy:
# - Lists (departments, equipment, services): Exact order comparison for appended items.
# - Dicts (staff_roles, contacts): Exact key-value comparison.
# - Floats: Compared with 0.01 tolerance for floating-point precision.


def _compare_values(actual, expected, tolerance=0.01):
    """Recursively compare values with float tolerance."""
    if isinstance(expected, float):
        if not isinstance(actual, (int, float)):
            return False
        return abs(actual - expected) <= tolerance
    elif isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(_compare_values(actual[k], expected[k], tolerance) for k in expected)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(_compare_values(a, e, tolerance) for a, e in zip(actual, expected))
    elif isinstance(expected, tuple):
        # Tuple means "one of these values is acceptable"
        return actual in expected
    else:
        return actual == expected


def _validate_state(runtime: IPythonRuntime, expected: dict) -> list:
    """Helper to validate runtime state against expected values."""
    errors = []
    for key, exp_val in expected.items():
        val = runtime.retrieve(key)
        if not _compare_values(val, exp_val):
            errors.append(f"{key}={val} (expected {exp_val})")
    return errors


def validate_community_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Riverside Community Hospital",
        "director": "Dr. Sarah Chen",
        "address": "100 Health Way, Springfield",
        "specialty": "General Medicine",
        "license_number": "HC-2020-001",
        "beds": 150,
        "doctors": 45,
        "nurses": 120,
        "patients": 80,
        "founded_year": 2005,
        "budget": 25000000.0,
        "revenue": 30000000.0,
        "occupancy_rate": 0.53,
        "satisfaction_score": 4.2,
        "avg_stay_days": 3.5,
        "accredited": True,
        "emergency_services": True,
        "research_facility": False,
        "teaching_hospital": False,
        "nonprofit": True,
        "departments": ["Emergency", "Surgery", "Pediatrics", "Cardiology"],
        "equipment": ["MRI", "CT Scanner", "X-Ray"],
        "services": ["Inpatient", "Outpatient", "Emergency"],
        "staff_roles": {"admin": 30, "support": 50, "technicians": 25},
        "contacts": {"main": "555-1000", "emergency": "555-1911"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Community hospital initialized")

def validate_community_expansion(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Riverside Community Hospital",
        "director": "Dr. Sarah Chen",
        "address": "100 Health Way, Springfield",
        "specialty": "General Medicine",
        "license_number": "HC-2020-001",
        "beds": 250,
        "doctors": 75,
        "nurses": 200,
        "patients": 175,
        "founded_year": 2005,
        "budget": 40000000.0,
        "revenue": 50000000.0,
        "occupancy_rate": 0.70,
        "satisfaction_score": 4.5,
        "avg_stay_days": 3.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": False,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["Emergency", "Surgery", "Pediatrics", "Cardiology", "Oncology", "Neurology"],
        "equipment": ["MRI", "CT Scanner", "X-Ray", "PET Scanner", "Robot Surgery"],
        "services": ["Inpatient", "Outpatient", "Emergency", "Rehab", "Telemedicine"],
        "staff_roles": {"admin": 45, "support": 80, "technicians": 40, "residents": 30},
        "contacts": {"main": "555-1000", "emergency": "555-1911", "appointments": "555-1200"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Expansion complete")

def validate_community_upgrade(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Riverside Regional Medical Center",
        "director": "Dr. Sarah Chen",
        "address": "100 Health Way, Springfield",
        "specialty": "Comprehensive Care",
        "license_number": "HC-2020-001-R",
        "beds": 400,
        "doctors": 120,
        "nurses": 350,
        "patients": 300,
        "founded_year": 2005,
        "budget": 75000000.0,
        "revenue": 90000000.0,
        "occupancy_rate": 0.75,
        "satisfaction_score": 4.7,
        "avg_stay_days": 2.5,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["Emergency", "Surgery", "Pediatrics", "Cardiology", "Oncology", "Neurology", "Research", "Trauma"],
        "equipment": ["MRI", "CT Scanner", "X-Ray", "PET Scanner", "Robot Surgery", "Proton Therapy", "Lab Automation"],
        "services": ["Inpatient", "Outpatient", "Emergency", "Rehab", "Telemedicine", "Clinical Trials", "Trauma Center"],
        "staff_roles": {"admin": 60, "support": 120, "technicians": 70, "residents": 50, "researchers": 25},
        "contacts": {"main": "555-1000", "emergency": "555-1911", "appointments": "555-1200", "research": "555-1300"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Upgrade to medical center complete")


def validate_research_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Metro University Hospital",
        "director": "Dr. James Wright",
        "address": "500 Academic Drive, Metro City",
        "specialty": "Research & Teaching",
        "license_number": "UH-1985-100",
        "beds": 600,
        "doctors": 200,
        "nurses": 500,
        "patients": 450,
        "founded_year": 1985,
        "budget": 150000000.0,
        "revenue": 180000000.0,
        "occupancy_rate": 0.75,
        "satisfaction_score": 4.6,
        "avg_stay_days": 4.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["All Specialties"],
        "equipment": ["State of the Art"],
        "services": ["Full Service"],
        "staff_roles": {"faculty": 150, "residents": 200, "fellows": 75},
        "contacts": {"main": "555-5000", "admissions": "555-5001"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Research hospital initialized")

def validate_research_grant(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Metro University Hospital",
        "director": "Dr. James Wright",
        "address": "500 Academic Drive, Metro City",
        "specialty": "Cancer Research",
        "license_number": "UH-1985-100",
        "beds": 650,
        "doctors": 225,
        "nurses": 550,
        "patients": 500,
        "founded_year": 1985,
        "budget": 200000000.0,
        "revenue": 220000000.0,
        "occupancy_rate": 0.77,
        "satisfaction_score": 4.7,
        "avg_stay_days": 4.5,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["All Specialties", "Oncology Research Center"],
        "equipment": ["State of the Art", "Gene Sequencing Lab", "Immunotherapy Suite"],
        "services": ["Full Service", "Clinical Trials Phase I-III"],
        "staff_roles": {"faculty": 150, "residents": 200, "fellows": 75, "research_staff": 100},
        "contacts": {"main": "555-5000", "admissions": "555-5001", "research": "555-5050"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Research grant program launched")

def validate_research_partnership(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Metro University Hospital & Research Institute",
        "director": "Dr. James Wright",
        "address": "500 Academic Drive, Metro City",
        "specialty": "Precision Medicine",
        "license_number": "UH-1985-100-RI",
        "beds": 750,
        "doctors": 275,
        "nurses": 650,
        "patients": 600,
        "founded_year": 1985,
        "budget": 300000000.0,
        "revenue": 350000000.0,
        "occupancy_rate": 0.80,
        "satisfaction_score": 4.8,
        "avg_stay_days": 4.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["All Specialties", "Oncology Research Center", "Genomics Institute", "AI Medicine Lab"],
        "equipment": ["State of the Art", "Gene Sequencing Lab", "Immunotherapy Suite", "Quantum Computing", "AI Diagnostics"],
        "services": ["Full Service", "Clinical Trials Phase I-III", "Precision Diagnostics", "Global Telemedicine"],
        "staff_roles": {"faculty": 175, "residents": 250, "fellows": 100, "research_staff": 150, "data_scientists": 50},
        "contacts": {"main": "555-5000", "admissions": "555-5001", "research": "555-5050", "partnerships": "555-5100"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Research partnership established")


# Private clinic validators
def validate_clinic_open(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Elite Care Clinic",
        "director": "Dr. Michael Ross",
        "address": "200 Luxury Lane, Beverly Hills",
        "specialty": "Cosmetic Surgery",
        "license_number": "PC-2018-500",
        "beds": 20,
        "doctors": 8,
        "nurses": 25,
        "patients": 15,
        "founded_year": 2018,
        "budget": 5000000.0,
        "revenue": 8000000.0,
        "occupancy_rate": 0.75,
        "satisfaction_score": 4.9,
        "avg_stay_days": 1.0,
        "accredited": True,
        "emergency_services": False,
        "research_facility": False,
        "teaching_hospital": False,
        "nonprofit": False,
        "departments": ["Cosmetic", "Dermatology", "Wellness"],
        "equipment": ["Laser Systems", "Imaging Suite"],
        "services": ["Outpatient", "Day Surgery", "Consultations"],
        "staff_roles": {"admin": 10, "aestheticians": 15, "concierge": 5},
        "contacts": {"appointments": "555-8000", "vip": "555-8001"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Private clinic opened")

def validate_clinic_expand(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Elite Care Medical Center",
        "director": "Dr. Michael Ross",
        "address": "200 Luxury Lane, Beverly Hills",
        "specialty": "Comprehensive Aesthetics",
        "license_number": "PC-2018-500-M",
        "beds": 50,
        "doctors": 25,
        "nurses": 60,
        "patients": 40,
        "founded_year": 2018,
        "budget": 15000000.0,
        "revenue": 25000000.0,
        "occupancy_rate": 0.80,
        "satisfaction_score": 4.9,
        "avg_stay_days": 1.5,
        "accredited": True,
        "emergency_services": False,
        "research_facility": True,
        "teaching_hospital": False,
        "nonprofit": False,
        "departments": ["Cosmetic", "Dermatology", "Wellness", "Anti-Aging", "Regenerative"],
        "equipment": ["Laser Systems", "Imaging Suite", "Stem Cell Lab", "Cryo Therapy"],
        "services": ["Outpatient", "Day Surgery", "Consultations", "Med Spa", "Research Trials"],
        "staff_roles": {"admin": 20, "aestheticians": 30, "concierge": 10, "researchers": 15},
        "contacts": {"appointments": "555-8000", "vip": "555-8001", "research": "555-8050"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Clinic expanded")

def validate_clinic_franchise(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Elite Care International",
        "director": "Dr. Michael Ross",
        "address": "200 Luxury Lane, Beverly Hills",
        "specialty": "Luxury Healthcare",
        "license_number": "PC-2018-500-INT",
        "beds": 100,
        "doctors": 50,
        "nurses": 120,
        "patients": 80,
        "founded_year": 2018,
        "budget": 50000000.0,
        "revenue": 80000000.0,
        "occupancy_rate": 0.80,
        "satisfaction_score": 5.0,
        "avg_stay_days": 2.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": False,
        "departments": ["Cosmetic", "Dermatology", "Wellness", "Anti-Aging", "Regenerative", "Executive Health", "Global VIP"],
        "equipment": ["Laser Systems", "Imaging Suite", "Stem Cell Lab", "Cryo Therapy", "Robotic Surgery", "AI Diagnostics"],
        "services": ["Outpatient", "Day Surgery", "Consultations", "Med Spa", "Research Trials", "Concierge Medicine", "Medical Tourism"],
        "staff_roles": {"admin": 40, "aestheticians": 50, "concierge": 25, "researchers": 30, "international": 20},
        "contacts": {"appointments": "555-8000", "vip": "555-8001", "research": "555-8050", "global": "555-8100"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "International franchise established")


# Children's hospital validators
def validate_childrens_open(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Sunshine Children's Hospital",
        "director": "Dr. Lisa Park",
        "address": "300 Rainbow Road, Sunnyville",
        "specialty": "Pediatrics",
        "license_number": "CH-2010-200",
        "beds": 100,
        "doctors": 40,
        "nurses": 100,
        "patients": 60,
        "founded_year": 2010,
        "budget": 30000000.0,
        "revenue": 35000000.0,
        "occupancy_rate": 0.60,
        "satisfaction_score": 4.8,
        "avg_stay_days": 2.5,
        "accredited": True,
        "emergency_services": True,
        "research_facility": False,
        "teaching_hospital": False,
        "nonprofit": True,
        "departments": ["General Pediatrics", "NICU", "Pediatric Surgery"],
        "equipment": ["Child-sized MRI", "Pediatric ICU", "Play Therapy Room"],
        "services": ["Inpatient", "Outpatient", "Emergency", "Family Support"],
        "staff_roles": {"admin": 20, "child_life": 15, "social_workers": 10},
        "contacts": {"main": "555-KIDS", "emergency": "555-5432"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Children's hospital opened")

def validate_childrens_specialize(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Sunshine Children's Hospital",
        "director": "Dr. Lisa Park",
        "address": "300 Rainbow Road, Sunnyville",
        "specialty": "Pediatric Oncology",
        "license_number": "CH-2010-200",
        "beds": 150,
        "doctors": 60,
        "nurses": 150,
        "patients": 100,
        "founded_year": 2010,
        "budget": 50000000.0,
        "revenue": 55000000.0,
        "occupancy_rate": 0.67,
        "satisfaction_score": 4.9,
        "avg_stay_days": 5.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": False,
        "nonprofit": True,
        "departments": ["General Pediatrics", "NICU", "Pediatric Surgery", "Oncology", "Hematology"],
        "equipment": ["Child-sized MRI", "Pediatric ICU", "Play Therapy Room", "Proton Beam", "Chemo Suite"],
        "services": ["Inpatient", "Outpatient", "Emergency", "Family Support", "Cancer Treatment", "Clinical Trials"],
        "staff_roles": {"admin": 30, "child_life": 25, "social_workers": 20, "researchers": 15},
        "contacts": {"main": "555-KIDS", "emergency": "555-5432", "oncology": "555-5433"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Specialty program launched")

def validate_childrens_flagship(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Sunshine National Children's Medical Center",
        "director": "Dr. Lisa Park",
        "address": "300 Rainbow Road, Sunnyville",
        "specialty": "Comprehensive Pediatrics",
        "license_number": "CH-2010-200-NAT",
        "beds": 300,
        "doctors": 120,
        "nurses": 300,
        "patients": 225,
        "founded_year": 2010,
        "budget": 120000000.0,
        "revenue": 140000000.0,
        "occupancy_rate": 0.75,
        "satisfaction_score": 5.0,
        "avg_stay_days": 4.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["General Pediatrics", "NICU", "Pediatric Surgery", "Oncology", "Hematology", "Cardiology", "Neurology", "Genetics"],
        "equipment": ["Child-sized MRI", "Pediatric ICU", "Play Therapy Room", "Proton Beam", "Chemo Suite", "Heart Center", "Gene Lab"],
        "services": ["Inpatient", "Outpatient", "Emergency", "Family Support", "Cancer Treatment", "Clinical Trials", "Transplant", "Rehab"],
        "staff_roles": {"admin": 50, "child_life": 40, "social_workers": 30, "researchers": 35, "educators": 25},
        "contacts": {"main": "555-KIDS", "emergency": "555-5432", "oncology": "555-5433", "research": "555-5434"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Flagship status achieved")


# Veterans hospital validators
def validate_veterans_establish(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Veterans Memorial Medical Center",
        "director": "Dr. Robert Miller",
        "address": "400 Honor Drive, Capital City",
        "specialty": "Veteran Care",
        "license_number": "VA-2000-001",
        "beds": 200,
        "doctors": 60,
        "nurses": 180,
        "patients": 150,
        "founded_year": 2000,
        "budget": 60000000.0,
        "revenue": 60000000.0,
        "occupancy_rate": 0.75,
        "satisfaction_score": 4.3,
        "avg_stay_days": 5.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": False,
        "teaching_hospital": False,
        "nonprofit": True,
        "departments": ["Primary Care", "Mental Health", "Rehabilitation"],
        "equipment": ["Standard Imaging", "Prosthetics Lab"],
        "services": ["Inpatient", "Outpatient", "Emergency", "PTSD Treatment"],
        "staff_roles": {"admin": 40, "veterans_liaisons": 20, "therapists": 30},
        "contacts": {"main": "555-VETS", "crisis": "555-0000"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Veterans hospital established")

def validate_veterans_modernize(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "Veterans Memorial Medical Center",
        "director": "Dr. Robert Miller",
        "address": "400 Honor Drive, Capital City",
        "specialty": "Comprehensive Veteran Care",
        "license_number": "VA-2000-001",
        "beds": 350,
        "doctors": 100,
        "nurses": 280,
        "patients": 280,
        "founded_year": 2000,
        "budget": 100000000.0,
        "revenue": 100000000.0,
        "occupancy_rate": 0.80,
        "satisfaction_score": 4.6,
        "avg_stay_days": 4.0,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": False,
        "nonprofit": True,
        "departments": ["Primary Care", "Mental Health", "Rehabilitation", "Traumatic Brain Injury", "Polytrauma"],
        "equipment": ["Standard Imaging", "Prosthetics Lab", "Advanced MRI", "VR Therapy", "Robotic Rehab"],
        "services": ["Inpatient", "Outpatient", "Emergency", "PTSD Treatment", "Telehealth", "Home Care"],
        "staff_roles": {"admin": 60, "veterans_liaisons": 40, "therapists": 50, "researchers": 25},
        "contacts": {"main": "555-VETS", "crisis": "555-0000", "telehealth": "555-0001"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Modernization complete")

def validate_veterans_flagship(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "hospital_name": "National Veterans Health System Flagship",
        "director": "Dr. Robert Miller",
        "address": "400 Honor Drive, Capital City",
        "specialty": "National Veteran Excellence",
        "license_number": "VA-2000-001-FLAG",
        "beds": 500,
        "doctors": 180,
        "nurses": 450,
        "patients": 400,
        "founded_year": 2000,
        "budget": 200000000.0,
        "revenue": 200000000.0,
        "occupancy_rate": 0.80,
        "satisfaction_score": 4.9,
        "avg_stay_days": 3.5,
        "accredited": True,
        "emergency_services": True,
        "research_facility": True,
        "teaching_hospital": True,
        "nonprofit": True,
        "departments": ["Primary Care", "Mental Health", "Rehabilitation", "Traumatic Brain Injury", "Polytrauma", "Burn Center", "Spinal Cord", "Research"],
        "equipment": ["Standard Imaging", "Prosthetics Lab", "Advanced MRI", "VR Therapy", "Robotic Rehab", "3D Printing", "Exoskeletons"],
        "services": ["Inpatient", "Outpatient", "Emergency", "PTSD Treatment", "Telehealth", "Home Care", "National Training", "Research Hub"],
        "staff_roles": {"admin": 80, "veterans_liaisons": 60, "therapists": 80, "researchers": 50, "educators": 30},
        "contacts": {"main": "555-VETS", "crisis": "555-0000", "telehealth": "555-0001", "research": "555-0002"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Flagship status achieved")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    Variable("hospital_name", hospital_name, "Hospital name (str, initial: '')."),
    Variable("director", director, "Medical director (str, initial: '')."),
    Variable("address", address, "Full address (str, initial: '')."),
    Variable("specialty", specialty, "Primary specialty (str, initial: ''). Use '&' for compound names (e.g., 'Research & Teaching')."),
    Variable("license_number", license_number, "License number (str, initial: '')."),
    Variable("beds", beds, "Number of beds (int, initial: 0)."),
    Variable("doctors", doctors, "Number of doctors (int, initial: 0)."),
    Variable("nurses", nurses, "Number of nurses (int, initial: 0)."),
    Variable("patients", patients, "Current patients (int, initial: 0)."),
    Variable("founded_year", founded_year, "Year founded (int, initial: 0)."),
    Variable("budget", budget, "Annual budget (float, initial: 0.0)."),
    Variable("revenue", revenue, "Annual revenue (float, initial: 0.0)."),
    Variable("occupancy_rate", occupancy_rate, "Bed occupancy 0-1 (float, initial: 0.0)."),
    Variable("satisfaction_score", satisfaction_score, "Patient satisfaction 1-5 (float, initial: 0.0)."),
    Variable("avg_stay_days", avg_stay_days, "Average stay in days (float, initial: 0.0)."),
    Variable("accredited", accredited, "Accreditation status (bool, initial: False)."),
    Variable("emergency_services", emergency_services, "Has ER (bool, initial: False)."),
    Variable("research_facility", research_facility, "Research facility (bool, initial: False)."),
    Variable("teaching_hospital", teaching_hospital, "Teaching hospital (bool, initial: False)."),
    Variable("nonprofit", nonprofit, "Nonprofit status (bool, initial: False)."),
    Variable("departments", departments, "Department names (list[str], initial: [])."),
    Variable("equipment", equipment, "Major equipment (list[str], initial: []). Use exact names as given (e.g., 'Robot Surgery' not 'Robotic Surgery')."),
    Variable("services", services, "Services offered (list[str], initial: [])."),
    Variable("staff_roles", staff_roles, "Staff by role (dict, initial: {}). Key-value store for role counts like admin, support, technicians, residents, etc. Use staff_roles['role'] = count to add/update entries."),
    Variable("contacts", contacts, "Contact numbers (dict, initial: {}). Key-value store for phone numbers like main, emergency, appointments, etc. Use contacts['type'] = number to add/update entries."),
]

validators = {
    "validate_community_init": validate_community_init,
    "validate_community_expansion": validate_community_expansion,
    "validate_community_upgrade": validate_community_upgrade,
    "validate_research_init": validate_research_init,
    "validate_research_grant": validate_research_grant,
    "validate_research_partnership": validate_research_partnership,
    "validate_clinic_open": validate_clinic_open,
    "validate_clinic_expand": validate_clinic_expand,
    "validate_clinic_franchise": validate_clinic_franchise,
    "validate_childrens_open": validate_childrens_open,
    "validate_childrens_specialize": validate_childrens_specialize,
    "validate_childrens_flagship": validate_childrens_flagship,
    "validate_veterans_establish": validate_veterans_establish,
    "validate_veterans_modernize": validate_veterans_modernize,
    "validate_veterans_flagship": validate_veterans_flagship,
}
