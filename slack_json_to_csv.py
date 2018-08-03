"""
Convert Slack messages exported in their complicated JSON format to simple CSV format.

To run the application use the following command:

python slack_json_to_csv.py channel_export_dir path_to_slack_users.json output.csv
eg.
python slack_json_to_csv.py slack_export/channelA slack_export/users.json output.csv
"""
import sys
import os
import csv
import json
import re
from datetime import datetime


def handle_annotated_mention(matchobj):
    return "@{}".format((matchobj.group(0)[2:-1]).split("|")[1])


def handle_mention(matchobj):
    global users
    return "@{}".format(users[matchobj.group(0)[2:-1]][0])


def transform_text(text):
    text = text.replace("<!channel>", "@channel")
    text = text.replace("&gt;",  ">")
    text = text.replace("&amp;", "&")
    # Handle "<@U0BM1CGQY|the100rabh> has joined the channel"
    text = re.compile("<@U\w+\|[A-Za-z0-9.-_]+>").sub(handle_annotated_mention, text)
    text = re.compile("<@U\w+>").sub(handle_mention, text)
    return text


def check_exist(pth, type):
    """
    Check the existence of the input file path.

    :param pth:         Full path to directory or file
    :param type:        One of 'directory' or 'file'
    :return:            Validated full path to directory
    """
    if type == 'directory' and os.path.isdir(pth):
        return pth
    elif os.path.isfile(pth):
        return pth
    else:
        raise IOError('Input {} does not exist:  {}'.format(type, pth))


def get_all_users(in_json):
    """
    Read the users.json file.

    :param in_json:     Full path to the json file
    :return:            Parsed users json
    """
    print("Users: ")
    with open(in_json) as user_data:
        user_json = json.load(user_data)
        users = {}  # Dictionary to remember all users

        # Slackbot is not in users file -- add manually
        users["USLACKBOT"] = "slackbot"

        for usr in user_json:
            userid = usr["id"]
            if "real_name" in usr and usr["real_name"]:
                realname = usr["real_name"]
                if not re.match('.*[a-zA-Z].*', realname):
                    realname = usr["name"]
            else:
                realname = usr["name"]

            print("\t{}".format(realname))
            users[userid] = realname

        return users


def write_message(csvwriter, message, author):
    """
    Write a single message from the user json as a row in the output csv.

    :param csvwriter:   A csv writer object
    :param message:     A dictionary containing information about one message
    :param author:      The name of the message author
    """
    ts = datetime.utcfromtimestamp(float(message['ts']))
    time = ts.strftime("%Y-%m-%d %H:%M:%S")
    message = transform_text(message["text"])

    csvwriter.writerow([time, author, message])


# Make sure inputs exist
json_dir = check_exist(sys.argv[1], 'directory')
userjson = check_exist(sys.argv[2], 'file')
outcsv = sys.argv[3]

users = get_all_users(userjson)

all_messages = []

for day_json in os.listdir(json_dir):
    # Open a json file containing all messages for a single day
    with open(json_dir + '/' + day_json) as data_file:
        day = json.load(data_file)
        for message in day:
            if message["type"] == "message":
                # Don't record channel joins
                if "subtype" in message and message["subtype"] == "channel_join":
                    continue

                author = users[message["user"]]

                ts = datetime.utcfromtimestamp(float(message['ts']))
                message = transform_text(message["text"])
                all_messages.append([author, ts, message])

# Sort all the messages by the timestamp, then make time more readable
all_messages = sorted(all_messages, key=lambda x: x[1])
all_messages = [[x[0], x[1].strftime("%Y-%m-%d"), x[2]] for x in all_messages]
all_messages = [[x.encode('utf-8') for x in y] for y in all_messages]
all_messages = [[x.encode('ascii', 'ignore') for x in y] for y in all_messages]

with open(outcsv, 'w') as f:
    csvwriter = csv.writer(f)
    csvwriter.writerows(all_messages)
