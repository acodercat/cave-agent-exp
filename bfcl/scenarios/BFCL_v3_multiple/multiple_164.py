from typing import List, Dict, Any, Union, Tuple, Set 
def grocery_store_find_nearby(location:str, categories:List[str]=None) -> str:
	"""
	grocery_store_find_nearby : Locate nearby grocery stores based on specific criteria like organic fruits and vegetables.    
	Parameters:
	location (str): The city and state, e.g. Houston, TX
	categories (List[str]): Categories of items to be found in the grocery store. Default is empty array

	Required Parameter = [location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_NPV(cash_flows:List[float], discount_rate:float, initial_investment:float=None) -> str:
	"""
	calculate_NPV : Calculate the NPV (Net Present Value) of an investment, considering a series of future cash flows, discount rate, and an initial investment.    
	Parameters:
	cash_flows (List[float]): Series of future cash flows.
	discount_rate (float): The discount rate to use.
	initial_investment (float): The initial investment. Default is 0 if not specified.

	Required Parameter = [cash_flows,discount_rate,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_stock_price(company_name:str, date:str, exchange:str=None) -> str:
	"""
	get_stock_price : Get the closing stock price for a specific company on a specified date.    
	Parameters:
	company_name (str): Name of the company.
	date (str): Date of when to get the stock price. Format: yyyy-mm-dd.
	exchange (str): Name of the stock exchange market where the company's stock is listed. Default is 'NASDAQ'

	Required Parameter = [company_name,date,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def instrument_price_get(brand:str, model:str, finish:str) -> str:
	"""
	instrument_price_get : Retrieve the current retail price of a specific musical instrument.    
	Parameters:
	brand (str): The brand of the instrument.
	model (str): The specific model of the instrument.
	finish (str): The color or type of finish on the instrument.

	Required Parameter = [brand,model,finish,]

	"""
	return 'Success'

tools = [grocery_store_find_nearby, calculate_NPV, get_stock_price, instrument_price_get]
