import time
import config 

def log(msg: str):
    """Verbose logging with timestamp."""
    if config.VERBOSE:  # Always checks the live value
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[VERBOSE {timestamp}] {msg}")

def print_non_verbose(msg: str):
    """Print only required outputs."""
    print(msg)