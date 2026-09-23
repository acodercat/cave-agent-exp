from typing import List, Dict, Any, Union, Tuple, Set 
def european_history_get_events(country:str, century:int, event_type:str=None) -> str:
	"""
	european_history_get_events : Provides a list of major historical events based on the specified country and century.    
	Parameters:
	country (str): Country name.
	century (int): Century as an integer. For example, for the 1700s, input '18'.
	event_type (str): Type of the event such as 'war', 'invention', 'revolution' etc. This field is optional. Default is 'all'

	Required Parameter = [country,century,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def european_history_get_culture(country:str, century:int, aspect:str=None) -> str:
	"""
	european_history_get_culture : Provides information on cultural trends, art movements, philosophical ideas based on the specified country and century.    
	Parameters:
	country (str): Country name.
	century (int): Century as an integer. For example, for the 1700s, input '18'.
	aspect (str): Aspect of culture such as 'literature', 'art', 'philosophy' etc. This field is optional. Default 'any'

	Required Parameter = [country,century,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def european_history_get_monarchs(country:str, century:int) -> str:
	"""
	european_history_get_monarchs : Provides a list of monarchs based on the specified country and century.    
	Parameters:
	country (str): Country name.
	century (int): Century as an integer. For example, for the 1700s, input '18'.

	Required Parameter = [country,century,]

	"""
	return 'Success'

tools = [european_history_get_events, european_history_get_culture, european_history_get_monarchs]
