# call this :
# curl -X POST -d "message=salut" -d "date=2018-04-29T17:31:00Z" -d "dest=schmittgerald@gmail.com" 127.0.0.1:5000/message/

# smtp server stuff
import smtplib
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

# http server stuff
from flask import Flask, request, send_file, flash, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

# datetime stuff
import dateutil.parser
from datetime import datetime, timezone

# python stuff
import queue
import threading
import time
import json
import os
from collections import namedtuple

MyMessage = namedtuple("MyMessage", "message date dest filename")

# init server
UPLOAD_FOLDER = '/tmp/picfu/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__, static_url_path='')
app.secret_key = '!qh/C@S5WC|>_eA`#/f-{FcVW(}z4U'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# init globals
mailQueue = queue.PriorityQueue()
condition = threading.Condition()
smtp_config = dict()
server_is_running = True


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)


@app.route("/message/", methods=['POST', 'GET'])
def message():
    if request.method == 'POST':
        print("request.data = " + request.data.decode("utf-8"))
        print(request.form)

        # check if the post request has the file part
        if 'file' not in request.files:
            # flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            # flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            print(file)
            filename = secure_filename(file.filename)
            print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #return redirect(url_for('uploaded_file', filename=filename))

            m = MyMessage(request.form["message"], request.form["date"], request.form["dest"], filename)
            print(m)
            queue_new_mail(m)
            return "Message will be send!\n"
        return "An error occured..."
    return send_file("form.html")


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


def send_mail_with_attachement(data):
    print("Sending email")
    try :
        smtp_server = smtplib.SMTP(smtp_config["url"], smtp_config["port"])
        # smtp_server.set_debuglevel(True)
        smtp_server.starttls()
        smtp_server.login(smtp_config["login"], smtp_config["password"])

        msg = MIMEMultipart()
        msg['Subject'] = "Email from picfu"
        msg['From'] = "schmittgerald@yahoo.fr"
        msg['To'] = data.dest
        msg.attach(MIMEText(data.message))

        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], data.filename)
        with open(fullpath, 'rb') as file:
            part = MIMEApplication(file.read(), Name=data.filename)

        part['Content-Disposition'] = 'attachment; filename="%s"' % data.filename
        msg.attach(part)

        smtp_server.send_message(msg)
        smtp_server.quit()
    except :
        print("Can't send mail")
    return


# thread unpiling the mail queue
def mail_queue_pop_thread():
    while server_is_running:
        while mailQueue.qsize() > 0:
            next_mail = mailQueue.get()[1]
            print(next_mail)
            send_time = dateutil.parser.parse(next_mail.date)
            print(send_time)
            now = datetime.now(timezone.utc)
            diff = send_time - now
            if diff.total_seconds() < 0:
                print("Sending email now \n{}, but sendtime is\n{}".format(now, send_time))
                send_mail_with_attachement(next_mail)
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
                        send_mail_with_attachement(next_mail)
        print("No mail to send. Waiting 10s...{}".format(threading.currentThread().getName()))
        # time.sleep(10)
        with condition:
            condition.wait(10)


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

    # stop all the thread
    server_is_running = False
    with condition:
        condition.notify_all()
    queue_thread.join()


