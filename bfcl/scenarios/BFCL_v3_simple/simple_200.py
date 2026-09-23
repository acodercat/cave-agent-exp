from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_emissions(distance:int, fuel_type:str, fuel_efficiency:float, efficiency_reduction:int=None) -> str:
	"""
	calculate_emissions : Calculates the annual carbon dioxide emissions produced by a vehicle based on the distance traveled, the fuel type and the fuel efficiency of the vehicle.    
	Parameters:
	distance (int): The distance travelled in miles.
	fuel_type (str): Type of fuel used by the vehicle.
	fuel_efficiency (float): The vehicle's fuel efficiency in miles per gallon.
	efficiency_reduction (int): The percentage decrease in fuel efficiency per year (optional). Default is 0

	Required Parameter = [distance,fuel_type,fuel_efficiency,]

	"""
	return 'Success'

tools = [calculate_emissions]
