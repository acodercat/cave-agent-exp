from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_emission_savings(energy_type:str, usage_duration:int, region:str='West') -> str:
	"""
	calculate_emission_savings : Calculate potential greenhouse gas emissions saved by switching to renewable energy sources.    
	Parameters:
	energy_type (str): Type of the renewable energy source.
	usage_duration (int): Usage duration in months.
	region (str): The region where you use energy.

	Required Parameter = [energy_type,usage_duration,]

	"""
	return 'Success'

tools = [calculate_emission_savings]
