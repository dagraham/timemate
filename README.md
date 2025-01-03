```
         ████████╗██╗███╗   ███╗███████╗███╗   ███╗ █████╗ ████████╗███████╗ 
         ╚══██╔══╝██║████╗ ████║██╔════╝████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
            ██║   ██║██╔████╔██║█████╗  ██╔████╔██║███████║   ██║   █████╗ 
            ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██╔══██║   ██║   ██╔══╝ 
            ██║   ██║██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
            ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
```
This is the *TimeMate* user manual.  It is best viewed at [GitHub.io](https://dagraham.github.io/timemate/). 

The first step in conserving a scare resource is tracking its use. *TimeMate*'s purpose is to do just that for your precious time. The general idea is to maintain a list of accounts on which important amounts of time might be spent together with a means of easily starting and stopping timers to charge times spent against these accounts.  

*TimeMate* provides both CLI and Shell interfaces with methods for

- creating *accounts*:  
Each account could be the name of an *activity* or a *client* that occupies your time and for which a record would be useful.
- creating *timers* for an account:  
Each timer provides an option for entering a "memo" as well as the account name and provides a record of both the duration and the date-time for the time spent.
- listing, starting and pausing timers:  
When another timer is running, automatically pause the other timer, record time spent and then starts the new timer.
        ![list, start and pause timers](./png/list_start_pause.png)
- reporting times spent. Times are aggregated by account and date and reported using the setting `SECONDS`. Here `SECONDS=360` which causes all times to be rounded up to the nearest 360 seconds = 6 minutes or 1/10 of an hour.
  - by week:  
    times spent by day for a specified week for all accounts listed by day
    ![report-week](./png/week.png)
  - by account:  
    times spent for specified account(s) and month(s) listed by month, account and day
    ![report-account](./png/monthly.png)
  - by account tree:  
    aggregates of times spent for specified account(s) and month(s) in a tree diagram by month and account
    ![report-acount --tree](./png/tree.png)
- another example of times spent this time for *activities* instead of clients and with `MINUTES=1` which causes all times to be rounded up to the nearest minute and reported in hours and minutes. Note that with the '/' in the account names, the second parts of the names are treated as branches of the first part in the tree display.
    ![path account names](./png/path_accounts.png)

## Details

Entering `timemate` without any arguments at the command prompt in a terminal will start the shell version of the interface which repeatedly cycles through these familiar steps:
1. presents a display
2. waits for your input
3. responds appropriately to your input
4. presents an updated display

Here the shell has been started, a '?' has been entered at the *TimeMate>* prompt and return has been pressed. The resulting display is a list of the available commands:
> 

    TimeMate> ?

    Documented commands (type help <topic>):
    ========================================
    account-delete  info            report-week    timer-delete  timer-start   tp
    account-list    populate        set-home       timer-list    timer-update  ts
    account-merge   report-account  set-minutes    timer-new     tl
    account-new     report-month    timer-archive  timer-pause   tn


There are two ways of creating an account:

- account-new:  
  prompts for account name and displays list of close matches while entering name to insure that the name is unique
- timer-new:  
  prompts for account name and, similarly, offers tab completion. Will create a new account if the name is unique

There are two alternative ways of creating a timer:

- timer-new:  
  prompts for account name and offers tab completion. Then prompts for optional memo, elapsed time and datetime fields while providing defaults for each
- timer-start:  
  prompts for a position (row number) from the timer-list (tl) display. If the datetime for the selected timer is not within the current date, then a copy of the timer will be created using the original values of the account name and memo but with the current datetime. Times are not only charged against a particular account but also against a particular date - times recorded on a date are charged against that date.

In addition to *timer-start* which uses the times at which the timer is started and paused to record time, it is also possible to record times manually using either *timer-new* or *timer-update*, both of which offer the opportunity to directly enter the elapsed time and datetime recorded. 

## Nickle and Dime Billing

One of the reasons for rounding times up concerns the need in billing to have amounts that can be expressed in dollars and cents. Suppose for a moment that times are rounded up to the nearest 1/100 hour = 36 seconds and the billing rate is some multiple of 1/100 dollars. Then the smallest bill would be for 36 seconds and the smallest amount would be $0.01, with an implied billing rate of 1 penny per 36 seconds. Whatever the billing rate, as long as it is an integer number of cents per 36 seconds, the resulting bill will be an integer number of cents. Rounding up to 36 seconds, moreover, is the minimum number of seconds for which this is true. The general relationship is in the table below. If times are rounded up to *interval* and if the billing rate is some integer multiple of *billing*, then the total bill must also be an integer multiple of *billing*.


| Interval (seconds) |  Billing (per interval)  |
|:------------------:|:------------------------:| 
| 36                 | 1  (penny)               |
| 180                | 5  (nickle)              | 
| 360                | 10 (dime)                |
| 540                | 15 (nickle and dime)     | 
| 720                | 20 (2 dime)              | 
| 900                | 25 (quarter)             |
| 1800               | 50 (half-dollar)         |
| 3600               | 100 (dollar)             |

  

## Installation

TimeMate can be installed from PyPi using either `pip install timemate` or, for personal use, `pipx install timemate`. For updates use either `pip install --force timemate` or `pip install -U timemate`.  It is also available from [GitHub](https://github.com/dagraham/timemate).

If the JSON file `~/timemate_config` exists and specifies a path for `TIMEMATEHOME`, it will be used as the home directory for TimeMate. Otherwise, if there is an environmental setting for `TIMEMATEHOME` then the path specified by that setting will be used. Finally, the directory `~/.timemate_home/` will be used as the home directory and created if necessary. The sqlite3 database, `timemate.db`, will be stored in this directory along with backup and log files.
