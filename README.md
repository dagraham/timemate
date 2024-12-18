# Time Mate

*TimeMate* is intended to help you keep track of where your time goes. It provides both a CLI and Shell interface with methods for

- creating an *account*:   
The account could be the name of an *activity* or a *client* that occupies your time and for which a record would be useful. 
- creating a *timer* for an account:   
The timer provides an option for entering a "memo" as well as the account name and keeps a record of both the duration and the datetime for the time spent.
- starting and pausing a timer:  
Automatically updates the timer for time spent and, when starting a timer on a new day, automatically creates a copy of the original timer for the new date. 
- reporting times spent:  
    - by week:  
    list times spent by day for a specified week for all accounts
    ![report-week](./png/week.png)
    - by account:   
    list times spent for specified account(s) and month(s)
    ![report-account](./png/monthly.png)
    - by account tree:   
    display aggregates of times spent for specified account(s) and month(s) in a tree diagram
    ![report-acount --tree](./png/tree.png)

    These reports reflect the setting `MINUTES=6` which causes all times to be rounded up to the nearest 6 minutes or 1/10 of an hour.

