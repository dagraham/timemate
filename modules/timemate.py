import datetime
import inspect
import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Literal

import click
import yaml  # pip install pyyaml
from click_shell import shell
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.tree import Tree

from . import (CONFIG_FILE, backup_dir, db_path, log_dir, pos_to_id,
               timemate_home)
from .__version__ import version

AllowedMinutes = Literal[1, 6, 12, 30, 60]
MINUTES = 1

console = Console()


def timestamp():
    return round(datetime.datetime.now().timestamp())


def format_datetime(
    seconds: int, fmt: str = "%Y-%m-%d %H:%M %Z", stage: int = 1
) -> str:
    return f"{datetime.datetime.fromtimestamp(seconds).astimezone().strftime(fmt)}"


def click_log(msg: str):
    # Get the name of the calling function
    caller_name = inspect.stack()[1].function
    ts = timestamp()
    log_name = format_datetime(ts, "%Y-%m-%d.log")

    # Format the log message
    with open(os.path.join(log_dir, log_name), "a") as debug_file:
        msg = f"\nclick_log {format_datetime(timestamp())} [{caller_name}]\n{msg}"
        click.echo(
            msg,
            file=debug_file,
        )


# click_log(
#     f"{timemate_home = }; {backup_dir = }; {log_dir =}, {db_path = }; {version = }"
# )


# Other imports and functions remain unchanged...
@click.command(short_help="Archive timers dated before today")
def timer_archive():
    """
    Archive timers by setting the status to 'inactive' for all timers with start times before today. Such timers will not be displayed by list-timers unless the flag '--all' is appended.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Calculate the cutoff timestamp for the current day
    now = datetime.datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    # Update status for timers
    cursor.execute(
        """
        UPDATE Times
        SET status = 'inactive'
        WHERE datetime < ? AND status != 'inactive'
        """,
        (midnight,),
    )
    conn.commit()
    console.print(
        "[green]Timers with start times before today have been archived![/green]"
    )
    conn.close()


@shell(
    prompt="TimeMate> ",
    intro="Welcome to the TimeMate shell! Type ? or help for commands.",
)
def cli():
    """TimeMate: record and report times spent in various activities"

    Started without any options, open a TimeMate shell.
    """
    conn = setup_database()


@click.command()
@click.argument("account_name")
def account_add(account_name):
    """Add a new account."""
    conn = setup_database()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Accounts (account_name, datetime) VALUES (?, ?)",
            (account_name, timestamp()),
        )
        conn.commit()
        console.print(
            f"[limegreen]Account '{account_name}' added successfully![/limegreen]"
        )
    except sqlite3.IntegrityError:
        console.print(f"[red]Account '{account_name}' already exists![/red]")
    conn.close()


def format_hours_and_tenths(total_seconds: int):
    """
    Convert seconds into hours and tenths of an hour, rounding up based on the global MINUTES setting.
    """
    if MINUTES <= 1:
        # hours, minutes and seconds if not rounded up
        return format_hours_minutes(total_seconds)

    seconds = total_seconds
    minutes = seconds // 60
    if seconds % 60:
        minutes += 1
    if minutes:
        return f"{math.ceil(minutes / MINUTES) / (60 / MINUTES)}"
    else:
        return "0.0"


def format_dt(seconds: int):
    dt = datetime.datetime.fromtimestamp(seconds)
    return dt.strftime("%y-%m-%d %H:%M")


def format_hours_minutes(total_seconds: int) -> str:
    until = []
    hours = minutes = seconds = 0
    if total_seconds:
        seconds = total_seconds
        if seconds >= 60:
            minutes = seconds // 60
            seconds = seconds % 60
            if seconds >= 30:
                minutes += 1
            seconds = 0
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
    return f"{hours}:{minutes:>02}"


def setup_database():
    conn = sqlite3.connect(db_path)  # Use a persistent SQLite database
    cursor = conn.cursor()

    # Create Settings table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Settings (
            setting_name TEXT PRIMARY KEY,
            setting_value INTEGER
        )
    """
    )

    # Insert default MINUTES value if not already set
    cursor.execute(
        """
        INSERT OR IGNORE INTO Settings (setting_name, setting_value)
        VALUES ('MINUTES', 1)
    """
    )

    # Create Accounts table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL UNIQUE,
            datetime INTEGER
        )
    """
    )

    # Create Times table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Times (
            time_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            memo TEXT, 
            status TEXT CHECK(status IN ('paused', 'running', 'inactive')) DEFAULT 'paused',
            timedelta INTEGER NOT NULL DEFAULT 0,
            datetime INTEGER,
            rounded_timedelta INTEGER,
            FOREIGN KEY (account_id) REFERENCES Accounts(account_id)
        )
    """
    )

    conn.commit()

    create_triggers(conn)

    return conn


