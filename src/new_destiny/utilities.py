from colorama import init, Fore, Style
from httpx import Headers
import json

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Define the COLOR_MAP for color handling
COLOR_MAP = {
    "black": Fore.BLACK,
    "red": Fore.RED,
    "light red": Fore.LIGHTRED_EX,
    "green": Fore.GREEN,
    "light green": Fore.LIGHTGREEN_EX,
    "yellow": Fore.YELLOW,
    "light yellow": Fore.LIGHTYELLOW_EX,
    "blue": Fore.BLUE,
    "magenta": Fore.MAGENTA,
    "cyan": Fore.CYAN,
    "white": Fore.WHITE,
}

def custom_print(obj, color="cyan"):
    """
    Pretty-print objects with colors and line breaks.
    Each dictionary key-value pair gets its own line.
    """
    color_prefix = COLOR_MAP.get(color.lower(), "") if color else ""

    # Convert httpx.Headers (which is immutable) to a dictionary
    if isinstance(obj, Headers):
        obj = dict(obj)

    # Handle the case where the object is a dictionary (ex. parsed JSON)
    if isinstance(obj, dict):
        print(
            f"{color_prefix}{json.dumps(obj, indent=4, sort_keys=True)}{Style.RESET_ALL}"
        )

    # Handle the case where the object is a string (or can be converted to a string)
    elif isinstance(obj, str):
        print(f"{color_prefix}{obj}{Style.RESET_ALL}")

    # Handle other objects by using repr()
    else:
        print(f"{color_prefix}{repr(obj)}{Style.RESET_ALL}")