from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_magnetic_field(current:int, radius:int, permeability:float=None) -> str:
	"""
	calculate_magnetic_field : Calculate the magnetic field produced at the center of a circular loop carrying current.    
	Parameters:
	current (int): The current through the circular loop in Amperes.
	radius (int): The radius of the circular loop in meters.
	permeability (float): The magnetic permeability. Default is 12.57e10 (Vacuum Permeability).

	Required Parameter = [current,radius,]

	"""
	return 'Success'

tools = [calculate_magnetic_field]
