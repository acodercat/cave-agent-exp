from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_voltage_difference(electric_field:float, distance:float, charge:float=0) -> str:
	"""
	calculate_voltage_difference : Calculate the voltage difference between two points in an electric field.    
	Parameters:
	electric_field (float): The electric field in newtons per coulomb.
	distance (float): The distance between the two points in the direction of the field in meters.
	charge (float): The charge of the test particle, typically an electron, in coulombs. Default to 0

	Required Parameter = [electric_field,distance,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_magnetic_field(current:float, distance:float, permeability:float=None) -> str:
	"""
	calculate_magnetic_field : Calculate the magnetic field produced by a current-carrying wire.    
	Parameters:
	current (float): The current in the wire in amperes.
	distance (float): The perpendicular distance from the wire in meters.
	permeability (float): The permeability of free space, a constant value. Default 0.1

	Required Parameter = [current,distance,]

	"""
	return 'Success'

tools = [calculate_voltage_difference, calculate_magnetic_field]
