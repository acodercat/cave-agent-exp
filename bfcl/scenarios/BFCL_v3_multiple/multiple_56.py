from typing import List, Dict, Any, Union, Tuple, Set 
def volume_traded(company:str, days:int, data_source:str=None) -> str:
	"""
	volume_traded : Calculate the total volume of stocks traded over a certain period of time    
	Parameters:
	company (str): Name of the company to get data for
	days (int): Number of past days to calculate volume traded for
	data_source (str): Source to fetch the financial data. default is 'yahoo finance'

	Required Parameter = [company,days,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def total_revenue(company:str, days:int, data_source:str=None) -> str:
	"""
	total_revenue : Calculate the total revenue of a company over a specific period of time    
	Parameters:
	company (str): Name of the company to get data for
	days (int): Number of past days to calculate total revenue for
	data_source (str): Source to fetch the financial data. default is 'google finance'

	Required Parameter = [company,days,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def avg_closing_price(company:str, days:int, data_source:str=None) -> str:
	"""
	avg_closing_price : Calculate the average closing price of a specific company over a given period of time    
	Parameters:
	company (str): Name of the company to get data for
	days (int): Number of past days to calculate average closing price for
	data_source (str): Source to fetch the stock data. default is 'yahoo finance'

	Required Parameter = [company,days,]

	"""
	return 'Success'

tools = [volume_traded, total_revenue, avg_closing_price]
