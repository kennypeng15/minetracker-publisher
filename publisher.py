import boto3
from browser_history.browsers import Chrome
from dotenv import load_dotenv
from os.path import join, dirname
import pytz

# load necessary environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

print("Scanning Chrome history...")

# get the browser history
c = Chrome()
outputs = c.fetch_history()

# his is a list of (datetime.datetime, url) tuples
his = outputs.histories
minesweeper_chrome_history = []

# be sure to convert everything to a UTC timestamp
for history_item in his:
    if "minesweeper.online/game/" in history_item[1]:
        minesweeper_chrome_history.append((history_item[1], str(history_item[0].astimezone(pytz.utc)))) # this is now UTC, and as a string instead of python datetime

print("Finished scanning browser history complete.")
print("Found " + str(len(minesweeper_chrome_history)) + " minesweeper games in local Chrome history.")