def get_minutes_setting(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM Settings WHERE setting_name = 'MINUTES'")
    result = cursor.fetchone()
    return result[0] if result else 1  # Default to 1


# MINUTES = get_minutes_setting(conn)
# click_log(f"got {MINUTES = }")


def create_triggers(conn):
    minutes = get_minutes_setting(conn)

    cursor = conn.cursor()

    # Drop existing triggers to avoid duplicates
    cursor.execute("DROP TRIGGER IF EXISTS calculate_rounded_timedelta_insert")
    cursor.execute("DROP TRIGGER IF EXISTS calculate_rounded_timedelta_update")

    # Create new triggers
    cursor.execute(
        f"""
    CREATE TRIGGER calculate_rounded_timedelta_insert
    AFTER INSERT ON Times
    FOR EACH ROW
    BEGIN
        UPDATE Times
        SET rounded_timedelta = CEIL(NEW.timedelta / ({minutes} * 60.0)) * ({minutes} * 60)
        WHERE time_id = NEW.time_id;
    END;
    """
    )

    cursor.execute(
        f"""
    CREATE TRIGGER calculate_rounded_timedelta_update
    AFTER UPDATE OF timedelta ON Times
    FOR EACH ROW
    BEGIN
        UPDATE Times
        SET rounded_timedelta = CEIL(NEW.timedelta / ({minutes} * 60.0)) * ({minutes} * 60)
        WHERE time_id = NEW.time_id;
    END;
    """
    )

    conn.commit()


@click.command(short_help="Set the round-up value for report times")
@click.argument("new_minutes", type=click.Choice(["1", "6", "12", "30", "60"]))
def set_minutes(new_minutes):
    """
    Update the MINUTES setting from [1, 6, 12, 30, 60]. With 1, elapsed times in reports are rounded up to the next minute, with 6 they are rounded up to the next 6/60 = 1/10 of an hour, with 12 to the next 12/60 = 2/10 of an hour and so forth.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Update the database
    new_minutes = int(new_minutes)
    cursor.execute(
        """
        UPDATE Settings
        SET setting_value = ?
        WHERE setting_name = 'MINUTES'
    """,
        (new_minutes,),
    )
    conn.commit()

    # Update the global MINUTES variable
    global MINUTES
    MINUTES = new_minutes

    # Recreate triggers (if needed)
    create_triggers(conn)

    console.print(f"[green]MINUTES setting updated to {new_minutes}.[/green]")
    conn.close()


@click.command()
def list_accounts():
    """List all accounts."""
    _accounts_list()


def _accounts_list():
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()
    table = Table(title="Accounts", expand=True)
    table.add_column("row", justify="center", width=2, style="dim")
    table.add_column("account name", style="cyan")
    for idx, (account_id, account_name) in enumerate(accounts, start=1):
        table.add_row(str(idx), account_name)
    console.print(table)
    conn.close()


@click.command(short_help="add a new timer")
def timer_add():
    """
    Add a timer. Use fuzzy autocompletion to select or create an account,
    then optionally add a memo to describe the time spent.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch all account names and positions for autocompletion
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()

    account_completions = {}
    for idx, (account_id, account_name) in enumerate(accounts, start=1):
        account_completions[str(idx)] = account_id  # Map position to account_id
        account_completions[account_name.lower()] = account_id  # Map name to account_id

    # Create a FuzzyCompleter with account names and positions
    completer = FuzzyCompleter(
        WordCompleter(account_completions.keys(), ignore_case=True)
    )

    # Use PromptSession for fuzzy autocompletion
    session = PromptSession()
    try:
        selection = session.prompt(
            "Enter account position or name: ",
            completer=completer,
            complete_while_typing=True,
        )
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Resolve selection to account_id
    account_id = account_completions.get(selection.lower())
    if not account_id:  # If input is a new account name
        cursor.execute("INSERT INTO Accounts (account_name) VALUES (?)", (selection,))
        conn.commit()
        account_id = cursor.lastrowid

    # Prompt for memo (optional)
    try:
        memo = session.prompt(
            "Enter a memo to describe the time spent (optional): ", default=""
        )
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Add the timer
    now = timestamp()
    cursor.execute(
        "INSERT INTO Times (account_id, memo, status, timedelta, datetime) VALUES (?, ?, 'paused', 0, ?)",
        (account_id, memo, now),
    )
    conn.commit()
    console.print("[green]Timer added successfully![/green]")
    conn.close()


@click.command(short_help="shortcut for timer-add")
@click.argument("arguments", nargs=-1)
def ta(arguments):
    """
    Shortcut for adding a timer using arguments <account id> and [memo]

    Example:
        ta 27 some writing
    """
    if len(arguments) < 1:
        console.print("[red]Invalid input. Usage: add <account_id> [memo][/red]")
        return

    try:
        account_id = int(arguments[0])  # First part is the account_id
        memo = " ".join(arguments[1:])  # The rest is the memo
    except ValueError:
        console.print("[red]Invalid account_id. Must be an integer.[/red]")
        return

    # Add the timer
    conn = setup_database()
    cursor = conn.cursor()

    # Check if the account_id exists
    cursor.execute(
        "SELECT account_name FROM Accounts WHERE account_id = ?", (account_id,)
    )
    result = cursor.fetchone()

    if not result:
        console.print(f"[red]No account found with account_id {account_id}.[/red]")
        conn.close()
        return

    account_name = result[0]
    now = timestamp()
    cursor.execute(
        """
        INSERT INTO Times (account_id, memo, status, timedelta, datetime)
        VALUES (?, ?, 'paused', 0, ?)
        """,
        (account_id, memo, now),
    )
    conn.commit()
    conn.close()

    console.print(
        f"[green]Timer added for account '{account_name}' with memo: '{memo}'[/green]"
    )


@click.command()
@click.argument("position", type=int)
def timer_update(position):
    """
    Update fields (account, memo, timedelta) for a specific timer interactively.
    Existing values are shown as defaults.
    """
    time_id = pos_to_id.get(position)
    click_log(f"got {time_id = } from {position = }")
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch the current timer record
    cursor.execute(
        """
        SELECT T.account_id, A.account_name, T.memo, T.timedelta, T.datetime
        FROM Times T
        JOIN Accounts A ON T.account_id = A.account_id
        WHERE T.time_id = ?
        """,
        (time_id,),
    )
    timer = cursor.fetchone()

    if not timer:
        console.print(f"[red]Timer ID {timer_id} not found![/red]")
        conn.close()
        return

    account_id, current_account, current_memo, current_timedelta, current_datetime = (
        timer
    )

    # Format current datetime for display
    current_datetime_str = (
        datetime.datetime.fromtimestamp(current_datetime).strftime("%y-%m-%d %H:%M")
        if current_datetime
        else ""
    )

    # Fetch all accounts for fuzzy completion
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()
    account_completions = {
        account_name.lower(): (account_id, account_name)
        for account_id, account_name in accounts
    }

    # PromptSession setup
    session = PromptSession()
    completer = FuzzyCompleter(
        WordCompleter(account_completions.keys(), ignore_case=True)
    )

    # Prompt for new account name with fuzzy completion
    try:
        new_account_name = session.prompt(
            f"Enter account name [{current_account}]: ",
            completer=completer,
            complete_while_typing=True,
            default=current_account,
        ).lower()
    except KeyboardInterrupt:
        console.print("[red]Operation cancelled by user.[/red]")
        conn.close()
        return

    # Resolve account ID (use the current one if unchanged)
    if new_account_name == current_account.lower():
        new_account_id = account_id
    else:
        resolved_account = account_completions.get(new_account_name)
        if not resolved_account:
            console.print(f"[red]Account '{new_account_name}' not found![/red]")
            conn.close()
            return
        new_account_id = resolved_account[0]

    # Prompt for memo
    try:
        new_memo = session.prompt(
            f"Enter memo [{current_memo or ''}]: ", default=current_memo or ""
        )
    except KeyboardInterrupt:
        console.print("[red]Operation cancelled by user.[/red]")
        conn.close()
        return

    # Prompt for timedelta
    try:
        new_timedelta = session.prompt(
            f"Enter timedelta (seconds) [{current_timedelta}]: ",
            default=str(current_timedelta),
        )
        new_timedelta = int(new_timedelta)
    except (ValueError, KeyboardInterrupt):
        console.print("[red]Invalid input or operation cancelled.[/red]")
        conn.close()
        return

    # Prompt for datetime
    try:
        new_datetime_input = session.prompt(
            f"Enter datetime (YY-MM-DD HH:MM) [{current_datetime_str}]: ",
            default=current_datetime_str,
        )
        new_datetime = (
            round(
                datetime.datetime.strptime(
                    new_datetime_input, "%y-%m-%d %H:%M"
                ).timestamp()
            )
            if new_datetime_input.strip()
            else current_datetime
        )
    except (ValueError, KeyboardInterrupt):
        console.print("[red]Invalid datetime format or operation cancelled.[/red]")
        conn.close()
        return

    # Update the timer record
    cursor.execute(
        """
        UPDATE Times
        SET account_id = ?, memo = ?, timedelta = ?, datetime = ?
        WHERE time_id = ?
        """,
        (new_account_id, new_memo, new_timedelta, new_datetime, time_id),
    )
    conn.commit()
    conn.close()

    console.print(f"[green]Timer {position} updated successfully![/green]")


@cli.command(short_help="Shows info for TimeMate")
def info():
    """Show application information."""

    _info()


def _info():
    console.print(
        f"""\
[#87CEFA]Time Mate[/#87CEFA]
version: [green]{version}[/green]
config:  [green]{CONFIG_FILE}[/green]
home:    [green]{timemate_home}[/green]
MINUTES: [green]{MINUTES}[/green]
"""
    )


@click.command()
@click.option(
    "--all", is_flag=True, default=False, help="Include timers with any status."
)
def list_timers(all):
    """
    List timers. By default, shows only timers with status in ('running', 'paused').
    """
    _list_timers(all)


def _list_timers(include_all=False):
    global pos_to_id
    conn = setup_database()
    cursor = conn.cursor()

    if include_all:
        status_filter = "1 = 1"  # No filter, include all statuses
        console.print("[blue]Displaying all timers:[/blue]")
    else:
        status_filter = "status IN ('running', 'paused')"
        console.print("[blue]Displaying active timers (running, paused):[/blue]")

    # Fetch timers based on the filter
    cursor.execute(
        f"""
        SELECT T.time_id, A.account_name, T.memo, T.status, T.rounded_timedelta, T.datetime 
        FROM Times T
        JOIN Accounts A ON T.account_id = A.account_id
        WHERE {status_filter}
        ORDER BY T.time_id
        """
    )
    timers = cursor.fetchall()

    table = Table(title="Timers", expand=True)
    table.add_column("row", justify="center", width=3, style="dim")
    table.add_column("account name", width=15)
    table.add_column("memo", justify="center", width=8)
    table.add_column("status", justify="center", style="green", width=6)
    table.add_column("time", justify="right", width=4),
    table.add_column("date", justify="center", width=10)

    now = round(datetime.datetime.now().timestamp())
    for idx, (time_id, account_name, memo, status, timedelta, start_time) in enumerate(
        timers, start=1
    ):
        pos_to_id[idx] = time_id
        elapsed = timedelta + (now - start_time if status == "running" else 0)
        status_color = (
            "yellow"
            if status == "running"
            else "green" if status == "paused" else "blue"
        )
        table.add_row(
            str(idx),
            f"[{status_color}]{account_name}[/{status_color}]",
            f"[{status_color}]{memo}[/{status_color}]",
            f"[{status_color}]{status}[/{status_color}]",
            f"[{status_color}]{format_hours_and_tenths(elapsed)}[/{status_color}]",
            f"[{status_color}]{format_dt(start_time)}[/{status_color}]",
        )
    console.clear()
    console.print(table)
    conn.close()


@cli.command("ts", short_help="Shortcut for timer-start")
@click.argument("position", type=int)
@click.pass_context
def timer_start_shortcut(ctx, position):
    """Shortcut for "timer-start". Start timer at POSITION."""
    ctx.forward(timer_start)


@click.command()
@click.argument("position", type=int)
def timer_start(position):
    """Start a timer."""
    time_id = pos_to_id.get(position)
    click_log(f"got {time_id = } from {position = }")

    conn = setup_database()
    cursor = conn.cursor()

    now = timestamp()
    today = round(
        datetime.datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    )
    # Stop the currently running timer (if any)
    cursor.execute(
        """
        UPDATE Times
        SET status = 'paused', timedelta = timedelta + (? - datetime), datetime = ?
        WHERE status = 'running'
        """,
        (now, now),
    )

    if time_id:
        cursor.execute(
            """
            SELECT time_id, account_id, memo, datetime, timedelta, status
            FROM Times
            WHERE time_id = ? 
            """,
            (time_id,),
        )
        row = cursor.fetchone()

        if row:
            time_id, account_id, memo, start_time, timedelta, status = row
            if start_time and start_time < today:  # Timer from a previous day
                # Create a new timer
                click_log(f"copying as a new timer")
                cursor.execute(
                    """
                    INSERT INTO Times (account_id, memo, status, timedelta, datetime)
                    VALUES (?, ?, 'running', 0, ?)
                    """,
                    (account_id, memo, now),
                )
                new_timer_id = cursor.lastrowid
                console.print(
                    f"[yellow]Timer from a previous day detected. Created a new timer with ID {new_timer_id}.[/yellow]"
                )

                click_log(f"archiving original timer")
                cursor.execute(
                    """
                    UPDATE Times
                    SET status = 'inactive'
                    WHERE time_id = ?
                    """,
                    (time_id,),
                )
                conn.commit()

            else:
                # Start the selected timer
                cursor.execute(
                    """
                    UPDATE Times
                    SET status = 'running', datetime = ?
                    WHERE time_id = ?
                    """,
                    (now, time_id),
                )
                console.print(f"[green]Timer {position} started![/green]")
    else:
        console.print("[red]Invalid position![/red]")

    conn.commit()
    conn.close()
    _list_timers()


@cli.command("tp", short_help="Shortcut for timer-pause")
@click.argument("position", type=int)
@click.pass_context
def timer_pause_shortcut(ctx, position):
    """Shortcut for "timer-pause". Pause timer at POSITION."""
    ctx.forward(timer_pause)


@click.command()
@click.argument("position", type=int)
def timer_pause(position):
    """Pause a timer."""
    time_id = pos_to_id.get(position)
    click_log(f"got {time_id = } from {position = }")

    conn = setup_database()
    cursor = conn.cursor()

    now = timestamp()

    if time_id:
        cursor.execute(
            """
            SELECT time_id, datetime
            FROM Times
            WHERE time_id = ?
            """,
            (time_id,),
        )

        row = cursor.fetchone()

        if row:
            time_id, start_time = row
            if start_time is None:
                console.print(f"[yellow]Timer {position} is already paused.[/yellow]")
            else:
                elapsed = now - start_time
                cursor.execute(
                    """
                    UPDATE Times
                    SET status = 'paused', timedelta = timedelta + ?, datetime = ?
                    WHERE time_id = ?
                    """,
                    (elapsed, now, time_id),
                )
                conn.commit()
                console.print(f"[yellow]Timer {position} stopped![/yellow]")
    else:
        console.print("[red]Invalid position![/red]")

    conn.close()
    _list_timers()


@click.command(short_help="Generate a weekly report")
@click.argument("report_date", type=click.DateTime(formats=["%y-%m-%d"]))
def report_week(report_date):
    """
    Generate a weekly report for the week containing REPORT_DATE (format: YY-MM-DD).
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Calculate the start and end of the week (Monday to Sunday)
    week_start = report_date - datetime.timedelta(days=report_date.weekday())
    week_end = week_start + datetime.timedelta(days=6)

    # Total time for the week
    cursor.execute(
        """
        SELECT SUM(T.timedelta)
        FROM Times T
        WHERE T.datetime BETWEEN ? AND ?
        ORDER BY T.datetime
        """,
        (week_start.timestamp(), week_end.timestamp()),
    )
    week_total = cursor.fetchone()[0] or 0

    console.print(
        f"[bold cyan]Weekly Report[/bold cyan] ({week_start.date()} to {week_end.date()}):"
    )
    console.print(f"Total Time: [yellow]{format_hours_and_tenths(week_total)}[/yellow]")

    # Daily breakdown
    for i in range(7):
        day = week_start + datetime.timedelta(days=i)
        cursor.execute(
            """
            SELECT SUM(T.timedelta)
            FROM Times T
            WHERE T.datetime BETWEEN ? AND ?
            ORDER BY T.datetime
            """,
            (day.timestamp(), (day + datetime.timedelta(days=1)).timestamp()),
        )
        day_total = cursor.fetchone()[0] or 0
        if day_total == 0:
            continue
        console.print(
            f"\n[bold][green]{day.strftime('%a %b %-d')}[/green] - [yellow]{format_hours_and_tenths(day_total)}[/yellow][/bold]"
        )

        # Timers for the day
        cursor.execute(
            """
            SELECT A.account_name, T.timedelta, T.datetime, T.memo
            FROM Times T
            JOIN Accounts A ON T.account_id = A.account_id
            WHERE T.datetime BETWEEN ? AND ?
            ORDER BY T.datetime
            """,
            (day.timestamp(), (day + datetime.timedelta(days=1)).timestamp()),
        )
        timers = cursor.fetchall()

        for account_name, timedelta, datetime_val, memo in timers:
            datetime_str = datetime.datetime.fromtimestamp(datetime_val).strftime(
                "%H:%M"
            )
            memo_str = f" ({memo})" if memo else ""
            console.print(
                # f"  [yellow]{format_hours_and_tenths(timedelta)}[/yellow] [green]{datetime_str}[/green]{memo_str} [#6699ff]{account_name}[/#6699ff] "
                f"    [yellow]{format_hours_and_tenths(timedelta)}[/yellow] [green]{datetime_str}[/green] [#6699ff]{account_name}[/#6699ff]{memo_str}"
            )

    conn.close()


@click.command(short_help="Generate a monthly report")
def report_month():
    """
    Generate a monthly report for the month containing a specified date.
    Prompts for the month in YY-MM format.
    """
    conn = setup_database()
    cursor = conn.cursor()

    session = PromptSession()
    try:
        month_input = session.prompt("Enter the month for the report (YY-MM): ")
        report_date = datetime.datetime.strptime(month_input, "%y-%m")
    except ValueError:
        console.print("[red]Invalid date format! Please use YY-MM.[/red]")
        conn.close()
        return
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Calculate the start and end of the month
    month_start = report_date.replace(day=1)
    next_month = (month_start + datetime.timedelta(days=32)).replace(day=1)
    month_end = next_month - datetime.timedelta(seconds=1)

    # Total time for the month
    cursor.execute(
        """
        SELECT SUM(T.rounded_timedelta)
        FROM Times T
        WHERE T.datetime BETWEEN ? AND ?
        """,
        (month_start.timestamp(), month_end.timestamp()),
    )
    month_total = cursor.fetchone()[0] or 0

    console.print(
        f"\n[bold][cyan]Monthly Report[/cyan] [green]{month_start.strftime('%b %Y')}[/green] - [yellow]{format_hours_and_tenths(month_total)}[/yellow][/bold]"
    )

    # Breakdown by account
    cursor.execute(
        """
        SELECT A.account_name, SUM(T.rounded_timedelta)
        FROM Times T
        JOIN Accounts A ON T.account_id = A.account_id
        WHERE T.datetime BETWEEN ? AND ?
        GROUP BY A.account_name
        ORDER BY A.account_name
        """,
        (month_start.timestamp(), month_end.timestamp()),
    )
    accounts = cursor.fetchall()

    for account_name, account_total in accounts:
        console.print(
            f"\n[bold][#6699ff]{account_name}[/#6699ff] [green]{month_start.strftime('%b %Y')}[/green] - [yellow]{format_hours_and_tenths(account_total)}[/yellow][/bold]"
        )

        # Timers for the account
        cursor.execute(
            """
            SELECT T.rounded_timedelta, T.datetime, T.memo
            FROM Times T
            JOIN Accounts A ON T.account_id = A.account_id
            WHERE A.account_name = ? AND T.datetime BETWEEN ? AND ?
            ORDER BY T.datetime
            """,
            (account_name, month_start.timestamp(), month_end.timestamp()),
        )
        timers = cursor.fetchall()

        for rounded_timedelta, datetime_val, memo in timers:
            datetime_str = datetime.datetime.fromtimestamp(datetime_val).strftime(
                "%d %H:%M"
            )
            memo_str = f" ({memo})" if memo else ""
            console.print(
                f"  [yellow]{format_hours_and_tenths(rounded_timedelta)}[/yellow] [green]{datetime_str}[/green]{memo_str}"
            )

    conn.close()


@click.command(short_help="Generate a report for account(s)")
@click.option(
    "--tree", is_flag=True, default=False, help="Display the report as a tree summary."
)
def report_account(tree):
    """
    Generate a monthly report for accounts matching a specific name or pattern.
    Prompts for account name (supports fuzzy matching) and optionally for a starting month.
    If no starting month is provided, generates a report for all months.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch account names for fuzzy matching
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()

    account_completions = {
        account_name.lower(): (account_id, account_name)
        for account_id, account_name in accounts
    }

    # Prompt for account using fuzzy autocompletion
    completer = FuzzyCompleter(
        WordCompleter(account_completions.keys(), ignore_case=True)
    )
    session = PromptSession()
    try:
        selected_name = session.prompt(
            "Enter account name (supports fuzzy matching): ",
            completer=completer,
            complete_while_typing=True,
        ).lower()
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Find matching accounts
    matching_accounts = [
        (account_id, account_name)
        for account_name_lower, (
            account_id,
            account_name,
        ) in account_completions.items()
        if selected_name in account_name_lower
    ]

    if not matching_accounts:
        console.print(f"[red]No accounts found matching '{selected_name}'![/red]")
        conn.close()
        return

    if selected_name:
        ACCOUNTS = (
            f"accounts matching '{selected_name}'"
            if len(matching_accounts) > 1
            else f"{matching_accounts[0][1]}"
        )
    else:
        ACCOUNTS = "all accounts"
    # Prompt for starting month (optional)
    try:
        start_date_input = session.prompt(
            "Enter starting month (YY-MM) (press Enter to include all months): ",
            default="",
        )
        start_date = (
            datetime.datetime.strptime(start_date_input, "%y-%m")
            if start_date_input
            else None
        )
    except ValueError:
        console.print("[red]Invalid date format! Please use YY-MM.[/red]")
        conn.close()
        return
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Generate report for all months if no start_date is provided
    if not start_date:
        cursor.execute(
            """
            SELECT MIN(datetime), MAX(datetime)
            FROM Times
            """
        )
        date_range = cursor.fetchone()
        if not date_range or not date_range[0]:
            console.print("[yellow]No records found in the database.[/yellow]")
            conn.close()
            return

        start_date = datetime.datetime.fromtimestamp(date_range[0])
        end_date = datetime.datetime.fromtimestamp(date_range[1])
    else:
        # Prompt for optional ending month if start_date is given
        try:
            end_date_input = session.prompt(
                "Enter ending month (YY-MM) (press Enter to use the same as starting month): ",
                default=start_date.strftime("%y-%m"),
            )
            end_date = datetime.datetime.strptime(end_date_input, "%y-%m")
        except ValueError:
            console.print("[red]Invalid date format! Please use YY-MM.[/red]")
            conn.close()
            return
        except KeyboardInterrupt:
            console.print("[red]Cancelled by user.[/red]")
            conn.close()
            return

        if end_date < start_date:
            console.print("[red]Ending month cannot be before starting month![/red]")
            conn.close()
            return

    # Generate report grouped by month first
    current_date = start_date
    total = 0
    while current_date <= end_date:
        month_start = current_date.replace(day=1)
        next_month = (month_start + datetime.timedelta(days=32)).replace(day=1)
        month_end = next_month - datetime.timedelta(seconds=1)

        # Fetch data for each matching account
        paths = []
        for account_id, account_name in matching_accounts:
            # Timers for the account in this month
            cursor.execute(
                """
                SELECT T.rounded_timedelta, T.datetime, T.memo
                FROM Times T
                WHERE T.account_id = ? AND T.datetime BETWEEN ? AND ?
                ORDER BY T.datetime
                """,
                (account_id, month_start.timestamp(), month_end.timestamp()),
            )
            timers = cursor.fetchall()

            for rounded_timedelta, datetime_val, memo in timers:
                datetime_str = datetime.datetime.fromtimestamp(datetime_val).strftime(
                    "%d %H:%M"
                )
                total += rounded_timedelta
                paths.append(
                    (account_name, memo or "", rounded_timedelta, datetime_val)
                )

        if tree:
            # Build and display the tree
            report_title = f"{month_start.strftime('%B %Y')} times for {ACCOUNTS}"
            click_log(f"for tree using {paths = }")
            tree = build_tree(report_title, paths)
            console.print(tree)
        else:
            # Display the detailed report
            console.print(
                f"\n[bold cyan]{month_start.strftime('%B %Y')} times for {ACCOUNTS}[/bold cyan]"
            )
            for account_id, account_name in matching_accounts:
                # Total time for the account in this month
                cursor.execute(
                    """
                    SELECT SUM(T.rounded_timedelta)
                    FROM Times T
                    WHERE T.account_id = ? AND T.datetime BETWEEN ? AND ?
                    """,
                    (account_id, month_start.timestamp(), month_end.timestamp()),
                )
                account_total = cursor.fetchone()[0] or 0

                if account_total == 0:
                    continue  # Skip accounts with no timers in this month

                console.print(
                    f"\n[bold][#6699ff]{account_name}[/#6699ff] - [yellow]{format_hours_and_tenths(account_total)}[/yellow][/bold]"
                )

                for path in paths:
                    if path[0] == account_name:
                        account, memo, rounded_timedelta, datetime_val = path
                        datetime_str = datetime.datetime.fromtimestamp(
                            datetime_val
                        ).strftime("%d %H:%M")
                        memo_str = f" ({memo})" if memo else ""
                        console.print(
                            f"  [bold yellow]{format_hours_and_tenths(rounded_timedelta)}[/bold yellow] [green]{datetime_str}[/green]{memo_str}"
                        )

        # Move to the next month
        current_date = next_month

    conn.close()


def aggregate_paths(paths):
    """
    Aggregate paths for building a tree.
    """
    paths.sort()
    data = {}
    total = 0
    for name, _, time, _ in paths:
        if time == 0:
            continue
        total += time
        parts = name.split("/")
        for i in range(len(parts)):
            key = "/".join(parts[: i + 1])
            data.setdefault(key, 0)
            data[key] += time
    return total, data


def build_tree(name, paths):
    """
    Build a Rich Tree from a dictionary where keys are paths and values are numbers.
    """
    total, data = aggregate_paths(paths)

    root = Tree(
        f"[bold][blue]{name}[/blue] [yellow]{format_hours_and_tenths(total)}[/yellow][/bold]"
    )  # Create the root of the tree
    nodes = {}  # Store nodes to attach children dynamically

    for path, value in data.items():
        parts = path.split("/")  # Split the path into segments
        current_node = root

        # Iterate through the segments, creating nodes if necessary
        for i, part in enumerate(parts):
            # Construct the full path for the current node
            full_path = "/".join(parts[: i + 1])

            # Check if the node exists; if not, create it
            if full_path not in nodes:
                nodes[full_path] = current_node.add(part)

            # Move to the next node
            current_node = nodes[full_path]

        # Add the value as a leaf
        current_node.label = f"[bold][green]{current_node.label}[/green] [yellow]{format_hours_and_tenths(value)}[/yellow][/bold]"

    return root


@click.command(short_help="Populate the database with JSON or YAML records")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    help="File containing test data in JSON or YAML format.",
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Format of the input file (default: json).",
)
def populate(file, format):
    """
    Populate the Accounts and Times tables with data from a specified JSON or YAML file.
    """
    conn = setup_database()
    cursor = conn.cursor()

    if not file:
        console.print(
            "[red]Error: No input file provided! Use -f to specify a file.[/red]"
        )
        return

    # Load data from the file
    try:
        data = json.load(file) if format == "json" else yaml.safe_load(file)
    except Exception as e:
        console.print(f"[red]Error loading {format} data: {e}[/red]")
        return

    # Populate Accounts
    accounts = data.get("accounts", [])
    for account in accounts:
        account_name = account["account_name"]
        try:
            cursor.execute(
                "INSERT INTO Accounts (account_name, datetime) VALUES (?, ?)",
                (account_name, timestamp()),
            )
        except sqlite3.IntegrityError:
            console.print(
                f"[yellow]Account '{account_name}' already exists! Skipping.[/yellow]"
            )

    # Populate Times
    times = data.get("times", [])

    for time_entry in times:
        account_name = time_entry["account_name"]
        memo = time_entry.get("memo", "")
        timedelta = time_entry.get("timedelta", 0)
        datetime_val = time_entry.get("datetime", None)

        # Find account_id for account_name
        cursor.execute(
            "SELECT account_id FROM Accounts WHERE account_name = ?",
            (account_name,),
        )
        account = cursor.fetchone()
        if account:
            account_id = account[0]
            cursor.execute(
                """
                INSERT INTO Times (account_id, memo, status, timedelta, datetime)
                VALUES (?, ?, 'paused', ?, ?)
                """,
                (account_id, memo, timedelta, datetime_val),
            )
        else:
            console.print(
                f"[yellow]Account '{account_name}' not found! Skipping timer.[/yellow]"
            )

    conn.commit()
    conn.close()
    console.print("[green]Database populated successfully![/green]")


