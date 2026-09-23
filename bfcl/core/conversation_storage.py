from typing import List

from pathlib import Path
from datetime import datetime
from cave_agent.agent import Message, MessageRole, SystemMessage, UserMessage, AssistantMessage, CodeExecutionMessage, ExecutionResultMessage
import json
import numpy as np
import pandas as pd


class ExtendedEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy and pandas types."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        if isinstance(obj, pd.Series):
            return obj.tolist()
        return super().default(obj)


class ConversationStorage:
    """Conversation storage class - completely independent storage logic"""
    
    def __init__(self, storage_path: str = "./conversations"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_messages(self, messages: List[Message], conversation_id: str) -> str:
        """Save messages to a JSON file."""
        
        data = {
            'conversation_id': conversation_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': [msg.to_dict() for msg in messages],
        }
        
        file_path = self.storage_path / f"{conversation_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, cls=ExtendedEncoder)
        
        return conversation_id
    
    def load_messages(self, conversation_id: str) -> List[Message]:
        """Load messages from a JSON file."""
        file_path = self.storage_path / f"{conversation_id}.json"
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            for msg_data in data['messages']:
                role = msg_data['role']
                content = msg_data['content']
                
                # Rebuild message objects
                if role == MessageRole.SYSTEM:
                    msg = SystemMessage(content)
                elif role == MessageRole.USER:
                    msg = UserMessage(content)
                elif role == MessageRole.ASSISTANT:
                    msg = AssistantMessage(content)
                elif role == MessageRole.CODE_EXECUTION:
                    msg = CodeExecutionMessage(content)
                elif role == MessageRole.EXECUTION_RESULT:
                    msg = ExecutionResultMessage(content)
                else:
                    continue
                    
                messages.append(msg)
            
            return messages
            
        except Exception as e:
            print(f"Failed to load conversation {conversation_id}: {e}")
            return []

storage = ConversationStorage(storage_path="./conversations")