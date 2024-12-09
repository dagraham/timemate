# For Chat

I have some startup questions for a new application. Here is the basic setup:
- Tables
    - Accounts
        - account_name (unique): str
        - account_id (index, unique): int

    - Times 
        - account_id: int (lookup in Accounts)
        - timedelta: int (seconds)
        - datetime: int (seconds since epoch)

The idea is that each time record would represent a timedelta and datetime "charged" to a particular account record.

Here are the questions
    - sqlite3 many_to_one setup for the Times and Accounts Tables?
    - When creating a Times record, how to do LIKE based tab completion on account_names so that, e.g., entering "ill" when creating a new Times record would use "%ill% to produce a popup list of LIKE matches including, say, "Bill", "Will" and "William". Pressing Tab would cycle among the matches, changing the entry to "illi" would remove "Bill" and "Will" from the list of matches and pressing Return would accept the current selection, creating the corresponding record in Accounts, if necessary, and return the corresponding account_id.


This approach isn't quite correct for my application. I would like to be able to issue other commands than just the one to record a time. These would include, add_account, list_accounts, add_timer, list_timers, .... The idea with the times records is to be able to initiate a time record with an account id, thus an associated account name, and a status = 'paused'. Timedelta and Datetime entries would both be None. A command, active_timers, would show all time records for which the status is either "paused" or "running".  Another command, start_timer, would have a single argument corresponding to the row number of the relevant timer in the active_timers list. It would do the following:
1) if another active timer has the status "running", first invoke the command "stop_timer" with it's row number (more on stop_timer below) on the other timer.
2)


This approach isn't quite correct for my application. The normal usage is not to create a complete time record but instead to initiate what amounts to a timer. Here are the relevant commands:

add_account: create a record in Accounts with a unique name and id

list_accounts: list accounts in a rich table with an initial position/row number that is associated with the account_id of the corresponding record.

add_timer: display list_accounts and prompt to select the position number of an existing account or the name of a new account. Create a record in Times using the provided account name/id with status = 'paused', timedelta = 0 and datetime = None. 

list_timers: list times records for which the status is 'paused' or 'running' in a rich table with an initial position/row number that is associated with the id of the associated times record. 

start_timer: called with the position number of the relevant timer from list timers. If another timer is running, first stop it (details below), then set the status to 'running', datetime = now() where now() = round(datetime.datetime.now().timestamp()). At most one timer can be active - color it, say green, in list_timers.

stop_timer: called with the position number of the relevant timer from list timers. Set status = 'paused', timedelta += (now() - datetime)

Since the accounting for time records is based on the date, a timer cannot persist beyond the date on which it was created. Accordingly, whenever the app is run, if a time record has either running or stopped as it's status, 