@cli.command("set-home", short_help="Set or clear a temporary home directory for TimeMate")
@click.argument("home", required=False)  # Optional argument for the home directory
def set_home(home):
    """
    Set or clear a temporary home directory for TimeMate.
    Provide a path to use as a temporary directory or
    enter nothing to stop using a temporary directory.
    """
    if home is None:
        # No argument provided, clear configuration
        update_tmp_home("")
    else:
        # Argument provided, set configuration
        update_tmp_home(home)


def is_valid_path(path):
    """
    Check if a given path is a valid directory.
    """
    path = Path(path).expanduser()

    # Check if the path exists and is a directory
    if path.exists():
        if path.is_dir():
            if os.access(path, os.W_OK):  # Check if writable
                return True, f"{path} is a valid and writable directory."
            else:
                return False, f"{path} is not writable."
        else:
            return False, f"{path} exists but is not a directory."
    else:
        # Try to create the directory
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True, f"{path} did not exist but has been created."
        except OSError as e:
            return False, f"Cannot create directory at {path}: {e}"


def update_tmp_home(tmp_home: str = ""):
    """
    Save the TimeMate path to the configuration file.
    """
    tmp_home = tmp_home.strip()
    if tmp_home:
        is_valid, message = is_valid_path(tmp_home)
        if is_valid:
            console.print(message)
            config = {"TIMEMATEHOME": tmp_home}
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
            console.print(f"Configuration saved to {CONFIG_FILE}")
        else:
            console.print(f"[red]An unexpected error occurred: {message}[/red]")
    elif os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        console.print(f"[green]Temporary home directory use cancelled[/green]")
    else:
        console.print(f"[yellow]Temporary home directory not in use[/yellow]")


