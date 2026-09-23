from typing import List, Dict, Any, Union, Tuple, Set 
def calcVolume_cuboid(height:float, width:float, depth:float) -> str:
	"""
	calcVolume_cuboid : Calculates the volume of a cuboid.    
	Parameters:
	height (float): The height of the cuboid.
	width (float): The width of the cuboid.
	depth (float): The depth of the cuboid.

	Required Parameter = [height,width,depth,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calcVolume_sphere(radius:float) -> str:
	"""
	calcVolume_sphere : Calculates the volume of a sphere.    
	Parameters:
	radius (float): The radius of the sphere.

	Required Parameter = [radius,]

	"""
	return 'Success'

tools = [calcVolume_cuboid, calcVolume_sphere]
