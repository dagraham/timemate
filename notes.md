# Forget me nots

## setup.py and friends

`python setup.py check`

`python setup.py sdist bdist_wheel`

`sqlite3 time_mate.db .dump > backup.sql  # Backup
sqlite3 time_mate.db < backup.sql       # Restore`

# ToDo

- [ ] Add memo 


# Chat

- [x] Add a method "archive_timers" to set the status to "inactive" for all timers with "datetime" entries < 00:00 hours on the current date. It would be nice if this command could be executed automatically when any command is executed for the first time in a new day. 

- [x] In list_timers provide an option to include all timers, i.e., timers with any status in ('inactive', 'running', 'paused'), but make the default only to show timers with status in ('running', 'paused'). 

- [x] Make the "start_date" optional in "report-account". When not given, do not prompt for end_date and create report for all months

- [ ] Add "details" to Account? Or another related Table with fields for phone, email, address, ...? Or perhaps nothing?

- [ ] rename_account: argument row. Prompt for changes with old_name as default. Avoid duplicates

- [x] update_time: argument row. options account_name, memo, status?, datetime, timedelta  

- [ ] allow range of weeks in report-week with prompt like report-month

- [x] allow fuzzy (%LIKE%) matches in report-account

- [x] Don't automatically archive_timers, but have a command to make inactive a selected one. When timer-start is called with a paused timer for which the start_time is less than the current date, create a copy of the timer with the current datetime as the start_time and 0 as the timedelta.



- [x] User errors
    - An account should actually be regarded as the same as another account. Merge?

- [x] setup.py


I need 

def str_to_seconds(time_str: str)->int:
    """
    Takes a string composed of integers joined by characters from 'd', 'h', 'm' and 's' and returns 
    the corresponding number of seconds as the sum of integer preceeding 's' plus the integer preceeding 'm' times 60 
    plus the integer preceeding h times 60 times 60 plus the integer preceeding d times 24 times 60 times 60. E.g.,
    '3h15s' = 3 * 60 * 60 + 15 = 10815. 
    """

I also need a function that takes a string representing a datetime and parses it using parse and parserinfo from dateutil.parser with these
parserinfo settings: dayfirst = False, yearfirst = True. It should return the corresponding datetime in integer seconds since the epoch.
I would like the datetime to be interpreted as aware in the local timezone of the computer but, if possible, also to be able to specify  
an optional timezone, such as 'US/Pacific' to interpret the datetime as aware but in the specified timezone.

def str_to_datetime(datetime_str: str)->int:
    """
    Takes a string such as "10pm Thu" and returns in integer number of seconds representing the corresponding
    datetime in seconds since the epoch.
    """
