from typing import List, Dict, Any, Union, Tuple, Set 
def musicCharts_getMostPlayed(genre:str, region:str, duration:int=None) -> str:
	"""
	musicCharts_getMostPlayed : This function retrieves the current most played song in a particular genre from a specified region    
	Parameters:
	genre (str): Music genre e.g., Rock, Pop, HipHop etc.
	region (str): Region where the song popularity is to be checked
	duration (int): Time duration in hours for which the music played count will be considered. default is 0

	Required Parameter = [genre,region,]

	"""
	return 'Success'

tools = [musicCharts_getMostPlayed]
