import threading
import time
from typing import Any, Callable

def timed_input_with_default(prompt: str, suggestion: str, timeout: int = 10) -> str:
    """
    Asks the user for input with a timeout.
    If no input is received, returns the suggestion.
    """
    result = [None]
    event = threading.Event()

    def get_input():
        try:
            result[0] = input(f"{prompt} (Default: {suggestion}) [Timeout {timeout}s]: ")
        except EOFError:
            pass
        finally:
            event.set()

    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()

    # Wait for the event OR the timeout
    event.wait(timeout)

    if result[0] is None:
        if not event.is_set():
            print(f"\n[Timeout reached] Using recommended default: {suggestion}")
        else:
            print(f"\n[No terminal input available] Using recommended default: {suggestion}")
        return suggestion
    return result[0]

def auto_confirm_trade(trade_details: Any, recommend_action: str = "YES") -> bool:
    print(f"\n--- TRADE CONFIRMATION REQUIRED ---")
    print(f"Details: {trade_details}")
    choice = timed_input_with_default("Confirm trade execution?", recommend_action, 10)
    return choice.upper() in ["YES", "Y"]
