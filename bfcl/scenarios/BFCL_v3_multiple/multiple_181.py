from typing import List, Dict, Any, Union, Tuple, Set 
def building_get_dimensions(building_name:str, unit:str) -> str:
	"""
	building_get_dimensions : Retrieve the dimensions of a specific building based on its name.    
	Parameters:
	building_name (str): The name of the building.
	unit (str): The unit in which you want the dimensions. Default is meter.

	Required Parameter = [building_name,unit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def plot_sine_wave(start_range:float, end_range:float, frequency:float, amplitude:float=None, phase_shift:float=None) -> str:
	"""
	plot_sine_wave : Plot a sine wave for a given frequency in a given range.    
	Parameters:
	start_range (float): Start of the range in radians.
	end_range (float): End of the range in radians.
	frequency (float): Frequency of the sine wave in Hz.
	amplitude (float): Amplitude of the sine wave. Default is 1.
	phase_shift (float): Phase shift of the sine wave in radians. Default is 0.

	Required Parameter = [start_range,end_range,frequency,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def random_forest_train(n_estimators:int, max_depth:int, data:Any) -> str:
	"""
	random_forest_train : Train a Random Forest Model on given data    
	Parameters:
	n_estimators (int): The number of trees in the forest.
	max_depth (int): The maximum depth of the tree.
	data (Any): The training data for the model.

	Required Parameter = [n_estimators,max_depth,data,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def soccer_get_last_match(team_name:str, include_stats:bool=None) -> str:
	"""
	soccer_get_last_match : Retrieve the details of the last match played by a specified soccer club.    
	Parameters:
	team_name (str): The name of the soccer club.
	include_stats (bool): If true, include match statistics like possession, shots on target etc. Default is false.

	Required Parameter = [team_name,]

	"""
	return 'Success'

tools = [building_get_dimensions, plot_sine_wave, random_forest_train, soccer_get_last_match]
