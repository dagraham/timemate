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


def setup_database():
    conn = sqlite3.connect("time_mate.db")  # Use a persistent SQLite database
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Accounts (
                        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_name TEXT NOT NULL UNIQUE,
                        pinned INTEGER DEFAULT 0,
                        datetime INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Times (
                        time_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        description TEXT, 
                        status TEXT CHECK(status IN ('paused', 'running', 'ended')) DEFAULT 'paused',
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
            "INSERT INTO Accounts (account_name, pinned, datetime) VALUES (?, ?, ?)",
            (account_name, 0, timestamp()),
        )
        conn.commit()
        console.print(f"[green]Account '{account_name}' added successfully![/green]")
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
    cursor.execute("SELECT account_id, pinned, account_name FROM Accounts")
    accounts = cursor.fetchall()
    table = Table(title="Accounts", expand=True)
    table.add_column("row", justify="center", width=3, style="dim")
    table.add_column("pinned", width=3)
    table.add_column("account name", style="cyan")
    for idx, (account_id, pinned, account_name) in enumerate(accounts, start=1):
        table.add_row(str(idx), str(pinned), account_name)
    console.print(table)
    conn.close()


@click.command()
def add_timer():
    """
    Add a timer. Use fuzzy autocompletion to select or create an account.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch all account names and positions for autocompletion
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()

    # Create a mapping of position and account names to account IDs
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

    # Add the timer
    cursor.execute(
        "INSERT INTO Times (account_id, status, timedelta, datetime) VALUES (?, 'paused', 0, NULL)",
        (account_id,),
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
        SELECT T.time_id, A.account_name, T.status, T.timedelta, T.datetime
        FROM Times T
        JOIN Accounts A ON T.account_id = A.account_id
        WHERE T.status IN ('paused', 'running')
        """
    )
    timers = cursor.fetchall()

    table = Table(title="Timers", expand=True)
    table.add_column("row", justify="center", width=3, style="dim")
    table.add_column("Account Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Total Time (seconds)", justify="right")

    now = round(datetime.datetime.now().timestamp())
    for idx, (time_id, account_name, status, timedelta, start_time) in enumerate(
        timers, start=1
    ):
        elapsed = timedelta + (now - start_time if status == "running" else 0)
        status_color = "green" if status == "running" else "blue"
        table.add_row(
            str(idx),
            account_name,
            f"[{status_color}]{status}[/{status_color}]",
            str(elapsed),
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
def stop_timer(position):
    """Stop a timer."""
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
            console.print(f"[green]Timer {position} stopped![/green]")
    else:
        console.print("[red]Invalid position![/red]")

    conn.close()
    _list_timers()


cli.add_command(add_account)
cli.add_command(list_accounts)
cli.add_command(add_timer)
cli.add_command(list_timers)
cli.add_command(start_timer)
cli.add_command(stop_timer)

if __name__ == "__main__":
    cli()
