from typing import List, Dict, Any, Union, Tuple, Set 
def send_email(to:str, subject:str, body:str, cc:str=None, bcc:str=None) -> str:
	"""
	send_email : Send an email to the specified email address.    
	Parameters:
	to (str): The email address to send to.
	subject (str): The subject of the email.
	body (str): The body content of the email.
	cc (str): The email address to carbon copy. default is ''.
	bcc (str): The email address to blind carbon copy. the value is set to '' for default.

	Required Parameter = [to,subject,body,]

	"""
	return 'Success'

tools = [send_email]
