import datetime
import json
import math
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


# Replace @click.group() with @shell()
@shell(
    prompt="TimeMate> ",
    intro="Welcome to the Time Mate shell! Type ? or help for commands.",
)
def cli():
    """Time Mate: A CLI Timer Manager."""
    pass


# Commands remain unchanged...
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
def list_timers():
    """List active timers."""
    _list_timers()


def _list_timers():
    conn = setup_database()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT T.time_id, A.account_name, T.memo, T.status, T.timedelta, T.datetime
        FROM Times T
        JOIN Accounts A ON T.account_id = A.account_id
        WHERE T.status IN ('paused', 'running')
        """
    )
    timers = cursor.fetchall()

    table = Table(title="Timers", expand=True)
    table.add_column("row", justify="center", width=3, style="dim")
    table.add_column("account name", width=15)
    table.add_column("memo", justify="center", width=15)
    table.add_column("status", justify="center", style="green", width=6)
    table.add_column("time", justify="right")
    table.add_column("date", justify="right")

    now = round(datetime.datetime.now().timestamp())
    for idx, (time_id, account_name, memo, status, timedelta, timer_time) in enumerate(
        timers, start=1
    ):
        elapsed = timedelta + (now - start_time if status == "running" else 0)
        status_color = "green" if status == "running" else "blue"
        table.add_row(
            str(idx),
            f"[{status_color}]{account_name}[/{status_color}]",
            f"[{status_color}]{memo}[/{status_color}]",
            f"[{status_color}]{status}[/{status_color}]",
            f"[{status_color}]{format_hours_and_tenths(elapsed)}[/{status_color}]",
            # f"[{status_color}]{format_dt(start_time)}[/{status_color}]",
            f"[{status_color}]{format_dt(timer_time)}[/{status_color}]",
        )

    console.print(table)
    conn.close()


@click.command()
@click.argument("position", type=int)
def timer_start(position):
    """Start a timer."""
    conn = setup_database()
    cursor = conn.cursor()

    now = timestamp()

    # Stop the currently running timer (if any)
    cursor.execute(
        """
        UPDATE Times
        SET status = 'paused', timedelta = timedelta + (? - datetime), datetime = NULL
        WHERE status = 'running'
        """,
        (now,),
    )

    # Get the timer to start
    cursor.execute(
        """
        SELECT time_id
        FROM Times
        WHERE status IN ('paused', 'running')
        ORDER BY time_id LIMIT 1 OFFSET ?
        """,
        (position - 1,),
    )
    row = cursor.fetchone()

    if row:
        time_id = row[0]
        cursor.execute(
            """
            UPDATE Times
            SET status = 'running', datetime = ?
            WHERE time_id = ?
            """,
            (now, time_id),
        )
        conn.commit()
        console.print(f"[green]Timer {position} started![/green]")
    else:
        console.print("[red]Invalid position![/red]")

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
        console.print(
            f"\n[bold]Day: {day.date()}[/bold] - Total Time: [yellow]{format_hours_and_tenths(day_total)}[/yellow]"
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
                "%y-%m-%d %H:%M"
            )
            memo_str = f" ({memo})" if memo else ""
            console.print(
                f"  [yellow]{format_hours_and_tenths(timedelta)}[/yellow] [#6699ff]{account_name}[/#6699ff] @ [green]{datetime_str}[/green]{memo_str}"
            )

    conn.close()


@click.command()
@click.argument("report_date", type=click.DateTime(formats=["%Y-%m-%d"]))
def report_month(report_date):
    """
    Generate a monthly report for the month containing REPORT_DATE (format: YYYY-MM-DD).
    """
    conn = setup_database()
    cursor = conn.cursor()

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
        f"\n[bold cyan]Monthly Report[/bold cyan] ({month_start.date()} to {month_end.date()}):"
    )
    console.print(
        f"Total Time: [yellow]{format_hours_and_tenths(month_total)}[/yellow]"
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
            f"\n[bold]{account_name}[/bold] - Total Time: [yellow]{format_hours_and_tenths(account_total)}[/yellow]"
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
                "%y-%m-%d %H:%M"
            )
            memo_str = f" ({memo})" if memo else ""
            console.print(
                f"  [yellow]{format_hours_and_tenths(timedelta)}[/yellow] @ [green]{datetime_str}[/green]{memo_str}"
            )

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
cli.add_command(report_month)
cli.add_command(report_week)
cli.add_command(populate)

if __name__ == "__main__":
    cli()
