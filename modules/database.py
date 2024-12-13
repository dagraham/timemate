import datetime
import json
import math
import os
import sqlite3
from typing import Literal

import click
import yaml  # pip install pyyaml
from click_shell import shell
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table


# Other imports and functions remain unchanged...
@click.command()
def archive_timers():
    """
    Archive timers by setting the status to 'inactive' for all timers with start times before today.
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
    """Time Mate: A CLI Timer Manager.

    Started without any options, open a TimeMate shell.
    """
    conn = setup_database()


@click.command()
@click.argument("account_name")
def add_account(account_name):
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


AllowedMinutes = Literal[0, 1, 6, 12, 30, 60]
MINUTES = 6

console = Console()


def timestamp():
    return round(datetime.datetime.now().timestamp())


def format_hours_and_tenths(total_seconds: int, round_up: AllowedMinutes = MINUTES):
    """
    Convert seconds into hours and tenths of an hour rounding up to the nearest AllowedMinutes.
    """
    if round_up <= 1:
        # hours, minutes and seconds if not rounded up
        return format_hours_minutes_seconds(total_seconds)
    seconds = total_seconds
    minutes = seconds // 60
    if seconds % 60:
        minutes += 1
    if minutes:
        return f"{math.ceil(minutes/round_up)/(60/round_up)}h"
    else:
        return "0.0h"


def format_dt(seconds: int):
    dt = datetime.datetime.fromtimestamp(seconds)
    return dt.strftime("%y-%m-%d %H:%M")


def format_hours_minutes_seconds(total_seconds: int) -> str:
    until = []
    hours = minutes = seconds = 0
    if total_seconds:
        seconds = total_seconds
        if seconds >= 60:
            minutes = seconds // 60
            seconds = seconds % 60
            if seconds >= 30:
                minutes += 1
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
    else:
        seconds = 0
    if hours:
        until.append(f"{hours}h")
    if minutes:
        until.append(f"{minutes}m")
    if seconds:
        until.append(f"{seconds}s")
    if not until:
        until.append("0m")
    return f"{''.join(until)}"


def setup_database():
    conn = sqlite3.connect("time_mate.db")  # Use a persistent SQLite database
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Accounts (
                        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_name TEXT NOT NULL UNIQUE,
                        datetime INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Times (
                        time_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        memo TEXT, 
                        status TEXT CHECK(status IN ('paused', 'running', 'inactive')) DEFAULT 'paused',
                        timedelta INTEGER NOT NULL DEFAULT 0,
                        datetime INTEGER,
                        FOREIGN KEY (account_id) REFERENCES Accounts(account_id))"""
    )
    conn.commit()
    return conn


@click.command()
def list_accounts():
    """List all accounts."""
    _list_accounts()


def _list_accounts():
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


@click.command()
def add_timer():
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
    cursor.execute(
        "INSERT INTO Times (account_id, memo, status, timedelta, datetime) VALUES (?, ?, 'paused', 0, NULL)",
        (account_id, memo),
    )
    conn.commit()
    console.print("[green]Timer added successfully![/green]")
    conn.close()


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
        SELECT T.time_id, A.account_name, T.memo, T.status, T.timedelta, T.datetime
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
    table.add_column("time", justify="right", width=3),
    table.add_column("date", justify="center", width=10)

    now = round(datetime.datetime.now().timestamp())
    for idx, (time_id, account_name, memo, status, timedelta, start_time) in enumerate(
        timers, start=1
    ):
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


