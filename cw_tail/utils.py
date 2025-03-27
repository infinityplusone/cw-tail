import argparse
import re
import sys
import time
import yaml
from pathlib import Path
from rich.text import Text

__all__ = [
    "chunk_list",
    "color_funcs",
    "load_config",
    "parse_command_line_arguments",
    "parse_qs",
    "parse_time_string",
    "sleep",
]


def chunk_list(lst, n):
    """
    Split a list into chunks of size n.
    
    Args:
        lst: The list to chunk
        n: The maximum size of each chunk
    
    Returns:
        Generator yielding chunks of the list
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def color_funcs():
    """
    Returns a dictionary of color functions.
    """
    return {
        "blue": lambda text: Text(text, style="blue"),
        "cyan": lambda text: Text(text, style="cyan"),
        "green": lambda text: Text(text, style="green"),
        "dark_green": lambda text: Text(text, style="dark_green"),
        "purple": lambda text: Text(text, style="magenta"),
        "red": lambda text: Text(text, style="red"),
        "white": lambda text: Text(text, style="white"),
        "yellow": lambda text: Text(text, style="yellow"),
        "black": lambda text: Text(text, style="black"),
        "black_on_yellow": lambda text: Text(text, style="black on yellow"),
    }


def load_config(config_name: str = None) -> dict:
    """
    Load configuration from a YAML file.
    If config_name is provided, load that specific configuration,
    otherwise return the default configuration.
    """

    config_file = Path(__file__).parent / "config.yml"
    
    if not config_file.exists():
        print("HUH?")
        # Create default config if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            "default": {
                "region": "us-east-1",
                "since": "1h",
                "colorize": True,
            },
            "example": {
                "log_group": "your-log-group",
                "highlight_tokens": ["error", "warning"],
                "exclude_tokens": ["debug"],
                "formatter": "json_formatter",
                "format_options": {
                    "remove_keys": "logger,request_id",
                    "key_value_pairs": "level:info,level:debug"
                }
            }
        }
        config_file.write_text(yaml.dump(default_config, default_flow_style=False))
        
    try:
        configs = yaml.safe_load(config_file.read_text())
    except Exception as e:
        print(f"Error loading config file: {e}", file=sys.stderr)
        return {}

    if not config_name:
        return configs.get("default", {})
    
    if config_name not in configs:
        print(f"Config '{config_name}' not found in {config_file}", file=sys.stderr)
        return {}
    
    # Merge with default config
    return {**configs.get("default", {}), **configs[config_name]}


def parse_command_line_arguments(args: argparse.Namespace) -> dict:
    """
    Parse command line arguments into a dictionary.
    """
    CONFIG_LIST_KEYS = [
        "filter_pattern",
        "highlight_tokens",
        "exclude_tokens",
        "exclude_streams",
    ]
    CONFIG_DICT_KEYS = [
        "format_options",
    ]
    
    config = {}
    for key in vars(args):
        if getattr(args, key):
            if key in CONFIG_LIST_KEYS:
                config[key] = [k.strip() for k in getattr(args, key).strip().split(",")]
            elif key in CONFIG_DICT_KEYS:
                config[key] = parse_qs(getattr(args, key))
            else:
                config[key] = getattr(args, key)
    return config


def parse_qs(qs: str) -> dict:
    """
    Parse a querystring-like string into a dictionary.
    
    Example:
    >>> parse_qs("a=1&b=2&c=3")
    {'a': '1', 'b': '2', 'c': '3'}
    """
    return dict(opt.strip().split("=", 1) for opt in qs.strip().split("&") if opt and "=" in opt)


def parse_time_string(time_str: str) -> int:
    """
    Converts a string like "1h", "15m", or "10s" to seconds. Defaults to 3600 seconds.
    """
    match = re.match(r"^(\d+)([hms])$", time_str.strip(), re.IGNORECASE)
    if not match:
        return 3600
    value, unit = match.groups()
    value = int(value)
    unit = unit.lower()
    if unit == "h":
        return value * 3600
    elif unit == "m":
        return value * 60
    elif unit == "s":
        return value
    return 3600


def sleep(value: int):
    """
    Use multiple shorter sleeps that can be interrupted
    """    
    sleep_value = max(int(value/0.001), 1)
    for _ in range(sleep_value):
        time.sleep(0.001)