# minetracker-publisher
## Summary and Design
---
A suite of python applications that scans local Chrome history for minesweeper.online games,
with the ultimate goal of sending game URLs and the timestamps at which they were accessed to an 
AWS Lambda function (via an SNS endpoint).

`publisher.py` is the primary application. It uses the `browser_history` python library to access local Chrome history,
searches for entries in history corresponding to minesweeper.online games, and sends them to an SNS endpoint (invoking a Lambda) using `boto3`.
Differential crawling exists, in the sense that `publisher.py` writes the timestamp of the last history entry it has sent
to SNS to the `last-published.txt` file; all history entries with access timestamps earlier than what's in this file are ignored.
`publisher.py` is not designed to send all matching entries in history at once. Instead, evenly sized batches of URLs and timestamps
are sent at regular intervals; the rationale for doing so is discussed later.

`check.py` contains a simple validation script, designed to make sure that minesweeper.online is available and that 
the Lambda function invoked by the SNS endpoint is behaving as expected. 
This is achieved by copying over the scraping and processing code used in the `minetracker-lambda` (https://github.com/kennypeng15/minetracker-lambda) project and using that code to
scrape a known valid minesweeper.online game, comparing values to expectations.
`check.py` is thus designed to be run as a precursor to `publisher.py`.

`manual-publisher.py` is a manual counterpart to `publisher.py`, in the sense that it prompts the user to input
a minesweeper.online game URL and the time it was accessed, rather than scanning for that information in local browser history.
The information is still sent to an SNS endpoint, invoking a Lambda.
`manual-publisher.py` is intended to be used in the rare case that a minesweeper.online game ends up in the Lambda's
corresponding SQS deadletter queue even though manual inspection reveals it has valid data.


## Invocation
---
The recommended workflow is to invoke `python check.py` first.

If console output indicates success, invoke `python publisher.py` or `python manual-publisher.py` and 
follow console instructions / prompts.

If not successful, debugging the scraping code in `check.py` or verifying minesweeper.online is online may be necessary.


## Configuration
---
- `last-published.txt` shoud contain only a string, which is the UTC timestamp of the last browser history URL sent to SNS.
    - This is only considered when using `publisher.py`.
    - `manual-publisher.py` ignores the last published date and instead asks users directly for game URLs and timestamps.
- A `.env` file is expected.
- Batch size and send rate can be configured with the `BATCH_SIZE` and `SLEEP_DELAY_IN_MINUTES` variables in `publisher.py`, respectively.
    - More discussion on these two variables below.

## Monitoring and Rationale
---
We want to avoid the problem of IP bans (i.e., too many scraping requests from the same IP address in Lambda).

Although Lambda environments are ephemeral, they stay online for some time, and continuously sending requests can lead to 
a single environment (and thus a single IP) trying to scrape many times in sequence, which many lead to a temporary IP ban and thus data loss.
As such, we don't want to inundate Lambda/SNS; we instead send batches (default size of 100) of requests at once, then sleep a set amount of time
(default 45 minutes) between each batch.

Lambda's default concurrency limit (i.e., how many distinct Lambda environments can be spun up at once) is 10; with batch size of 100 requests,
this averages out to each environment/each IP address only making 10 scrapes, which carries little risk of an IP ban.

45 minutes is on the safe end of a delay; empirical testing has shown in my case that no Lambda environment will stay open for 45 minutes
when no requests are being sent, meaning at the end of the 45 minute delay, a whole new set of 10 Lambda execution environments (and thus 10 new IPs)
will be used.

This can be monitored in CloudWatch: each log group that appears is a single execution environment
(https://docs.aws.amazon.com/lambda/latest/operatorguide/log-structure.html).


## Future Work and Ideas:
---
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

## Progress (i.e., last last-published date)
---
As of Jan. 4, 2024:
- 10600 entries published; last published date 2023-09-14 22:57:28+00:00