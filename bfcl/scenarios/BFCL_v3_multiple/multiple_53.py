from typing import List, Dict, Any, Union, Tuple, Set 
def linear_regression(independent_var:List[str], dependent_var:str, forecast_period:int=None) -> str:
	"""
	linear_regression : Applies linear regression to a given set of independent variables to make a prediction.    
	Parameters:
	independent_var (List[str]): The independent variables.
	dependent_var (str): The dependent variable.
	forecast_period (int): The number of years to forecast the prices. Default 1

	Required Parameter = [independent_var,dependent_var,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def random_forest_regression(independent_var:List[str], dependent_var:str, n_estimators:int=None, forecast_period:int=None) -> str:
	"""
	random_forest_regression : Applies Random Forest Regression to a given set of independent variables to make a prediction.    
	Parameters:
	independent_var (List[str]): The independent variables.
	dependent_var (str): The dependent variable.
	n_estimators (int): The number of trees in the forest. Default 1
	forecast_period (int): The number of years to forecast the prices. Default 1

	Required Parameter = [independent_var,dependent_var,]

	"""
	return 'Success'

tools = [linear_regression, random_forest_regression]
