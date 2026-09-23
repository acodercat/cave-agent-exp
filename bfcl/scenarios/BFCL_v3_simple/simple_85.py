from typing import List, Dict, Any, Union, Tuple, Set 
def geo_distance_calculate(start_location:str, end_location:str, units:str=None) -> str:
	"""
	geo_distance_calculate : Calculate the geographic distance between two given locations.    
	Parameters:
	start_location (str): The starting location for the distance calculation. Specify the location in the format of City, State.
	end_location (str): The destination location for the distance calculation. Specify the location in the format of City, State.
	units (str): Optional. The desired units for the resulting distance ('miles' or 'kilometers'). Defaults to 'miles'.

	Required Parameter = [start_location,end_location,]

	"""
	return 'Success'

tools = [geo_distance_calculate]