@click.command()
@click.argument("position", type=int)
def timer_start(position):
    """Start a timer."""
    conn = setup_database()
    cursor = conn.cursor()

    now = timestamp()

    # Get the timer to start
    cursor.execute(
        """
        SELECT time_id, account_id, memo, datetime, timedelta, status
        FROM Times
        WHERE status IN ('paused', 'running', 'inactive')
        ORDER BY time_id LIMIT 1 OFFSET ?
        """,
        (position - 1,),
    )
    row = cursor.fetchone()

    if row:
        time_id, account_id, memo, start_time, timedelta, status = row
        if start_time and start_time < now - (now % 86400):  # Timer from a previous day
            # Create a new timer
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
        else:
            # Stop the currently running timer (if any)
            cursor.execute(
                """
                UPDATE Times
                SET status = 'paused', timedelta = timedelta + (? - datetime), datetime = NULL
                WHERE status = 'running'
                """,
                (now,),
            )

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


@click.command()
@click.argument("position", type=int)
def timer_pause(position):
    """Pause a timer."""
    conn = setup_database()
    cursor = conn.cursor()

    now = timestamp()

    # Get the timer to stop
    cursor.execute(
        """
        SELECT time_id, datetime
        FROM Times
        WHERE status IN ('paused', 'running')
        ORDER BY time_id LIMIT 1 OFFSET ?
        """,
        (position - 1,),
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


@click.command()
@click.argument("report_date", type=click.DateTime(formats=["%Y-%m-%d"]))
def report_week(report_date):
    """
    Generate a weekly report for the week containing REPORT_DATE (format: YYYY-MM-DD).
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
        """,
        (week_start.timestamp(), week_end.timestamp()),
    )
    week_total = cursor.fetchone()[0] or 0

    console.print(
        f"\n[bold cyan]Weekly Report[/bold cyan] ({week_start.date()} to {week_end.date()}):"
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
            """,
            (day.timestamp(), (day + datetime.timedelta(days=1)).timestamp()),
        )
        day_total = cursor.fetchone()[0] or 0
        if day_total == 0:
            continue
        # click.echo(f"{day_total = }")
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
            ORDER BY A.account_name, T.datetime
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
                f"  [yellow]{format_hours_and_tenths(timedelta)}[/yellow] [green]{datetime_str}[/green]{memo_str} [#6699ff]{account_name}[/#6699ff] "
            )

    conn.close()


@click.command()
def report_month():
    """
    Generate a monthly report for the month containing a specified date.
    Prompts for the month in YYYY-MM format.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Prompt for month (YYYY-MM format)
    session = PromptSession()
    try:
        month_input = session.prompt("Enter the month for the report (YYYY-MM): ")
        report_date = datetime.datetime.strptime(month_input, "%Y-%m")
    except ValueError:
        console.print("[red]Invalid date format! Please use YYYY-MM.[/red]")
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
        SELECT SUM(T.timedelta)
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
        SELECT A.account_name, SUM(T.timedelta)
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
            SELECT T.timedelta, T.datetime, T.memo
            FROM Times T
            JOIN Accounts A ON T.account_id = A.account_id
            WHERE A.account_name = ? AND T.datetime BETWEEN ? AND ?
            ORDER BY T.datetime
            """,
            (account_name, month_start.timestamp(), month_end.timestamp()),
        )
        timers = cursor.fetchall()

        for timedelta, datetime_val, memo in timers:
            datetime_str = datetime.datetime.fromtimestamp(datetime_val).strftime(
                "%d %H:%M"
            )
            memo_str = f" ({memo})" if memo else ""
            console.print(
                f"  [yellow]{format_hours_and_tenths(timedelta)}[/yellow] [green]{datetime_str}[/green]{memo_str}"
            )

    conn.close()


@click.command()
def report_account():
    """
    Generate a monthly report for a specific account.
    Prompts for account and optionally for a starting month.
    If no starting month is provided, generates a report for all months.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch account names for autocompletion
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
            "Enter account name: ",
            completer=completer,
            complete_while_typing=True,
        ).lower()
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    account = account_completions.get(selected_name)
    if not account:
        console.print(f"[red]Account '{selected_name}' not found![/red]")
        conn.close()
        return

    account_id, account_name = account  # Get original case account name and ID

    # Prompt for starting month (optional)
    try:
        start_date_input = session.prompt(
            "Enter starting month (YYYY-MM) (press Enter to include all months): ",
            default="",
        )
        start_date = (
            datetime.datetime.strptime(start_date_input, "%Y-%m")
            if start_date_input
            else None
        )
    except ValueError:
        console.print("[red]Invalid date format! Please use YYYY-MM.[/red]")
        conn.close()
        return
    except KeyboardInterrupt:
        console.print("[red]Cancelled by user.[/red]")
        conn.close()
        return

    # Generate report for all months if no start_date is provided
    if not start_date:
        month_str = "All months"
        cursor.execute(
            """
            SELECT MIN(datetime), MAX(datetime)
            FROM Times
            WHERE account_id = ?
            """,
            (account_id,),
        )
        date_range = cursor.fetchone()
        if not date_range or not date_range[0]:
            console.print(
                f"[yellow]No records found for account '{account_name}'.[/yellow]"
            )
            conn.close()
            return

        start_date = datetime.datetime.fromtimestamp(date_range[0])
        end_date = datetime.datetime.fromtimestamp(date_range[1])
    else:
        # Prompt for optional ending month if start_date is given
        month_str = "Selected months"
        try:
            end_date_input = session.prompt(
                "Enter ending month (YYYY-MM) (press Enter to use the same as starting month): ",
                default=start_date.strftime("%Y-%m"),
            )
            end_date = datetime.datetime.strptime(end_date_input, "%Y-%m")
        except ValueError:
            console.print("[red]Invalid date format! Please use YYYY-MM.[/red]")
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

    # Generate report
    current_date = start_date
    console.print(
        f"\n[bold cyan]{month_str} for {account_name}[/bold cyan]"
    )  # Use original case account name
    while current_date <= end_date:
        month_start = current_date.replace(day=1)
        next_month = (month_start + datetime.timedelta(days=32)).replace(day=1)
        month_end = next_month - datetime.timedelta(seconds=1)

        # Total time for the month
        cursor.execute(
            """
            SELECT SUM(T.timedelta)
            FROM Times T
            WHERE T.account_id = ? AND T.datetime BETWEEN ? AND ?
            """,
            (account_id, month_start.timestamp(), month_end.timestamp()),
        )
        month_total = cursor.fetchone()[0] or 0

        console.print(
            f"\n[bold][#6699ff]{account_name}[#6699ff] [green]{month_start.strftime('%b %Y')}[/green] - [yellow]{format_hours_and_tenths(month_total)}[/yellow][/bold]"
        )
        # console.print(f"Total: {format_hours_and_tenths(month_total)}")

        # Timers for the account in this month
        cursor.execute(
            """
            SELECT T.timedelta, T.datetime, T.memo
            FROM Times T
            WHERE T.account_id = ? AND T.datetime BETWEEN ? AND ?
            ORDER BY T.datetime
            """,
            (account_id, month_start.timestamp(), month_end.timestamp()),
        )
        timers = cursor.fetchall()

        for timedelta, datetime_val, memo in timers:
            datetime_str = datetime.datetime.fromtimestamp(datetime_val).strftime(
                "%d %H:%M"
            )
            memo_str = f" ({memo})" if memo else ""
            console.print(
                f"  [bold yellow]{format_hours_and_tenths(timedelta)}[/bold yellow] [green]{datetime_str}[/green]{memo_str}"
            )

        # Move to the next month
        current_date = next_month

    conn.close()


@click.command()
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
    Populate the Accounts and Times tables with test data.
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
    click.echo(f"{accounts = }")
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
    # click.echo(f"{times = }")

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


cli.add_command(add_account)
cli.add_command(list_accounts)
cli.add_command(add_timer)
cli.add_command(list_timers)
cli.add_command(timer_start)
cli.add_command(timer_pause)
cli.add_command(report_account)
cli.add_command(report_month)
cli.add_command(report_week)
cli.add_command(populate)
cli.add_command(archive_timers)  # New archive_timers command


def main():
    cli()


if __name__ == "__main__":
    main()
