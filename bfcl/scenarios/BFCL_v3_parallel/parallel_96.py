from typing import List, Dict, Any, Union, Tuple, Set 
def electromagnetic_force(charge1:int, charge2:int, distance:int, medium_permittivity:float=None) -> str:
	"""
	electromagnetic_force : Calculate the electromagnetic force between two charges placed at a certain distance.    
	Parameters:
	charge1 (int): The magnitude of the first charge in coulombs.
	charge2 (int): The magnitude of the second charge in coulombs.
	distance (int): The distance between the two charges in meters.
	medium_permittivity (float): The relative permittivity of the medium in which the charges are present. Default is 8.854 x 10^-12 F/m (vacuum permittivity).

	Required Parameter = [charge1,charge2,distance,]

	"""
	return 'Success'

tools = [electromagnetic_force]
