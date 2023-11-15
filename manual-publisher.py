import boto3
from datetime import *
from dotenv import load_dotenv
from os.path import join, dirname
import json
import os
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

while(True):
    game_url = input("Enter the URL of the minesweeper game you want to publish: ")
    game_timestamp = input("Enter the timestamp that the URL entered was accessed: ")

    stripped_game_url = game_url.strip()
    stripped_game_timestamp = game_timestamp.strip()

    print("Please confirm the inputs you supplied: ")
    print("Game URL: " + stripped_game_url)
    print("Game timestamp: " + stripped_game_timestamp)
    publish_confirmation = input("Proceed? (y/n): ")

    if publish_confirmation.strip().lower() != "y":
        print("Confirmation was not supplied. Terminating.")
        sys.exit(0)
    else:
        print("Confirmation was supplied. Proceeding.")

    message_dict = {
        "game-url": stripped_game_url,
        "game-timestamp": stripped_game_timestamp,
        "failsafe": os.environ['PERSONAL_SALT']
    }
    serialized_message = json.dumps(message_dict)
    response = topic.publish(Message=serialized_message)

    print("Published.")
    continue_confirmation = input("Continue? (y/n): ")
    if continue_confirmation.strip().lower() != "y":
        print("Confirmation was not supplied. Terminating.")
        sys.exit(0)
    else:
        print("Confirmation was supplied. Continuing.")

