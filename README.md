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

Ideas:
- if two entries in history have the same access time, its possible to skip some entries
- scenario: entry 100 at 1/1/1 12:00:00, entry 101 at 1/1/1 12:00:00
    - batch size 100 - stop executing after entry 100
    - last pubished date is 1/1/1 12:00:00, and since we have the strictly greater than operator, entry 101 will be skipped
    - solutions:
        - use greater than or equal to operator during comparisons - easy, but may lead to some re-processing (fine?)
        - seek forward in history; if the timestamp of the next entry is equal to the current timestamp at the end of a batch, process that as well. repeat
            - complicated!
            - may be best just to use geq ...
- TODO: add a print statement that says that, at any time while the program is sleeping, CTRL + C can be used to safely stop execution.
- TODO: add a local python program (local-scraper.py) that basically has just the content of the lambda, that can be run locally in case anything breaks.
    - perhaps this should be run (tested?) locally, before a publisher batch, to ensure that the lambda is functioning as desired.

Progress: (i.e., last last-published date)
- As of Dec. 20, 2023:
    - 8500; last published date 2023-09-13 21:22:11+00:00