import boto3
from browser_history.browsers import Chrome
from datetime import *
from dotenv import load_dotenv
from os.path import join, dirname
from time import sleep
import json
import os
import pytz

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

new_last_publish_date = datetime(1900, 1, 1).astimezone(pytz.utc)
# use minesweeper_chrome_history[:N] to get the first N entries
for minesweeper_game in minesweeper_chrome_history:
    # if the last published date is a more recent date than the game timestamp, skip.
    if minesweeper_game[1] <= last_published_date:
        # print("skipping: game was played at " + str(minesweeper_game[1]) + ", last published date in file is " + str(last_published_date))
        continue
    
    # print("publishing: game was played at " + str(minesweeper_game[1]) + ", last published date in file is " + str(last_published_date))

    # be sure to convert the datetime to a string here
    message_dict = {
        "game-url": minesweeper_game[0],
        "game-timestamp": str(minesweeper_game[1]),
        "failsafe": os.environ['PERSONAL_SALT']
    }
    # we have to dumps twice in order for the JSON string to be escaped as we want
    serialized_message = json.dumps(json.dumps(message_dict))
    
    # actually write to SNS
    response = topic.publish(Message=serialized_message)

    if minesweeper_game[1] > new_last_publish_date:
        new_last_publish_date = minesweeper_game[1]
    
    # sleep a couple seconds, just to make sure we don't overload anything
    print("sleeping")
    sleep(3)

# update the last_publish_date file
with open(last_published_path, 'w') as f:
    f.write(str(new_last_publish_date))
