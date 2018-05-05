# call this :
# curl -X POST -d "message=salut" -d "date=2018-04-29T17:31:00Z" -d "dest=schmittgerald@gmail.com" 127.0.0.1:5000/message/
# smtp server stuff
import smtplib
from email.message import EmailMessage

# http server stuff
from flask import Flask
from flask import request
from collections import namedtuple

# datetime stuff
import dateutil.parser
from datetime import datetime, timezone

# python stuff
import queue
import threading
import time
import json

MyMessage = namedtuple("MyMessage", "message date dest")

app = Flask(__name__)
mailQueue = queue.PriorityQueue()
condition = threading.Condition()
smtp_config = dict()


@app.route("/message/", methods=['POST', 'GET'])
def message():
    if request.method == 'POST':
        print("request.data = " + request.data.decode("utf-8"))
        print(request.form)
        m = MyMessage(request.form["message"], request.form["date"], request.form["dest"])
        print(m)
        queue_new_mail(m)
        #send_mail(m)
        return "POST message\n"
    return "GET Message\n"


@app.route("/")
def hello():
    return "Welcome to picfu, Marion!\n"


def queue_new_mail(data):
    print("Queuing new mail")
    mailQueue.put((data.date, data))
    with condition:
        condition.notify_all()


def send_mail(data):
    print("Sending email")
    try :
        smtp_server = smtplib.SMTP(smtp_config["url"], smtp_config["port"])
        # smtp_server.set_debuglevel(True)
        smtp_server.starttls()
        smtp_server.login(smtp_config["login"], smtp_config["password"])
        msg = EmailMessage()
        msg.set_content(data.message)
        msg['Subject'] = "Email from picfu"
        msg['From'] = "schmittgerald@yahoo.fr"
        msg['To'] = data.dest
        smtp_server.send_message(msg)
        smtp_server.quit()
    except :
        print("Can't send mail")
    return


# thread unpiling the mail queue
def mail_queue_pop_thread():
    while True:
        while mailQueue.qsize() > 0:
            next_mail = mailQueue.get()[1]
            print(next_mail)
            send_time = dateutil.parser.parse(next_mail.date)
            print(send_time)
            now = datetime.now(timezone.utc)
            diff = send_time - now
            if diff.total_seconds() < 0:
                print("Sending email now \n{}, but sendtime is\n{}".format(now, send_time))
                send_mail(next_mail)
            else:
                print("sending email in {}".format(diff))
                seconds_to_wait = diff.total_seconds()
                print("diff total seconds={}".format(diff.total_seconds()))
                with condition:
                    if condition.wait(seconds_to_wait):
                        # other event woke up the condition
                        print("other event wake up")
                        queue_new_mail(next_mail)
                    else:
                        # timeout occurs
                        print("timeout wake up")
                        send_mail(next_mail)
        print("No mail to send. Waiting 10s...{}".format(threading.currentThread().getName()))
        time.sleep(10)


def get_config():
    with open('config.json', 'r') as f:
        config = json.load(f)
    # print("url is {}".format(config["SMTP_SERVER"]["url"]))
    smtp_config["url"] = config["SMTP_SERVER"]["url"]
    smtp_config["port"] = config["SMTP_SERVER"]["port"]
    smtp_config["login"] = config["SMTP_SERVER"]["login"]
    smtp_config["password"] = config["SMTP_SERVER"]["password"]


if __name__ == '__main__':
    queue_thread = threading.Thread(target=mail_queue_pop_thread)
    queue_thread.start()
    get_config()
    app.run(debug=True)


