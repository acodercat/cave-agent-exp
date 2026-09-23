from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_emission_savings(energy_type:str, usage_duration:int, region:str=None) -> str:
	"""
	calculate_emission_savings : Calculate potential greenhouse gas emissions saved by switching to renewable energy sources.    
	Parameters:
	energy_type (str): Type of the renewable energy source.
	usage_duration (int): Usage duration in months.
	region (str): The region where you use energy. Default is 'USA'

	Required Parameter = [energy_type,usage_duration,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def timezone_convert(time:str, from_timezone:str, to_timezone:str) -> str:
	"""
	timezone_convert : Convert time from one time zone to another.    
	Parameters:
	time (str): The local time you want to convert, e.g. 3pm
	from_timezone (str): The time zone you want to convert from.
	to_timezone (str): The time zone you want to convert to.

	Required Parameter = [time,from_timezone,to_timezone,]

	"""
	return 'Success'

tools = [calculate_emission_savings, timezone_convert]
