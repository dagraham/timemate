import datetime
import sqlite3

import click
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def setup_database():
    conn = sqlite3.connect("time_mate.db")  # Use a persistent SQLite database
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Accounts (
                        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_name TEXT NOT NULL UNIQUE)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Times (
                        time_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        status TEXT CHECK(status IN ('paused', 'running')) DEFAULT 'paused',
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
            "INSERT INTO Accounts (account_name) VALUES (?)", (account_name,)
        )
        conn.commit()
        console.print(f"[green]Account '{account_name}' added successfully![/green]")
    except sqlite3.IntegrityError:
        console.print(f"[red]Account '{account_name}' already exists![/red]")
    conn.close()


@click.command()
def list_accounts():
    """List all accounts."""
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()
    table = Table(title="Accounts", expand=True)
    table.add_column("row", justify="center", width=3, style="dim")
    table.add_column("Account Name", style="cyan")
    for idx, (account_id, account_name) in enumerate(accounts, start=1):
        table.add_row(str(idx), account_name)
    console.print(table)
    conn.close()


@click.command()
@click.argument("selection", required=False)
def add_timer(selection):
    """
    Add a timer. SELECTION can be a position number of an existing account or a new account name.

    If SELECTION is not provided, the list of accounts will be displayed, and the user will be prompted.
    """
    conn = setup_database()
    cursor = conn.cursor()

    # Fetch and display the list of accounts
    cursor.execute("SELECT account_id, account_name FROM Accounts")
    accounts = cursor.fetchall()

    if not accounts:
        console.print(
            "[yellow]No accounts found. Please add an account first![/yellow]"
        )
        conn.close()
        return

    table = Table(title="Accounts", expand=True)
    table.add_column("Position", justify="right")
    table.add_column("Account Name", style="cyan")
    for idx, (account_id, account_name) in enumerate(accounts, start=1):
        table.add_row(str(idx), account_name)
    console.print(table)

    # Prompt the user for input if SELECTION is not provided
    if not selection:
        selection = Prompt.ask("Enter account position or new account name")

    # Handle position-based selection
    if selection.isdigit():
        position = int(selection)
        if 1 <= position <= len(accounts):
            account_id = accounts[position - 1][0]
        else:
            console.print("[red]Invalid position![/red]")
            conn.close()
            return
    else:
        # Handle new account creation
        account_name = selection
        cursor.execute(
            "INSERT INTO Accounts (account_name) VALUES (?)", (account_name,)
        )
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
        status_color = "green" if status == "running" else "red"
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

    now = round(datetime.datetime.now().timestamp())

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

    now = round(datetime.datetime.now().timestamp())

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
