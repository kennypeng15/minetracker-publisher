# minetracker-publisher
Python application that scrapes local Chrome history and sends minesweeper games to an SNS endpoint

Notes:
- last-published.txt shoud contain only a string, which is the UTC timestamp of the last browser history URL sent to SNS.
- `manual-publisher.py` ignores the last published date and instead asks users directly for game URLs and timestamps.

Invocation:
- as simple as `python publisher.py`, or `python manual-publisher.py`

Considerations:
- each log group that appears (in cloudwatch) is a single execution environment: https://docs.aws.amazon.com/lambda/latest/operatorguide/log-structure.html
- we WANT more execution environments - more spread IPs = less risk of failures due to IP bans
- in that vein, we DON'T want to throttle requests by introducing sleeps between each SNS publish
- however, we don't want to inundate Lambda - we want to space out batches of requests so we have turnover in execution environments
- hence, we batch send 100 requests at a time, then sleep for 60 minutes (these values are configurable)

Progress: (i.e., last last-published date)
- As of Nov. 15, 2023:
    - 1500 items scraped, last published date 2023-08-09 04:46:30+00:00