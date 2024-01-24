import boto3
from browser_history.browsers import Chrome
from datetime import *
from dotenv import load_dotenv
from os.path import join, dirname
from time import sleep
import json
import os
import pytz
import sys

# load necessary environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# create the SNS connection
# environment variables handle configuration
# clever workaround: https://stackoverflow.com/questions/71088521/how-can-i-get-the-sns-topic-arn-using-the-topic-name-to-publish-a-sns-message-in
# creating a topic with boto3 is idempotent, so we can get the existing topic by calling with an existing name
sns = boto3.resource('sns')
topic = sns.create_topic(Name=os.environ['SNS_TOPIC_NAME'])

# get the browser history
print("Scanning Chrome history...")
c = Chrome()
outputs = c.fetch_history()

# his is a list of (datetime.datetime, url) tuples
his = outputs.histories
minesweeper_chrome_history = []
for history_item in his:
    if "minesweeper.online/game/" in history_item[1]:
        # be sure to convert to UTC, to avoid timezone headaches.
        # we leave as a datetime object for ease of comparison; we'll convert to a string later
        minesweeper_chrome_history.append((history_item[1], history_item[0].astimezone(pytz.utc)))

print("Finished scanning browser history complete.")
print("Found " + str(len(minesweeper_chrome_history)) + " minesweeper games in local Chrome history.")
print("Earliest date: " + str(min(minesweeper_chrome_history, key=lambda t: t[1])[1]))
print("Latest date: " + str(max(minesweeper_chrome_history, key=lambda t: t[1])[1]))

# read in the last-published file
# if it doesn't exist, create it and populate it at the end of execution. use the minimum date as the last published date.
# if it exists, but doesn't have a value, use the minimum date as the last published date. update the file at the end of execution.
# if it exists and does have a value, use that value, and update the file at the end of execution.
last_published_exists = False
last_published_date = datetime(1900, 1, 1).astimezone(pytz.utc)
last_published_path = join(dirname(__file__), 'last-published.txt')
if os.path.exists(last_published_path) and os.path.isfile(last_published_path):
    last_published_exists = True

if last_published_exists:
    with open(last_published_path) as f:
        s = f.read()
        s.strip
        if s:
            last_published_date = datetime.strptime(s, '%Y-%m-%d %H:%M:%S%z').astimezone(pytz.utc)

# filter down the history to just entries where the timestamp is newer than the last published date
# minesweeper_chrome_history is already sorted to begin with (earliest entries come first), so no need to worry about sorting
# TODO: consider if this should be >=
# there is a possibility that two games share the same access time in history
filtered_minesweeper_chrome_history = [h for h in minesweeper_chrome_history if h[1] > last_published_date]
filtered_length = len(filtered_minesweeper_chrome_history)

# if there aren't any entries in the filtered list, return, since there's nothing to do
if filtered_length <= 0:
    print("No new entries to publish. Terminating.")
    # exit code 0 to indicate success
    sys.exit(0)

# print some helpful information, and ask for confirmation before proceeding
print("The last published entry's date is " + str(last_published_date) + ".")
print("There are " + str(filtered_length) + " minesweeper game entries in Chrome history that haven't been published.")
start_confirmation = input("Proceed? (y/n): ")
if start_confirmation.strip().lower() != "y":
    print("Confirmation was not supplied. Terminating.")
    sys.exit(0)
print("Confirmation supplied. Asking more questions...")

# variables that control batch size and sleep duration
SLEEP_DELAY_IN_MINUTES = 45
BATCH_SIZE = 100

# this one shouldn't technically be configured here - users will be prompted by the
# program before running if they want to manually confirm
prompt_for_continue = True

# prompt user - ask if they want to manually confirm between batches
while(True):
    need_between_batch_confirmation = input("Do you want to have to manually enter confirmation between each batch? (y/n): ")
    processed_batch_confirmation = need_between_batch_confirmation.strip().lower()
    if (processed_batch_confirmation == "y" or processed_batch_confirmation == "n"):
        break
    else:
        print("Unrecognized input, please try again.")
