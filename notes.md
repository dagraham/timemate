# ToDo

- [ ] Add memo 


# Chat

- [x] Add a method "archive_timers" to set the status to "inactive" for all timers with "datetime" entries < 00:00 hours on the current date. It would be nice if this command could be executed automatically when any command is executed for the first time in a new day. 

- [x] In list_timers provide an option to include all timers, i.e., timers with any status in ('inactive', 'running', 'paused'), but make the default only to show timers with status in ('running', 'paused'). 

- [x] Make the "start_date" optional in "report-account". When not given, do not prompt for end_date and create report for all months

- [ ] Add "details" to Account? Or another related Table with fields for phone, email, address, ...? Or perhaps nothing?

- [ ] rename_account: argument row. Prompt for changes with old_name as default.  

- [ ] update_time: argument row. options name, memo, status?, datetime, timedelta  

- [ ] Don't automatically archive_timers, but have a command to make inactive a selected one. When timer-start is called with a paused timer for which the start_time is less than the current date, create a copy of the timer with the current datetime as the start_time and 0 as the timedelta.
