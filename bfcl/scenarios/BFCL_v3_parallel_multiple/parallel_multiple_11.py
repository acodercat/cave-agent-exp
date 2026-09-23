from typing import List, Dict, Any, Union, Tuple, Set 
def physics_magnetic_field(current:float, turnsPerMeter:float, length:float) -> str:
	"""
	physics_magnetic_field : Calculate magnetic field for given current flowing through solenoid.    
	Parameters:
	current (float): Electric current in Amperes.
	turnsPerMeter (float): Number of turns of solenoid per meter.
	length (float): Length of the solenoid in meters.

	Required Parameter = [current,turnsPerMeter,length,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def physics_electric_field(charge:float, distance:float) -> str:
	"""
	physics_electric_field : Calculate electric field for a given point charge and distance.    
	Parameters:
	charge (float): Value of point charge in Coulombs.
	distance (float): Distance from the point charge in meters.

	Required Parameter = [charge,distance,]

	"""
	return 'Success'

tools = [physics_magnetic_field, physics_electric_field]
