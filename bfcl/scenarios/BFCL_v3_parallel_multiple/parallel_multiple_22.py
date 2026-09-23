from typing import List, Dict, Any, Union, Tuple, Set 
def financial_ratios_interest_coverage(company_name:str, years:int) -> str:
	"""
	financial_ratios_interest_coverage : Calculate a company's interest coverage ratio given the company name and duration    
	Parameters:
	company_name (str): The name of the company.
	years (int): Number of past years to calculate the ratio.

	Required Parameter = [company_name,years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sales_growth_calculate(company:str, years:int) -> str:
	"""
	sales_growth_calculate : Calculate a company's sales growth rate given the company name and duration    
	Parameters:
	company (str): The company that you want to get the sales growth rate for.
	years (int): Number of past years for which to calculate the sales growth rate.

	Required Parameter = [company,years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def weather_forecast(location:str, days:int) -> str:
	"""
	weather_forecast : Retrieve a weather forecast for a specific location and time frame.    
	Parameters:
	location (str): The city that you want to get the weather for.
	days (int): Number of days for the forecast.

	Required Parameter = [location,days,]

	"""
	return 'Success'

tools = [financial_ratios_interest_coverage, sales_growth_calculate, weather_forecast]
