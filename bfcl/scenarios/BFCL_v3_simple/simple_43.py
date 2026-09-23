from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_magnetic_field_strength(current:int, distance:int, permeability:float=None) -> str:
	"""
	calculate_magnetic_field_strength : Calculate the magnetic field strength at a point a certain distance away from a long wire carrying a current.    
	Parameters:
	current (int): The current flowing through the wire in Amperes.
	distance (int): The perpendicular distance from the wire to the point where the magnetic field is being calculated.
	permeability (float): The permeability of the medium. Default is 12.57e-7 (Vacuum Permeability).

	Required Parameter = [current,distance,]

	"""
	return 'Success'

tools = [calculate_magnetic_field_strength]
