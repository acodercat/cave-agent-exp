from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_stock_return(investment_amount:int, annual_growth_rate:float, holding_period:int, dividends:bool=None) -> str:
	"""
	calculate_stock_return : Calculate the projected return of a stock investment given the investment amount, the annual growth rate and holding period in years.    
	Parameters:
	investment_amount (int): The amount of money to invest.
	annual_growth_rate (float): The expected annual growth rate of the stock.
	holding_period (int): The number of years you intend to hold the stock.
	dividends (bool): Optional. True if the calculation should take into account potential dividends. Default is false.

	Required Parameter = [investment_amount,annual_growth_rate,holding_period,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def park_information(park_name:str, information:List[str]) -> str:
	"""
	park_information : Retrieve the basic information such as elevation and area of a national park.    
	Parameters:
	park_name (str): The name of the national park.
	information (List[str]): The type of information you want about the park.

	Required Parameter = [park_name,information,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def legal_case_fetch(case_id:str, details:bool) -> str:
	"""
	legal_case_fetch : Fetch detailed legal case information from database.    
	Parameters:
	case_id (str): The ID of the legal case.
	details (bool): True if need the detail info. Default is false.

	Required Parameter = [case_id,details,]

	"""
	return 'Success'

tools = [calculate_stock_return, park_information, legal_case_fetch]
