import json
from collections import OrderedDict

__all__ = [
    "json_formatter",
]

def json_formatter(message: str, **kwargs) -> str:
    """
    Format a JSON message.

    Args:
        message: The message to format.
        **kwargs: Additional options to pass to the formatter.
            remove_keys: A list of keys to remove from the message.
            sort: Whether to sort the message.
    Returns:
        The formatted message.
    """
    def clean_dict(message_as_dict: dict) -> dict:
        for k, v in message_as_dict.items():
            if isinstance(v, dict):
                message_as_dict[k] = clean_dict(v)
            elif isinstance(v, list):
                message_as_dict[k] = [clean_dict(i) for i in v]
            elif isinstance(v, str):
                message_as_dict[k] = v.strip().replace("\n", " ")
        if kwargs.get("sort"):
            message_as_dict = OrderedDict(sorted(message_as_dict.items()))
        return message_as_dict
        
    try:
        message_as_dict = json.loads(message)
        if kwargs.get("remove_keys"):
            for key in kwargs["remove_keys"].split(","):
                key = key.strip()
                if key in message_as_dict:
                    message_as_dict.pop(key)
        if kwargs.get("key_value_pairs"):
            for pair in kwargs["key_value_pairs"].split(","):
                k, v = pair.strip().split(":", 1)
                if k in message_as_dict and message_as_dict[k] == v:
                    message_as_dict.pop(k)
        message_as_dict = clean_dict(message_as_dict)
        return json.dumps(message_as_dict, ensure_ascii=False)
    except json.JSONDecodeError:
        return message