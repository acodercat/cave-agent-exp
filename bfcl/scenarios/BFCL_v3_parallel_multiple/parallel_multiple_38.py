from typing import List, Dict, Any, Union, Tuple, Set 
def us_history_gdp(year:int) -> str:
	"""
	us_history_gdp : Retrieves the Gross Domestic Product of the USA for a specific year.    
	Parameters:
	year (int): The year for which to retrieve GDP data.

	Required Parameter = [year,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def us_history_life_expectancy(year:int) -> str:
	"""
	us_history_life_expectancy : Retrieves the average life expectancy of the USA for a specific year.    
	Parameters:
	year (int): The year for which to retrieve life expectancy.

	Required Parameter = [year,]

	"""
	return 'Success'

tools = [us_history_gdp, us_history_life_expectancy]
