# from datetime import datetime, timezones
import datetime
import inspect
import os
import re
from typing import Literal

import click
from dateutil.parser import parse, parserinfo
from dateutil.tz import gettz

log_dir = None


def format_dt(seconds: int) -> str:
    """
    Formats a given number of seconds since the epoch into a string representation.

    Args:
        seconds (int): Positive seconds for aware datetime, negative for naive datetime.

    Returns:
        str: Formatted datetime string ("%y-%m-%d %H:%M").
    """
    if seconds >= 0:
        # Aware datetime: Convert from UTC to local timezone
        dt = datetime.datetime.fromtimestamp(seconds, tz=gettz("UTC")).astimezone()
    else:
        # Naive datetime: Treat as UTC without timezone adjustment
        dt = datetime.datetime.utcfromtimestamp(-seconds).replace(tzinfo=None)

    return dt.strftime("%y-%m-%d %H:%M")


def timestamp():
    return round(datetime.datetime.now().timestamp())


def format_datetime(
    seconds: int, fmt: str = "%Y-%m-%d %H:%M %Z", stage: int = 1
) -> str:
    return f"{datetime.datetime.fromtimestamp(seconds).astimezone().strftime(fmt)}"


# def click_log(msg: str, show_locals: bool = False):
def click_log(msg: str):
    # Get the name of the calling function
    caller_name = inspect.stack()[1].function
    log_name = format_datetime(timestamp(), "%Y-%m-%d.log")

    msgs = []
    msgs.append(f"% click_log {format_datetime(timestamp())} [{caller_name}]")
    ll = []
    for key, value in locals().items():
        if key in ["ll", "log_name", "show_locals", "msgs", "msg", "caller_name"]:
            continue
        ll.append(f"%     {key}: {value}")
    if ll:
        msgs.append("%   Local variables:")
        msgs.extend(ll)
    msgs.append(f"%   {msg}\n")
    msg = "\n".join(msgs)

    # Format the log message
    if log_dir:
        with open(os.path.join(log_dir, log_name), "a") as debug_file:
            # msg = f"\nclick_log {format_datetime(timestamp())} [{caller_name}]\n{msg}"
            click.echo(
                msg,
                file=debug_file,
            )
    else:
        # msg = f"\nclick_log {format_datetime(timestamp())} [{caller_name}]\n{msg}"
        click.echo(
            msg,
        )


def datetime_to_seconds(input_str: str) -> int:
    """
    Parses a datetime string with an optional timezone and returns the corresponding
    seconds since the epoch as a positive or negative integer.

    Args:
        input_str (str): The input string in the format "<datetime> z<timezone>"
                         or "<datetime> zNaive".

    Returns:
        int: Positive seconds for aware (with timezone), negative for naive (zNaive).
    """
    if "z" in input_str:
        datetime_part, timezone_part = input_str.split("z", 1)
    else:
        datetime_part, timezone_part = input_str, None

    # Create custom parserinfo with desired settings
    info = parserinfo(dayfirst=False, yearfirst=True)

    # Parse the datetime part
    dt = parse(datetime_part.strip(), parserinfo=info)

    if timezone_part:
        timezone_part = timezone_part.strip()
        if timezone_part.lower() == "float":
            # Handle zNaive: Treat as UTC first, then negate
            dt_utc = dt.replace(tzinfo=gettz("UTC"))
            # naive_seconds = round(dt.replace(tzinfo=gettz("UTC")).timestamp())
            naive_seconds = round(dt_utc.timestamp())
            click_log(f"{naive_seconds = }")
            # click_log(f"naive_seconds = ")
            return -naive_seconds
        else:
            # Handle other timezones: Aware datetime
            tz = gettz(timezone_part)
            if tz is None:
                raise ValueError(f"Invalid timezone: {timezone_part}")
            dt = dt.replace(tzinfo=tz)
    else:
        # Default to local timezone if no timezone is specified
        dt = dt.astimezone()

    # Return positive seconds for aware datetimes
    return int(dt.timestamp())


def time_to_seconds(time_str: str) -> int:
    """
    Converts a time string composed of integers followed by 'd', 'h', 'm', or 's'
    into the total number of seconds.

    Args:
        time_str (str): The time string (e.g., '3h15s').

    Returns:
        int: The total number of seconds.

    Raises:
        ValueError: If the input string is not in the expected format.
    """
    # Define time multipliers for each unit
    multipliers = {
        "d": 24 * 60 * 60,  # Days to seconds
        "h": 60 * 60,  # Hours to seconds
        "m": 60,  # Minutes to seconds
        "s": 1,  # Seconds
    }

    # Match all integer-unit pairs (e.g., "3h", "15s")
    matches = re.findall(r"(\d+)([dhms])", time_str)

    if not matches:
        raise ValueError(
            "Invalid time string format. Expected integers followed by 'd', 'h', 'm', or 's'."
        )

    # Convert each match to seconds and sum them
    total_seconds = sum(int(value) * multipliers[unit] for value, unit in matches)
    return total_seconds


