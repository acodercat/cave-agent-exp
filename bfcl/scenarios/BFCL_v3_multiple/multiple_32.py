from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_calculate_cone_volume(radius:int, height:int, round_off:int=None) -> str:
	"""
	geometry_calculate_cone_volume : Calculate the volume of a cone given the radius and height.    
	Parameters:
	radius (int): Radius of the cone base.
	height (int): Height of the cone.
	round_off (int): Number of decimal places to round off the answer. Default 0

	Required Parameter = [radius,height,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def physics_calculate_cone_mass(radius:float, height:float, density:float) -> str:
	"""
	physics_calculate_cone_mass : Calculate the mass of a cone given the radius, height, and density.    
	Parameters:
	radius (float): Radius of the cone base.
	height (float): Height of the cone.
	density (float): Density of the material the cone is made of.

	Required Parameter = [radius,height,density,]

	"""
	return 'Success'

tools = [geometry_calculate_cone_volume, physics_calculate_cone_mass]
