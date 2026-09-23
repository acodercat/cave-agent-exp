from typing import List, Dict, Any, Union, Tuple, Set 
def physics_calculate_force(mass:int, acceleration:int) -> str:
	"""
	physics_calculate_force : Calculate the force required to move an object of a particular mass at a particular acceleration.    
	Parameters:
	mass (int): The mass of the object in kg.
	acceleration (int): The acceleration of the object in m/s^2.

	Required Parameter = [mass,acceleration,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_calculate_time(velocity:int, distance:int) -> str:
	"""
	kinematics_calculate_time : Calculate time required for an object to travel a particular distance at a particular velocity.    
	Parameters:
	velocity (int): The velocity of the object in m/s.
	distance (int): The distance covered by the object in meters.

	Required Parameter = [velocity,distance,]

	"""
	return 'Success'

tools = [physics_calculate_force, kinematics_calculate_time]