def seconds_to_time(seconds: int) -> str:
    """
    Converts an integer number of seconds into a human-readable time string
    using days, hours, minutes, and seconds.

    Args:
        seconds (int): The total number of seconds.

    Returns:
        str: A time string (e.g., '3h15s', '2d5h', etc.).
    """
    if seconds < 0:
        raise ValueError("Seconds must be non-negative.")

    # Define time units in seconds
    time_units = {
        "d": 24 * 60 * 60,  # Days to seconds
        "h": 60 * 60,  # Hours to seconds
        "m": 60,  # Minutes to seconds
        "s": 1,  # Seconds
    }

    # Compute the number of each unit
    result = []
    for unit, value in time_units.items():
        if seconds >= value:
            count = seconds // value
            seconds %= value
            result.append(f"{count}{unit}")

    return "".join(result) or "0s"  # Return '0s' for input 0


def seconds_to_datetime(seconds: int) -> datetime.datetime:
    """
    Converts an integer seconds (positive for aware, negative for float)
    into a corresponding datetime.

    Args:
        seconds (int): The seconds since the epoch.
                      Positive = Aware (UTC converted to local timezone),
                      Negative = float (interpreted as UTC).

    Returns:
        datetime: The corresponding datetime object.
    """
    if seconds >= 0:
        # Aware datetime: UTC to local time
        dt_utc = datetime.datetime.fromtimestamp(seconds, tz=gettz("UTC"))
        dt_local = dt_utc.astimezone()  # Convert to local timezone
        return dt_local.strftime("%y-%m-%d %H:%M")
    else:
        # float datetime: Treat as UTC but without attaching a timezone
        dt_float = datetime.datetime.fromtimestamp(abs(seconds), tz=gettz("UTC"))
        click_log(f"{dt_float = }")
        return dt_float.replace(tzinfo=None).strftime("%y-%m-%d %H:%M zFloat")


if __name__ == "__main__":
    # Tests only run when this file is executed directly
    def run_time_tests():
        print("Running tests for time_to_seconds...")

        # Define test cases
        test_cases = {
            "3h15s": 10815,
            "2d5h30m45s": 187845,
            "10m": 600,
            "45s": 45,
            "15s3h": 10815,
        }

        # Track failures
        failures = []

        # Run tests
        for input_str, expected in test_cases.items():
            result = time_to_seconds(input_str)
            if result != expected:
                failures.append(
                    f"Test failed for input '{input_str}': expected {expected}, got {result}"
                )

        # Report results
        if failures:
            print("\n".join(failures))
            print("Some time tests failed!")
        else:
            print("All time tests passed!")

    def run_datetime_tests():
        print("Running tests for datetime_to_seconds...")

        # Define test cases
        test_cases = [
            ("2023-11-22 8:00 zUS/Pacific", 1700659200),  # Aware in US/Pacific
            ("2023-11-22 8:00 zFloat", -1700640000),  # float UTC
            ("2023-11-22 8:00", None),  # Local timezone
        ]

        for input_str, expected in test_cases:
            try:
                result = datetime_to_seconds(input_str)
                if expected is not None and result != expected:
                    print(
                        f"Test failed for input '{input_str}': expected {expected}, got {result}"
                    )
                elif expected is None:
                    print(
                        f"Test '{input_str}': {result} seconds (Local Timezone or relative date)"
                    )
            except Exception as e:
                print(f"Test failed for input '{input_str}': {e}")

    print("All tests completed!")
    run_time_tests()
    run_datetime_tests()
    for dt in ["8a", "8am Thu", "8am Thu zUS/Pacific", "8am Thu zUTC", "8a Thu zFloat"]:
        seconds = datetime_to_seconds(dt)
        result = seconds_to_datetime(seconds)
        print(f"{dt = }; {seconds = }; \n    {result = }")
    # print(datetime_to_seconds("8am Thu"))
    # print(datetime_to_seconds("8am Thu zUS/Pacific"))
    # print(datetime_to_seconds("8am Thu zUTC"))
else:

    from . import CONFIG_FILE, backup_dir, db_path, log_dir, pos_to_id, timemate_home
