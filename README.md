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
    - by month:   
    list times spent for a specified month grouped by month and account for all accounts
    - by account:   
    list times spent by month for a specified account with options to specify all months for the account, a range of months or a specific month

    Here is an illustration of a monthly report for the "Johnson, Noah" account. The memo field is shown in parentheses.
    ```
    Johnson, Noah Nov 2024 - 12.6h
      0.8h 02 10:42 (meeting)
      0.5h 03 12:36 (research)
      0.8h 10 14:42 (phone)
      1.1h 10 17:18 (meeting)
      1.0h 11 12:48 (research)
      0.6h 11 15:42 (travel)
      1.4h 14 14:48 (travel)
      1.4h 18 10:48 (travel)
      0.4h 24 10:42 (meeting)
      1.4h 26 12:54 (travel)
      1.0h 28 11:06 (travel)
      1.3h 29 15:24 (research)
      0.9h 30 14:48 (research)
    ```
