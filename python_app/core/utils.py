import threading
import time
import logging
from typing import Any, Optional

logger = logging.getLogger("Utils")

# Sentinel value to distinguish between actual input and timeout/error conditions
_NO_INPUT_RECEIVED = object()

def timed_input_with_default(prompt: str, suggestion: str, timeout: int = 10) -> str:
    """
    Asks the user for input with a timeout.
    If no input is received, returns the suggestion.

    Uses select (Unix) or msvcrt (Windows) to avoid blocking indefinitely
    on a closed/stdin pipe in the daemon thread.
    
    SECURITY WARNING: This function has FAIL-OPEN behavior and must NEVER be used for
    security-critical operations like trade authorization. When stdin is unavailable,
    closed, or times out, this function returns the caller-provided suggestion, which
    could result in unintended authorization of critical operations.
    
    For security-critical operations (trade confirmation, fund transfers, etc.),
    use timed_input_explicit() instead, which returns None on timeout/unavailability
    and implements fail-safe (fail-closed) behavior.
    
    DEPRECATED: This function is retained only for non-critical UI prompts.
    Do not use for any authorization or confirmation workflows.
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

def timed_input_explicit(prompt: str, timeout: int = 10) -> Optional[str]:
    """
    Asks the user for input with a timeout.
    Returns the actual user input string, or None if no input was received.
    
    This function is designed for security-critical operations where the absence
    of input must be distinguishable from a default value. Unlike timed_input_with_default,
    this function returns None on timeout, stdin unavailability, or any error condition.
    
    Args:
        prompt: The prompt message to display to the user
        timeout: Maximum seconds to wait for input
        
    Returns:
        str: The actual user input (stripped of whitespace) if received
        None: If timeout occurred, stdin is unavailable, or any error occurred
    """
    result = [_NO_INPUT_RECEIVED]
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
                    if val:
                        result[0] = val.rstrip("\r\n")
                    break
                time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Input error during trade confirmation: {e}")
        finally:
            event.set()

    print(prompt, end=" ", flush=True)
    thread = threading.Thread(target=get_input, daemon=True)
    thread.start()

    # Wait for the event OR the timeout
    signaled = event.wait(timeout)

    if result[0] is _NO_INPUT_RECEIVED:
        if not signaled:
            print(f"\n[Timeout reached] No input received within {timeout} seconds.")
        else:
            print(f"\n[Input unavailable] stdin is closed, redirected, or unreadable.")
        return None
    
    return result[0]

def auto_confirm_trade(trade_details: Any) -> bool:
    """
    Prompts for explicit trade confirmation with a timeout.
    
    SECURITY: This function implements fail-safe (fail-closed) authorization for live trade execution.
    Returns True ONLY if the user explicitly enters "YES" or "Y" within the timeout period.
    
    Any of the following conditions result in rejection (False):
    - Timeout without input
    - stdin unavailable, closed, or redirected
    - Empty input
    - Any input other than "YES" or "Y" (case-insensitive)
    - Any error during input collection
    
    This ensures that unattended processes, processes with closed stdin, or processes
    running in environments where stdin is unavailable cannot accidentally authorize
    live trades.
    
    The function will NEVER use a default value for authorization - explicit user input
    of "YES" or "Y" is the ONLY way to authorize a trade.
    
    Args:
        trade_details: Trade information to display to the user
        
    Returns:
        bool: True only if user explicitly entered "YES" or "Y", False otherwise
    """
    print(f"\n{'='*60}")
    print(f"TRADE CONFIRMATION REQUIRED")
    print(f"{'='*60}")
    print(f"Details: {trade_details}")
    print(f"\nType 'YES' or 'Y' to confirm, or wait {10} seconds to reject.")
    
    choice = timed_input_explicit("Confirm trade execution? [YES/Y to confirm]:", timeout=10)
    
    if choice is None:
        print("[REJECTED] Trade execution cancelled: no confirmation received.")
        logger.warning(f"Trade confirmation failed: no input received. Trade details: {trade_details}")
        return False
    
    if choice.upper() in ["YES", "Y"]:
        print("[CONFIRMED] Trade execution authorized.")
        logger.info(f"Trade confirmation received: {choice}")
        return True
    
    print(f"[REJECTED] Trade execution cancelled: invalid response '{choice}'.")
    logger.warning(f"Trade confirmation failed: invalid response '{choice}'. Trade details: {trade_details}")
    return False
