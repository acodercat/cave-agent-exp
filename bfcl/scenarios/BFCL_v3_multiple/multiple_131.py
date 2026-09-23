from typing import List, Dict, Any, Union, Tuple, Set 
def restaurant_find_nearby(location:str, dietary_preference:List[str]=None) -> str:
	"""
	restaurant_find_nearby : Locate nearby restaurants based on specific dietary preferences.    
	Parameters:
	location (str): The city and state, e.g. Los Angeles, CA
	dietary_preference (List[str]): Dietary preference. Default is empty array.

	Required Parameter = [location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def market_performance_get_data(indexes:List[str], days:int, detailed:bool=None) -> str:
	"""
	market_performance_get_data : Retrieve the market performance data for specified indexes over a specified time period.    
	Parameters:
	indexes (List[str]): Array of stock market indexes. Supported indexes are 'S&P 500', 'Dow Jones', 'NASDAQ', 'FTSE 100', 'DAX' etc.
	days (int): Number of days in the past for which the performance data is required.
	detailed (bool): Whether to return detailed performance data. If set to true, returns high, low, opening, and closing prices. If false, returns only closing prices. Default is false.

	Required Parameter = [indexes,days,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sports_match_results(team1:str, team2:str, season:str=None) -> str:
	"""
	sports_match_results : Returns the results of a given match between two teams.    
	Parameters:
	team1 (str): The name of the first team.
	team2 (str): The name of the second team.
	season (str): The season when the match happened. Default is the current season.

	Required Parameter = [team1,team2,]

	"""
	return 'Success'

tools = [restaurant_find_nearby, market_performance_get_data, sports_match_results]
