import bisect
import datetime
import sqlite3

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def timestamp():
    return round(datetime.datetime.now().timestamp())


def find_position(lst, x):
    try:
        pos = bisect.bisect_right(lst, x)
        if pos >= 0:
            return pos
        else:
            return 0
    except Exception as e:
        click_log(f"Exception {e} raised processing {lst = } and {x =}")
        return 0


s = 1
m = 60 * s
h = 60 * m
d = 24 * h
w = 7 * d
y = 52 * w
units = [s, m, h, d, w, y]
labels = ["seconds", "minutes", "hours", "days", "weeks", "years"]


def skip_show_units(seconds: int, num: int = 1):
    pos = find_position(units, seconds)
    used_labels = labels[:pos]
    show_labels = used_labels[-num:]
    round_labels = used_labels[:-num]

    return round_labels, show_labels


def format_timedelta(total_seconds: int, num: int = 2) -> str:
    sign = ""
    if total_seconds < 0:
        sign = "-"
        total_seconds = abs(total_seconds)
    until = []
    skip, show = skip_show_units(total_seconds, num)
    # click_log(f"{skip = }; {show = }")

    years = weeks = days = hours = minutes = 0
    if total_seconds:
        seconds = total_seconds
        if seconds >= 60:
            minutes = seconds // 60
            seconds = seconds % 60
            if "seconds" in skip and seconds >= 30:
                minutes += 1
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            if "minutes" in skip and minutes >= 30:
                hours += 1
        if hours >= 24:
            days = hours // 24
            hours = hours % 24
            if "hours" in skip and hours >= 12:
                days += 1
        if days >= 7:
            weeks = days // 7
            days = days % 7
            if "days" in skip and days >= 4:
                weeks += 1
        if weeks >= 52:
            years = weeks // 52
            weeks = weeks % 52
            if "weeks" in skip and weeks >= 26:
                years += 1
    else:
        seconds = 0
    if "years" in show:
        until.append(f"{years}y")
    if "weeks" in show:
        until.append(f"{weeks}w")
    if "days" in show:
        until.append(f"{days}d")
    if "hours" in show:
        until.append(f"{hours}h")
    if "minutes" in show:
        until.append(f"{minutes}m")
    if "seconds" in show:
        until.append(f"{seconds}s")
    if not until:
        until.append("0s")
    return f"{sign}{''.join(until)}"


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


@click.group()
def cli():
    """Time Mate: A CLI Timer Manager."""
    pass


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
    table.add_column("row", justify="center", width=3, style="dim")
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
    table.add_column("memo", width=15)
    table.add_column("status", style="green", width=6)
    table.add_column("time", justify="center")

    now = round(datetime.datetime.now().timestamp())
    for idx, (time_id, account_name, memo, status, timedelta, start_time) in enumerate(
        timers, start=1
    ):
        elapsed = timedelta + (now - start_time if status == "running" else 0)
        status_color = "green" if status == "running" else "blue"
        table.add_row(
            str(idx),
            f"[{status_color}]{account_name}[/{status_color}]",
            f"[{status_color}]{memo}[/{status_color}]",
            f"[{status_color}]{status}[/{status_color}]",
            f"[{status_color}]{format_timedelta(elapsed, 2)}[/{status_color}]",
        )

    console.print(table)
    conn.close()


@click.command()
@click.argument("position", type=int)
def start_timer(position):
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
def pause_timer(position):
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
                SET status = 'paused', timedelta = timedelta + ?, datetime = NULL
                WHERE time_id = ?
                """,
                (elapsed, time_id),
            )
            conn.commit()
            console.print(f"[yellow]Timer {position} stopped![/yellow]")
    else:
        console.print("[red]Invalid position![/red]")

    conn.close()
    _list_timers()


cli.add_command(add_account)
cli.add_command(list_accounts)
cli.add_command(add_timer)
cli.add_command(list_timers)
cli.add_command(start_timer)
cli.add_command(pause_timer)

if __name__ == "__main__":
    cli()
