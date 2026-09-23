from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_electrostatic_potential(charge1:float, charge2:float, distance:float, constant:float=None) -> str:
	"""
	calculate_electrostatic_potential : Calculate the electrostatic potential between two charged bodies using the principle of Coulomb's Law.    
	Parameters:
	charge1 (float): The quantity of charge on the first body.
	charge2 (float): The quantity of charge on the second body.
	distance (float): The distance between the two bodies.
	constant (float): The value of the electrostatic constant. Default is 8.99e9.

	Required Parameter = [charge1,charge2,distance,]

	"""
	return 'Success'

tools = [calculate_electrostatic_potential]