@click.command(short_help="Delete the timer at POSITION")
@click.argument("position", type=int)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt.")
def timer_delete(position, confirm):
    """
    Delete the timer record at POSITION in list-timers.
    """
    time_id = pos_to_id.get(position)
    click_log(f"got {time_id = } from {position = }")

    conn = setup_database()
    cursor = conn.cursor()

    if not confirm:
        console.print("[yellow]This action cannot be undone.[/yellow]")
        confirm = click.confirm("Are you sure you want to delete this timer?")

    if confirm:
        cursor.execute("DELETE FROM Times WHERE time_id = ?", (time_id,))
        conn.commit()
        console.print(f"[green]Timer {time_id} deleted successfully![/green]")
    else:
        console.print("[blue]Delete operation cancelled.[/blue]")

    conn.close()


@click.command(short_help="Merge one account into another")
def account_merge():
    """
    Merge one account into another, transferring all timers and deleting the source account.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch account names for autocompletion
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()

    if len(accounts) < 2:
        console.print(
            "[yellow]At least two accounts are required to perform a merge.[/yellow]"
        )
        conn.close()
        return

    # Build account completions
    account_completions = {
        account_name.lower(): (account_id, account_name)
        for account_id, account_name in accounts
    }

    # Prompt for source account
    completer = FuzzyCompleter(
        WordCompleter(account_completions.keys(), ignore_case=True)
    )
    session = PromptSession()

    try:
        source_name = session.prompt(
            "Enter source account name (to be merged): ",
            completer=completer,
            complete_while_typing=True,
        ).lower()
        target_name = session.prompt(
            "Enter target account name (to merge into): ",
            completer=completer,
            complete_while_typing=True,
        ).lower()
    except KeyboardInterrupt:
        console.print("[red]Operation cancelled by user.[/red]")
        conn.close()
        return

    # Resolve accounts
    source_account = account_completions.get(source_name)
    target_account = account_completions.get(target_name)

    if not source_account:
        console.print(f"[red]Source account '{source_name}' not found![/red]")
        conn.close()
        return
    if not target_account:
        console.print(f"[red]Target account '{target_name}' not found![/red]")
        conn.close()
        return
    if source_account[0] == target_account[0]:
        console.print("[red]Source and target accounts must be different![/red]")
        conn.close()
        return

    # Merge confirmation
    console.print(
        f"[yellow]All timers from '{source_account[1]}' will be transferred to '{target_account[1]}'.[/yellow]"
    )
    if not click.confirm("Are you sure you want to proceed?"):
        console.print("[blue]Merge operation cancelled.[/blue]")
        conn.close()
        return

    # Update timers and delete the source account
    cursor.execute(
        "UPDATE Times SET account_id = ? WHERE account_id = ?",
        (target_account[0], source_account[0]),
    )
    cursor.execute("DELETE FROM Accounts WHERE account_id = ?", (source_account[0],))
    conn.commit()

    console.print(
        f"[green]Account '{source_account[1]}' merged into '{target_account[1]}' successfully![/green]"
    )
    conn.close()


@click.command(short_help="Delete an account and all related times records")
def account_delete():
    """
    Delete an account and all related timer records.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch account names for autocompletion
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()

    if not accounts:
        console.print("[yellow]No accounts found to delete![/yellow]")
        conn.close()
        return

    # Build account completions
    account_completions = {
        account_name.lower(): (account_id, account_name)
        for account_id, account_name in accounts
    }

    # Prompt for account name using fuzzy completion
    completer = FuzzyCompleter(
        WordCompleter(account_completions.keys(), ignore_case=True)
    )
    session = PromptSession()
    try:
        selected_name = session.prompt(
            "Enter account name to delete: ",
            completer=completer,
            complete_while_typing=True,
        ).lower()
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Resolve account
    account = account_completions.get(selected_name)
    if not account:
        console.print(f"[red]Account '{selected_name}' not found![/red]")
        conn.close()
        return

    account_id, account_name = account

    # Confirmation prompt
    console.print(
        f"[yellow]Warning: This will delete the account '{account_name}' and all related timers.[/yellow]"
    )
    if not click.confirm("Are you sure you want to proceed?"):
        console.print("[blue]Delete operation cancelled.[/blue]")
        conn.close()
        return

    # Delete related timers and the account
    cursor.execute("DELETE FROM Times WHERE account_id = ?", (account_id,))
    cursor.execute("DELETE FROM Accounts WHERE account_id = ?", (account_id,))
    conn.commit()
    console.print(
        f"[green]Account '{account_name}' and all related timers deleted successfully![/green]"
    )
    conn.close()


cli.add_command(account_add)
cli.add_command(account_delete)
cli.add_command(account_merge)
cli.add_command(list_accounts)
cli.add_command(list_timers)
cli.add_command(populate)
cli.add_command(report_account)
cli.add_command(report_month)
cli.add_command(report_week)
cli.add_command(set_home)
cli.add_command(set_minutes)
cli.add_command(info)
cli.add_command(ta)
cli.add_command(timer_add)
cli.add_command(timer_archive)
cli.add_command(timer_delete)
cli.add_command(timer_pause)
cli.add_command(timer_start)
cli.add_command(timer_update)


def main():
    conn = setup_database()  # Set up the database connection
    global MINUTES  # Ensure MINUTES is accessible globally
    MINUTES = get_minutes_setting(conn)  # Load MINUTES from the database
    click_log(f"got {MINUTES = }")
    console.clear()
    # _info()
    cli()


if __name__ == "__main__":
    main()
