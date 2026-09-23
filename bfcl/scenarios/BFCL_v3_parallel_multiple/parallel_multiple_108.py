from typing import List, Dict, Any, Union, Tuple, Set 
def MBTI_analyse(thinking_vs_feeling:str, introverted_vs_extroverted:str, judging_vs_perceiving:str, sensing_vs_intuition:str) -> str:
	"""
	MBTI_analyse : Analyse personality based on the Myers-Briggs Type Indicator (MBTI) which sorts for preferences and generates a 4-letter personality type.    
	Parameters:
	thinking_vs_feeling (str): Preference of user between thinking and feeling.
	introverted_vs_extroverted (str): Preference of user between introverted and extroverted.
	judging_vs_perceiving (str): Preference of user between judging and perceiving.
	sensing_vs_intuition (str): Preference of user between sensing and intuition.

	Required Parameter = [thinking_vs_feeling,introverted_vs_extroverted,judging_vs_perceiving,sensing_vs_intuition,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def five_factor_model_analyse(talkative:bool, nervous:bool, artistic_interests:bool, lazy:bool, forgiving:bool) -> str:
	"""
	five_factor_model_analyse : Analyse personality based on the five-factor model, also known as the Big Five, which measures openness, conscientiousness, extraversion, agreeableness, and neuroticism.    
	Parameters:
	talkative (bool): Indicates if the user is talkative.
	nervous (bool): Indicates if the user gets nervous easily.
	artistic_interests (bool): Indicates if the user has many artistic interests.
	lazy (bool): Indicates if the user tends to be lazy.
	forgiving (bool): Indicates if the user is forgiving.

	Required Parameter = [talkative,nervous,artistic_interests,lazy,forgiving,]

	"""
	return 'Success'

tools = [MBTI_analyse, five_factor_model_analyse]