if (processed_batch_confirmation == "n"):
    prompt_for_continue = False
    print("User will not have to re-enter confirmation between batches. Program can be safely terminated between batches. Proceeding...")
else:
    print("User will have to re-enter confirmation between batches. Proceeding...")

# confirm one more time
print(f"Requests will be sent {BATCH_SIZE} at a time, with a {SLEEP_DELAY_IN_MINUTES} minute delay between each batch.")
if prompt_for_continue:
    print("User will be required to re-confirm between every batch.")
else:
    print("User will not have to confirm between batches.")
start_confirmation = input("Proceed? (y/n): ")
if start_confirmation.strip().lower() != "y":
    print("Confirmation was not supplied. Terminating.")
    sys.exit(0)

# instantiate variables to keep track of the last date we've published in this session,
# and track how many games we've published this session
new_last_publish_date = datetime(1900, 1, 1).astimezone(pytz.utc)
count = 0
try:
    for minesweeper_game in filtered_minesweeper_chrome_history:
        # print information about what we're publishing
        print("publishing: game was played at " + str(minesweeper_game[1]) + ", last published date prior to this session is " + str(last_published_date))

        # build the message to publish, and actually send it
        message_dict = {
            "game-url": minesweeper_game[0],
            "game-timestamp": str(minesweeper_game[1]),
            "failsafe": os.environ['PERSONAL_SALT']
        }
        serialized_message = json.dumps(message_dict)
        response = topic.publish(Message=serialized_message)

        # increment variables
        count = count + 1
        if minesweeper_game[1] > new_last_publish_date:
            new_last_publish_date = minesweeper_game[1]

        # batch control - we don't want to inundate lambda, so we delay after batches
        # can consider using publish_batch boto3 ...
        if count % BATCH_SIZE == 0:
            print("Batch of " + str(BATCH_SIZE) + " games has been published. Writing an updated last publish date to file.")
            with open(last_published_path, 'w') as f:
                f.write(str(new_last_publish_date))
            print(str(count) + " games in total have been published this session, out of " + str(filtered_length) + " in (filtered) history.")

            # change this to accoount for prompt_for_continue
            print("Sleeping for " + str(SLEEP_DELAY_IN_MINUTES) + " minutes.")
            print("Current time: " + str(datetime.now()))
            print("Resuming time: " + str(datetime.now() + timedelta(minutes=SLEEP_DELAY_IN_MINUTES)))
            if prompt_for_continue:
                print("User will be prompted to resume after sleeping.")
            else:
                print("Program will resume execution automatically.")
            print("At any time during sleeping, CTRL+C can be used to safely exit the program.")
            sleep(60 * SLEEP_DELAY_IN_MINUTES)

            # still prompt for user confirmation, just as a failsafe; this can be overridden by changing 
            # the value for prompt_for_continue.
            if prompt_for_continue:
                continue_confirmation = input("Resumed. Continue publishing? (y/n): ")
                if continue_confirmation.strip().lower() != "y":
                    print("Confirmation was not supplied. Terminating.")
                    sys.exit(0)
                else:
                    print("Confirmation was supplied. Proceeding.")
            else:
                print("Resumed. Continuing immediately.")

except KeyboardInterrupt:
    # newline, purely for aesthetics since on some systems CTRL + C shows up as a character on the terminal
    print("")
    print("Keyboard interrupt registered. " + str(count) + " total entries were published this session.")
    print("Writing updated last published date to file and terminating.")
    with open(last_published_path, 'w') as f:
        f.write(str(new_last_publish_date))
    sys.exit(0)

# do a final update of the last publish date before finishing execution.
print("Finished publishing entries in history. " + str(count) + " total entries were published this session.")
print("Writing updated last published date written to file and terminating.")
with open(last_published_path, 'w') as f:
    f.write(str(new_last_publish_date))
