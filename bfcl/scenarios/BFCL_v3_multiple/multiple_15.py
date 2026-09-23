from typing import List, Dict, Any, Union, Tuple, Set 
def solarFarm_potential(coordinates:List[float], panelArea:int, month:str=None) -> str:
	"""
	solarFarm_potential : Estimate the energy output of a solar farm given its location and panel area for a particular month.    
	Parameters:
	coordinates (List[float]): The geographic coordinates of the location of the solar farm.
	panelArea (int): The total solar panel area in square feet at the location.
	month (str): The month for which to calculate the potential energy output. Default to January

	Required Parameter = [coordinates,panelArea,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def windFarm_potential(coordinates:List[float], turbineCount:int, month:str=None) -> str:
	"""
	windFarm_potential : Estimate the energy output of a wind farm given its location and turbine count for a particular month.    
	Parameters:
	coordinates (List[float]): The geographic coordinates of the location of the wind farm.
	turbineCount (int): The total number of wind turbines at the location.
	month (str): The month for which to calculate the potential energy output. Default to January

	Required Parameter = [coordinates,turbineCount,]

	"""
	return 'Success'

tools = [solarFarm_potential, windFarm_potential]
