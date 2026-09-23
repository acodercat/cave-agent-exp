from typing import List, Dict, Any, Union, Tuple, Set 
def get_bureau_statistics(year:int, category:str) -> str:
	"""
	get_bureau_statistics : Retrieve statistical data for a specific year and statistical category    
	Parameters:
	year (int): The year for which to retrieve the statistical data
	category (str): The statistical category (e.g., employment, crime, health)

	Required Parameter = [year,category,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_population(year:int, category:str) -> str:
	"""
	get_population : Retrieve population data for a specific year and population category    
	Parameters:
	year (int): The year for which to retrieve the population data
	category (str): The population category (e.g., total, veterans, women)

	Required Parameter = [year,category,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_demographics(year:int, category:str) -> str:
	"""
	get_demographics : Retrieve demographic data for a specific year and demographic category    
	Parameters:
	year (int): The year for which to retrieve the demographic data
	category (str): The demographic category (e.g., gender, race, age)

	Required Parameter = [year,category,]

	"""
	return 'Success'

tools = [get_bureau_statistics, get_population, get_demographics]
