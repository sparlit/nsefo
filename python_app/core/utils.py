import threading
import time
import logging
from typing import Any, Optional

logger = logging.getLogger("Utils")

def timed_input_with_default(prompt: str, suggestion: str, timeout: int = 10) -> str:
    """
    Asks the user for input with a timeout.
    If no input is received, returns the suggestion.
    """
    result = [None]
    event = threading.Event()

    def get_input():
        try:
            # We use a wrapper to handle cases where input() is not available
            val = input(f"{prompt} (Default: {suggestion}) [Timeout {timeout}s]: ")
            result[0] = val
        except EOFError:
            logger.debug("Input stream ended (EOF).")
        except Exception as e:
            logger.debug(f"Input error: {e}")
        finally:
            event.set()

    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()

    # Wait for the event OR the timeout
    signaled = event.wait(timeout)

    if result[0] is None:
        if not signaled:
            print(f"\n[Timeout reached] Using recommended default: {suggestion}")
        else:
            print(f"\n[Manual input skipped] Using recommended default: {suggestion}")
        return suggestion
    return result[0]

def auto_confirm_trade(trade_details: Any, recommend_action: str = "YES") -> bool:
    print(f"\n--- TRADE CONFIRMATION REQUIRED ---")
    print(f"Details: {trade_details}")
    choice = timed_input_with_default("Confirm trade execution?", recommend_action, 10)
    return choice.upper() in ["YES", "Y"]
