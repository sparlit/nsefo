import threading
import time
import logging
from typing import Any, Optional

logger = logging.getLogger("Utils")

def timed_input_with_default(prompt: str, suggestion: str, timeout: int = 10) -> str:
    """
    Asks the user for input with a timeout.
    If no input is received, returns the suggestion.

    Uses select (Unix) or msvcrt (Windows) to avoid blocking indefinitely
    on a closed/stdin pipe in the daemon thread.
    """
    result = [None]
    event = threading.Event()

    def get_input():
        try:
            import sys
            import select as _select

            def _has_input() -> bool:
                """Return True if stdin has data ready within the timeout window."""
                try:
                    if sys.platform == "win32":
                        import msvcrt
                        return msvcrt.kbhit()
                    else:
                        return _select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])
                except Exception:
                    return False

            # Poll until timeout or data available
            start = time.monotonic()
            while (time.monotonic() - start) < timeout:
                if _has_input():
                    val = sys.stdin.readline()
                    result[0] = val.rstrip("\r\n") if val else suggestion
                    break
                time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Input error: {e}")
        finally:
            event.set()

    thread = threading.Thread(target=get_input, daemon=True)
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
