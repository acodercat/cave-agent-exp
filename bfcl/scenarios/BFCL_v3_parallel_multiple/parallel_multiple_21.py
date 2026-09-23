from typing import List, Dict, Any, Union, Tuple, Set 
def linear_regression_fit(x:List[float], y:List[float], return_residuals:bool='false') -> str:
	"""
	linear_regression_fit : Fit a linear regression model to data.    
	Parameters:
	x (List[float]): Array of the predictor variable.
	y (List[float]): Array of the dependent variable.
	return_residuals (bool): Flag indicating whether to return the residuals (the difference between the observed and predicted values). Optional.

	Required Parameter = [x,y,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def data_loading(file_path:str, delimiter:str=',') -> str:
	"""
	data_loading : Load data from a csv file into a data structure.    
	Parameters:
	file_path (str): The path to the file to load.
	delimiter (str): The character used to separate values in the file. Optional.

	Required Parameter = [file_path,]

	"""
	return 'Success'

tools = [linear_regression_fit, data_loading]
