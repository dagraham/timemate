#! /usr/bin/env python3
import json
import random
import sys
from datetime import date, datetime, timedelta
from typing import Union

import lorem

num_accounts = 9
onehour = 60 * 60  # in seconds
oneday = 24 * onehour  # in seconds
# now = round(datetime.now().timestamp())
# times = [x for x in range(oneday, 10 * oneday, onehour)]
timers_per_day = [2, 3, 4, 5]
length_timer = []

names = [
    "Johnson, Noah",
    "Williams, Oliver",
    "Brown, James",
    "Jones, Theodore",
    "Miller, Henry",
    "Davis, Lucas",
    "Smith, William",
]

accounts = []
for name in names:
    accounts.append({"account_name": name})

memos = ["phone", "meeting", "research", "travel"]

DAY = timedelta(days=1)


def begMonth(dt: datetime):
    """Return the first day of the month of the provided datetime."""
    return datetime.strptime(dt.strftime("%Y-%m") + "-01", "%Y-%m-%d")


def prevMonth(dt: datetime):
    """Return the first day of the previous month of the provided datetime."""
    active_month = dt.strftime("%Y-%m")
    dt = begMonth(dt) - DAY
    return begMonth(dt)


last_date = datetime.now()
start_date = prevMonth(prevMonth(begMonth(last_date)))

# month_days = {
#     1: 31,
#     2: 28,
#     3: 31,
#     4: 30,
#     5: 31,
#     6: 30,
#     7: 31,
#     8: 31,
#     9: 30,
#     10: 31,
#     11: 30,
#     12: 31,
# }

start_minutes = 9 * 60  # 09:00H
end_minutes = 17 * 60  # 17:00H

idle_minutes = [x for x in range(12, 91, 6)]
timer_minutes = [x for x in range(24, 85, 6)]

# today = date.today()
# this_year = today.year
# this_month = today.strftime("%Y-%m")
# this_day = today.day
#
# if this_month >= 3:
#     months = [
#         (this_year, this_month - 2),
#         (this_year, this_month - 1),
#         (this_year, this_month),
#     ]
# elif this_month >= 2:
#     months = [(this_year - 1, 12), (this_year, this_month - 1), (this_year, this_month)]
# else:
#     months = [(this_year - 1, 11), (this_year - 1, 12), (this_year, this_month)]
#
# num_days = month_days[months[0]] + month_days[months[1]] + this_day

times = []

dt = start_date
while dt < last_date:
    num_timers = random.choice(timers_per_day)
    start = dt + timedelta(minutes=start_minutes)
    for timer in range(num_timers):
        memo = random.choice(memos)
        account_name = random.choice(names)
        account_id = names.index(account_name)
        start += timedelta(minutes=random.choice(idle_minutes))
        extent = timedelta(minutes=random.choice(timer_minutes))
        start += extent
        times.append(
            {
                "account_name": account_name,
                "memo": memo,
                "timedelta": round(extent.total_seconds()),
                "datetime": round(start.timestamp()),
            }
        )

    dt += DAY

data = {"accounts": accounts, "times": times}

print(data)


"""
{
  "accounts": [
    {"name": "Work"},
    {"name": "Exercise"}
  ],
  "times": [
    {"account_name": "Work", "memo": "Meeting", "timedelta": 3600, "datetime": 1672444800}
  ]
}
"""


def make_examples(egfile: str):
    if egfile:
        with open(egfile, "w") as json_file:
            json.dump(data, json_file, indent=3)

    return data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        egfile = sys.argv.pop(1)
    else:
        egfile = None

    res = make_examples(egfile)
    for _ in res:
        print(_)
