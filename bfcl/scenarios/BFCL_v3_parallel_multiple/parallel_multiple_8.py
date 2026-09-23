from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_distance_traveled(initial_velocity:float, acceleration:float, time:float) -> str:
	"""
	kinematics_distance_traveled : Computes the total distance covered by a moving object given initial velocity, acceleration and time.    
	Parameters:
	initial_velocity (float): The initial velocity of the object in m/s.
	acceleration (float): The acceleration of the object in m/s^2.
	time (float): The time for which the object has been moving in seconds.

	Required Parameter = [initial_velocity,acceleration,time,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_final_velocity(initial_velocity:float, acceleration:float, time:float) -> str:
	"""
	kinematics_final_velocity : Calculates the final velocity of a moving object given initial velocity, acceleration and time.    
	Parameters:
	initial_velocity (float): The initial velocity of the object in m/s.
	acceleration (float): The acceleration of the object in m/s^2.
	time (float): The time for which the object has been moving in seconds.

	Required Parameter = [initial_velocity,acceleration,time,]

	"""
	return 'Success'

tools = [kinematics_distance_traveled, kinematics_final_velocity]
