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

tools = [market_performance_get_data]
