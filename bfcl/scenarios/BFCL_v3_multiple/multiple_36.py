from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_calculate_acceleration(initial_speed:float, final_speed:float, time:float, distance:float=0) -> str:
	"""
	kinematics_calculate_acceleration : Calculates the acceleration of an object under given conditions.    
	Parameters:
	initial_speed (float): The initial speed of the object.
	final_speed (float): The final speed of the object.
	time (float): The time in seconds it took the object to reach the final speed.
	distance (float): The distance in meters the object has traveled.

	Required Parameter = [initial_speed,final_speed,time,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_calculate_speed_from_rest(distance:int, time:int, initial_speed:int=0) -> str:
	"""
	kinematics_calculate_speed_from_rest : Calculates the speed of an object that starts from rest under a constant acceleration over a specified distance.    
	Parameters:
	distance (int): The distance in meters the object has traveled.
	time (int): The time in seconds it took the object to travel.
	initial_speed (int): The initial speed of the object.

	Required Parameter = [distance,time,]

	"""
	return 'Success'

tools = [kinematics_calculate_acceleration, kinematics_calculate_speed_from_rest]
