from flask import Flask, request, render_template, url_for, redirect
from flask_restful import Resource, Api
from flask_mail import Mail, Message  # used for email
# used for serializer email and error handling
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_cors import CORS
import boto3, botocore
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import urllib.parse
import urllib.request
import base64
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI, client


from werkzeug.exceptions import BadRequest, NotFound

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil
import string
import random
import os
import hashlib 

#regex
import re
# from env_keys import BING_API_KEY, RDS_PW

import decimal
import sys
import json
import pytz
import pymysql
import requests
import stripe
import binascii
from datetime import datetime
import datetime as dt
from env_file import RDS_PW, S3_BUCKET, S3_KEY, S3_SECRET_ACCESS_KEY

# RDS for AWS SQL 8.0
RDS_HOST = 'io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
RDS_PORT = 3306
RDS_USER = 'admin'
RDS_DB = 'manifest'
s3 = boto3.client('s3')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])


app = Flask(__name__)
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})
# Set this to false when deploying to live application
app.config['DEBUG'] = True
# Adding for email testing
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'ptydtesting@gmail.com'
app.config['MAIL_PASSWORD'] = 'ptydtesting06282020'
app.config['MAIL_DEFAULT_SENDER'] = 'ptydtesting@gmail.com'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
# app.config['MAIL_DEBUG'] = True
# app.config['MAIL_SUPPRESS_SEND'] = False
# app.config['TESTING'] = False
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

mail = Mail(app)
s = URLSafeTimedSerializer('thisisaverysecretkey')
# API
api = Api(app)


# convert to UTC time zone when testing in local time zone
utc = pytz.utc
def getToday(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
def getNow(): return datetime.strftime(datetime.now(utc),"%Y-%m-%d %H:%M:%S")

# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect(RDS_HOST,
                               user=RDS_USER,
                               port=RDS_PORT,
                               passwd=RDS_PW,
                               db=RDS_DB,
                               charset='utf8mb4',
                               cursorclass=pymysql.cursors.DictCursor)
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")


# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")


# Serialize JSON
def serializeResponse(response):
    try:
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif isinstance(row[key], bytes):
                    row[key] = row[key].decode()
                elif (type(row[key]) is date or type(row[key]) is datetime) and row[key] is not None:
                    row[key] = row[key].strftime("%Y-%m-%d")
        return response
    except:
        raise Exception("Bad query JSON")


# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization=False):
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd == 'get':
                result = cur.fetchall()
                response['message'] = 'Successfully executed SQL query.'
                # Return status code of 280 for successful GET request
                response['code'] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response['result'] = result
            elif cmd == 'post':
                conn.commit()
                response['message'] = 'Successfully committed SQL command.'
                # Return status code of 281 for successful POST request
                response['code'] = 281
            else:
                response['message'] = 'Request failed. Unknown or ambiguous instruction given for MySQL command.'
                # Return status code of 480 for unknown HTTP method
                response['code'] = 480
    except:
        response['message'] = 'Request failed, could not execute MySQL command.'
        # Return status code of 490 for unsuccessful HTTP request
        response['code'] = 490
    finally:
        # response['sql'] = sql
        return response

def helper_upload_meal_img(file, key):
    bucket = S3_BUCKET
  
    if file and allowed_file(file.filename):
        filename = 'https://s3-us-west-1.amazonaws.com/' \
                   + str(bucket) + '/' + str(key)

        upload_file = s3.put_object(
                            Bucket=bucket,
                            Body=file,
                            Key=key,
                            ACL='public-read',
                            ContentType='image/jpeg'
                        )
        return filename
    return None

def allowed_file(filename):
    """Checks if the file is allowed to upload"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Returns Goals and Routines
class GoalsRoutines(Resource):
    def get(self, user_id = None):
        response = {}
        items = {}
        try:

            conn = connect()
            data = request.json
            query = None

            #returns Routines of all users
            if user_id is None:
                query = """SELECT * FROM 
                                goals_routines ;"""

            #returns Routines of a Particular user_id
            else:
                query = """SELECT * FROM goals_routines WHERE 
                             user_id = \'""" +user_id+ """\';"""

            items = execute(query,'get', conn)

            # goal_routine_response = items['result']
            # for i in range(len(goal_routine_response)):
            #     gr_id = goal_routine_response[i]['gr_unique_id']
            #     res = execute("""Select * from notifications where gr_at_id = \'""" +gr_id+ """\';""", 'get', conn)
            #     items['result'][i]['notifications'] = list(res['result'])
            
            # file_path = open("/Users/rohan/Downloads/x.png", 'r+')
            # print(file_path)
            # helper_upload_meal_images(file_path, S3_BUCKET, "p")

            response['message'] = 'successful'
            response['result'] = items['result']

            return response, 200
        except:
            raise BadRequest('Get Routines Request failed, please try again later.')
        finally:
            disconnect(conn)

# Returns Actions and Tasks
class ActionsTasks(Resource):
    def get(self, goal_routine_id = None):
        response = {}
        items = {}
        try:

            conn = connect()
            data = request.json
            query = None

            query = """SELECT * FROM actions_tasks WHERE 
                             goal_routine_id = \'""" +goal_routine_id+ """\';"""
            items = execute(query,'get', conn)

            response['result'] = items['result']

            response['message'] = 'successful'

            return response, 200
        except:
            raise BadRequest('Get Actions/Tasks Request failed, please try again later.')
        finally:
            disconnect(conn)


# returns About me information
class AboutMe(Resource):
    def get(self, user_id = None):
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
            
            # About me information of all users
            if user_id is None:
        
                query = """SELECT * FROM
                                users
                                LEFT JOIN
                                    (SELECT ta_people_id
                                        , have_pic
                                        , picture
                                        , important
                                        , user_id
                                    FROM relationship
                                    WHERE relation_type!='advisor') r
                                ON users.user_unique_id = r.user_id;"""
            
            # About me information of a particular users
            else:
                query = """ SELECT ta_people_id
                                , ta_email_id
                                , CONCAT(ta_first_name, SPACE(1), ta_last_name) as people_name
                                , ta_have_pic
                                , ta_picture
                                , important
                                , user_uid
                                , relation_type
                                , ta_phone_number as ta_phone
                                , advisor
                            FROM relationship
                            JOIN ta_people
                            ON ta_people_id = ta_unique_id
                            WHERE important = 'TRUE' and user_uid = \'""" +user_id+ """\';"""

            items1 = execute(query, 'get', conn)

            items = execute("""SELECT user_have_pic
                                    , message_card
                                    , message_day
                                    , user_picture
                                    , user_first_name
                                    , user_last_name
                                    , user_email_id
                                    , evening_time
                                    , morning_time
                                    , afternoon_time
                                    , night_time
                                    , day_end
                                    , day_start
                                    , time_zone
                                FROM users
                            WHERE user_unique_id = \'""" +user_id+ """\';""", 'get', conn)

            if len(items1['result']) > 0:
                response['result'] = items['result'] + items1['result']
            else:
                items1['result'] = [{ "important_people" : "no important people"}]
                response['result'] = items['result'] + items1['result']
            
            response['message'] = 'successful'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# returns all users of a TA
class AllUsers(Resource):
    def get(self, email_id = None):
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
            
            # All users of a TA
        
            query = """SELECT user_unique_id
                            , CONCAT(user_first_name, SPACE(1), user_last_name) as user_name
                            , user_email_id
                            , user_picture
                            , time_zone
                        FROM
                        users
                        JOIN
                        relationship
                        ON user_unique_id = user_uid
                        JOIN ta_people
                        ON ta_people_id = ta_unique_id
                        WHERE advisor = '1' and ta_email_id = \'""" + email_id + """\';"""
            
            items = execute(query, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items['result']
        

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Returns all TA of a user
class ListAllTA(Resource):
    def get(self, user_id = None):    
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
            if user_id is None:
                query = """SELECT DISTINCT unique_id
                            , CONCAT(first_name, SPACE(1), last_name) as name
                            , first_name
                            , last_name
                            FROM ta_people
                            JOIN relationship on unique_id = ta_people_id
                            WHERE type = 'trusted_advisor';"""
                
            else:
                query = """ SELECT DISTINCT ta_unique_id
                                    , CONCAT(ta_first_name, SPACE(1), ta_last_name) as name
                                    , ta_first_name
                                    , ta_last_name
                            FROM ta_people
                            JOIN relationship on ta_unique_id = ta_people_id
                            WHERE user_uid = \'""" +user_id+ """\'
                            and advisor = '1';"""

                query2 = """SELECT DISTINCT ta_unique_id
                                    , CONCAT(ta_first_name, SPACE(1), ta_last_name) as name
                                    , ta_first_name
                                    , ta_last_name
                            FROM ta_people
                            JOIN relationship on ta_unique_id = ta_people_id
                            WHERE advisor = '1';"""

            idTAResponse = execute(query, 'get', conn)
            allTAResponse = execute(query2, 'get', conn)

            list = []
            final_list = []

            for i in range(len(idTAResponse['result'])):
                list.append(idTAResponse['result'][i]['ta_unique_id'])

            for i in range(len(allTAResponse['result'])):
                if allTAResponse['result'][i]['ta_unique_id'] not in list:
                    final_list.append(allTAResponse['result'][i])

            response['message'] = 'successful'
            response['result'] = final_list

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Add another TA for a user
class AnotherTAAccess(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()

            data = request.get_json(force=True)

            timestamp = getNow()

            ta_id = data['ta_people_id']
            user_id = data['user_id']

            query = ["Call get_relation_id;"]
            new_relation_id_response = execute(query[0], 'get', conn)
            new_relation_id = new_relation_id_response['result'][0]['new_id']

            query.append("""INSERT INTO relationship
                                        (id
                                        , r_timestamp
                                        , ta_people_id
                                        , user_uid
                                        , relation_type
                                        , ta_have_pic
                                        , ta_picture
                                        , important
                                        , advisor)
                            VALUES 
                                        ( \'""" + str(new_relation_id) + """\'
                                        , \'""" + str(timestamp) + """\'
                                        , \'""" + str(ta_id) + """\'
                                        , \'""" + str(user_id) + """\'
                                        , \'""" + 'advisor' + """\'
                                        , \'""" + 'False' + """\'
                                        , \'""" + '' + """\'
                                        , \'""" + 'False' + """\'
                                        , \'""" + str(1) + """\');""")
            items = execute(query[1], 'post', conn)

                # Load all the results as a list of dictionaries

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Returns ALl People of a user
class ListAllPeople(Resource):
    def get(self, user_id = None):
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
            
            if user_id is None:
        
                query = """SELECT user_id
                                , CONCAT(u.first_name, SPACE(1), u.last_name) as user_name
                                , ta_people_id
                                , ta.first_name as important_people_first_name
                                , ta.last_name as important_people_last_name
                                , ta.phone_number
                                , r.have_pic
                                , r.picture
                                , r.important
                            FROM relationship r
                            JOIN
                            ta_people ta
                            ON r.ta_people_id = ta.unique_id
                            JOIN users u on r.user_id = u.user_unique_id
                            WHERE (type = 'people' or type = 'both') and relation_type != 'advisor';"""
            else:
                query = """SELECT user_uid
                                , CONCAT(user_first_name, SPACE(1), user_last_name) as user_name
                                , ta_people_id
                                , ta_email_id as email
                                , user_have_pic as have_pic
                                , important as important
                                , CONCAT(ta_first_name, SPACE(1), ta_last_name) as name
                                , ta_phone_number as phone_number
                                , ta_picture as pic
                                , relation_type as relationship
                            FROM relationship
                            JOIN
                            ta_people ta
                            ON ta_people_id = ta_unique_id
                            JOIN users on user_uid = user_unique_id
                            WHERE user_uid = \'""" + user_id+  """\';"""
            
            items = execute(query,'get', conn)
                # Load all the results as a list of dictionaries

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Add new Goal/Routine of a user
class AddNewGR(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            id = data['id']
            audio = data['audio']
            datetime_completed = data['datetime_completed']
            datetime_started = data['datetime_started']
            end_day_and_time = data['end_day_and_time']
            expected_completion_time = data['expected_completion_time']
            user_id = data['user_id']
            # ta_id = data['ta_people_id']
            is_available = data['is_available']
            is_complete = data['is_complete']
            is_displayed_today = data['is_displayed_today']
            is_in_progress = data['is_in_progress']
            is_persistent = data['is_persistent']
            is_sublist_available = data['is_sublist_available']
            is_timed = data['is_timed']
            photo = data['photo']
            repeat = data['repeat']
            repeat_ends = data['repeat_ends']
            repeat_ends_on = data['repeat_ends_on']
            repeat_every = data['repeat_every']
            repeat_frequency = data['repeat_frequency']
            repeat_occurences = data['repeat_occurences']
            repeat_week_days = data['repeat_week_days']
            print(repeat_week_days)
            start_day_and_time = data['start_day_and_time']
            print(start_day_and_time)
            ta_before_is_enable = data['ta_notifications']['before']['is_enabled']
            print(ta_before_is_enable)
            ta_before_is_set = data['ta_notifications']['before']['is_set']
            ta_before_message = data['ta_notifications']['before']['message']
            ta_before_time = data['ta_notifications']['before']['time']
            ta_during_is_enable = data['ta_notifications']['during']['is_enabled']
            ta_during_is_set = data['ta_notifications']['during']['is_set']
            ta_during_message = data['ta_notifications']['during']['message']
            print(ta_during_message)
            ta_during_time = data['ta_notifications']['during']['time']
            ta_after_is_enable = data['ta_notifications']['after']['is_enabled']
            ta_after_is_set = data['ta_notifications']['after']['is_set']
            ta_after_message = data['ta_notifications']['after']['message']
            ta_after_time = data['ta_notifications']['after']['time']
            gr_title = data['title']
            print(gr_title)
            user_before_is_enable = data['user_notifications']['before']['is_enabled']
            user_before_is_set = data['user_notifications']['before']['is_set']
            user_before_message = data['user_notifications']['before']['message']
            user_before_time = data['user_notifications']['before']['time']
            user_during_is_enable = data['user_notifications']['during']['is_enabled']
            user_during_is_set = data['user_notifications']['during']['is_set']
            user_during_message = data['user_notifications']['during']['message']
            user_during_time = data['user_notifications']['during']['time']
            user_after_is_enable = data['user_notifications']['after']['is_enabled']
            user_after_is_set = data['user_notifications']['after']['is_set']
            user_after_message = data['user_notifications']['after']['message']
            user_after_time = data['user_notifications']['after']['time']

            dict_week_days = {"Sunday":"False", "Monday":"False", "Tuesday":"False", "Wednesday":"False", "Thursday":"False", "Friday":"False", "Saturday":"False"}
            for key in repeat_week_days:
                if repeat_week_days[key] == "Sunday":
                    dict_week_days["Sunday"] = "True"
                if repeat_week_days[key] == "Monday":
                    dict_week_days["Monday"] = "True"
                if repeat_week_days[key] == "Tuesday":
                    dict_week_days["Tuesday"] = "True"
                if repeat_week_days[key] == "Wednesday":
                    dict_week_days["Wednesday"] = "True"
                if repeat_week_days[key] == "Thursday":
                    dict_week_days["Thursday"] = "True"
                if repeat_week_days[key] == "Friday":
                    dict_week_days["Friday"] = "True"
                if repeat_week_days[key] == "Saturday":
                    dict_week_days["saturday"] = "True"

            # New Goal/Routine ID
            query = ["CALL get_gr_id;"]
            new_gr_id_response = execute(query[0],  'get', conn)
            new_gr_id = new_gr_id_response['result'][0]['new_id']

            # Add G/R to database
            query.append("""INSERT INTO goals_routines(gr_unique_id
                            , gr_title
                            , user_id
                            , is_available
                            , is_complete
                            , is_in_progress
                            , is_displayed_today
                            , is_persistent
                            , is_sublist_available
                            , is_timed
                            , photo
                            , `repeat`
                            , repeat_type
                            , repeat_ends_on
                            , repeat_every
                            , repeat_frequency
                            , repeat_occurences
                            , start_day_and_time
                            , repeat_week_days
                            , datetime_completed
                            , datetime_started
                            , end_day_and_time
                            , expected_completion_time)
                        VALUES 
                        ( \'""" + new_gr_id + """\'
                        , \'""" + gr_title + """\'
                        , \'""" + user_id + """\'
                        , \'""" + str(is_available).title() + """\'
                        , \'""" + str(is_complete).title() + """\'
                        , \'""" + str(is_in_progress).title() + """\'
                        , \'""" + str(is_displayed_today).title() + """\'
                        , \'""" + str(is_persistent).title() + """\'
                        , \'""" + str(is_sublist_available).title() + """\'
                        , \'""" + str(is_timed).title() + """\'
                        , \'""" + photo + """\'
                        , \'""" + str(repeat) + """\'
                        , \'""" + repeat_ends + """\'
                        , \'""" + repeat_ends_on + """\'
                        , \'""" + str(repeat_every) + """\'
                        , \'""" + repeat_frequency + """\'
                        , \'""" + str(repeat_occurences) + """\'
                        , \'""" + start_day_and_time + """\'
                        , \'""" + json.dumps(dict_week_days) + """\'
                        , \'""" + datetime_completed + """\'
                        , \'""" + datetime_started + """\'
                        , \'""" + end_day_and_time + """\'
                        , \'""" + expected_completion_time + """\');""")

            execute(query[1], 'post', conn)
            
            # # New Notification ID
            # new_notification_id_response = execute("CALL get_notification_id;",  'get', conn)
            # new_notfication_id = new_notification_id_response['result'][0]['new_id']

            # # TA notfication
            # query.append("""Insert into notifications
            #                     (notification_id
            #                         , user_ta_id
            #                         , gr_at_id
            #                         , before_is_enable
            #                         , before_is_set
            #                         , before_message
            #                         , before_time
            #                         , during_is_enable
            #                         , during_is_set
            #                         , during_message
            #                         , during_time
            #                         , after_is_enable
            #                         , after_is_set
            #                         , after_message
            #                         , after_time) 
            #                     VALUES
            #                     (     \'""" + new_notfication_id + """\'
            #                         , \'""" + ta_id + """\'
            #                         , \'""" + new_gr_id + """\'
            #                         , \'""" + str(ta_before_is_enable) + """\'
            #                         , \'""" + str(ta_before_is_set) + """\'
            #                         , \'""" + ta_before_message + """\'
            #                         , \'""" + ta_before_time + """\'
            #                         , \'""" + str(ta_during_is_enable) + """\'
            #                         , \'""" + str(ta_during_is_set) + """\'
            #                         , \'""" + ta_during_message + """\'
            #                         , \'""" + ta_during_time + """\'
            #                         , \'""" + str(ta_after_is_enable) + """\'
            #                         , \'""" + str(ta_after_is_set) + """\'
            #                         , \'""" + ta_after_message + """\'
            #                         , \'""" + ta_after_time + """\');""")
            # execute(query[2], 'post', conn)

            # New notification ID
            NewNotificationIDresponse = execute("CALL get_notification_id;",  'get', conn)
            NewNotificationID = NewNotificationIDresponse['result'][0]['new_id']

            # User notfication
            query.append("""Insert into notifications
                                (notification_id
                                    , user_ta_id
                                    , gr_at_id
                                    , before_is_enable
                                    , before_is_set
                                    , before_message
                                    , before_time
                                    , during_is_enable
                                    , during_is_set
                                    , during_message
                                    , during_time
                                    , after_is_enable
                                    , after_is_set
                                    , after_message
                                    , after_time) 
                                VALUES
                                (     \'""" + NewNotificationID + """\'
                                    , \'""" + user_id + """\'
                                    , \'""" + new_gr_id + """\'
                                    , \'""" + str(user_before_is_enable).title() + """\'
                                    , \'""" + str(user_before_is_set).title() + """\'
                                    , \'""" + user_before_message + """\'
                                    , \'""" + user_before_time + """\'
                                    , \'""" + str(user_during_is_enable).title() + """\'
                                    , \'""" + str(user_during_is_set).title() + """\'
                                    , \'""" + user_during_message + """\'
                                    , \'""" + user_during_time + """\'
                                    , \'""" + str(user_after_is_enable).title() + """\'
                                    , \'""" + str(user_after_is_set).title() + """\'
                                    , \'""" + user_after_message + """\'
                                    , \'""" + user_after_time + """\');""")
            items = execute(query[2], 'post', conn)


            response['message'] = 'successful'
            response['result'] = new_gr_id

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Add new Goal/Routine of a user
class UpdateGR(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            audio = data['audio']
            datetime_completed = data['datetime_completed']
            datetime_started = data['datetime_started']
            end_day_and_time = data['end_day_and_time']
            expected_completion_time = data['expected_completion_time']
            id = data['id']
            print(id)
            is_available = data['is_available']
            is_complete = data['is_complete']
            is_displayed_today = data['is_displayed_today']
            is_in_progress = data['is_in_progress']
            is_persistent = data['is_persistent']
            is_sublist_available = data['is_sublist_available']
            is_timed = data['is_timed']
            print(is_timed)
            photo = data['photo']
            print(photo)
            repeat = data['repeat']
            print(repeat)
            repeat_ends = data['repeat_ends']
            repeat_ends_on = data['repeat_ends_on']
            repeat_every = data['repeat_every']
            repeat_frequency = data['repeat_frequency']
            repeat_occurences = data['repeat_occurences']
            repeat_week_days = data['repeat_week_days']
            print(repeat_week_days)
            start_day_and_time = data['start_day_and_time']
            ta_before_is_enable = data['ta_notifications']['before']['is_enabled']
            ta_before_is_set = data['ta_notifications']['before']['is_set']
            ta_before_message = data['ta_notifications']['before']['message']
            ta_before_time = data['ta_notifications']['before']['time']
            ta_during_is_enable = data['ta_notifications']['during']['is_enabled']
            ta_during_is_set = data['ta_notifications']['during']['is_set']
            ta_during_message = data['ta_notifications']['during']['message']
            ta_during_time = data['ta_notifications']['during']['time']
            ta_after_is_enable = data['ta_notifications']['after']['is_enabled']
            ta_after_is_set = data['ta_notifications']['after']['is_set']
            ta_after_message = data['ta_notifications']['after']['message']
            ta_after_time = data['ta_notifications']['after']['time']
            gr_title = data['title']
            print(gr_title)
            user_before_is_enable = data['user_notifications']['before']['is_enabled']
            user_before_is_set = data['user_notifications']['before']['is_set']
            user_before_message = data['user_notifications']['before']['message']
            user_before_time = data['user_notifications']['before']['time']
            user_during_is_enable = data['user_notifications']['during']['is_enabled']
            user_during_is_set = data['user_notifications']['during']['is_set']
            user_during_message = data['user_notifications']['during']['message']
            user_during_time = data['user_notifications']['during']['time']
            user_after_is_enable = data['user_notifications']['after']['is_enabled']
            user_after_is_set = data['user_notifications']['after']['is_set']
            user_after_message = data['user_notifications']['after']['message']
            user_after_time = data['user_notifications']['after']['time']
            user_id = data['user_id']
            print(user_id)
            ta_people_id = data['ta_people_id']
            print(user_id)
            # user_id_response = execute("""SELECT user_id from goals_routines where gr_unique_id = \'""" +id+ """\'""", 'get', conn)
            # user_id = user_id_response['result'][0]['user_id']

            dict_week_days = {"Sunday":"False", "Monday":"False", "Tuesday":"False", "Wednesday":"False", "Thursday":"False", "Friday":"False", "Saturday":"False"}
            for key in repeat_week_days:
                if repeat_week_days[key] == "Sunday":
                    dict_week_days["Sunday"] = "True"
                if repeat_week_days[key] == "Monday":
                    dict_week_days["Monday"] = "True"
                if repeat_week_days[key] == "Tuesday":
                    dict_week_days["Tuesday"] = "True"
                if repeat_week_days[key] == "Wednesday":
                    dict_week_days["Wednesday"] = "True"
                if repeat_week_days[key] == "Thursday":
                    dict_week_days["Thursday"] = "True"
                if repeat_week_days[key] == "Friday":
                    dict_week_days["Friday"] = "True"
                if repeat_week_days[key] == "Saturday":
                    dict_week_days["Saturday"] = "True"   
                
            # Update G/R to database
            query = """UPDATE goals_routines
                            SET gr_title = \'""" + gr_title + """\'
                                , is_available = \'""" + str(is_available).title() + """\'
                                ,is_complete = \'""" + str(is_complete).title() + """\'
                                ,is_sublist_available = \'""" + str(is_sublist_available).title() + """\'
                                ,is_in_progress = \'""" + str(is_in_progress).title() + """\'
                                ,is_displayed_today = \'""" + str(is_displayed_today).title() + """\'
                                ,is_persistent = \'""" + str(is_persistent).title() + """\'
                                ,is_timed = \'""" + str(is_timed).title() + """\'
                                ,start_day_and_time = \'""" + start_day_and_time + """\'
                                ,end_day_and_time = \'""" + end_day_and_time + """\'
                                ,datetime_started = \'""" + datetime_started + """\'
                                ,datetime_completed = \'""" + datetime_completed + """\'
                                ,`repeat` = \'""" + str(repeat) + """\'
                                ,repeat_type = \'""" + repeat_ends + """\'
                                ,repeat_ends_on = \'""" + repeat_ends_on + """\'
                                ,repeat_every = \'""" + str(repeat_every) + """\'
                                ,repeat_frequency = \'""" + repeat_frequency + """\'
                                ,repeat_occurences = \'""" + str(repeat_occurences) + """\'
                                ,repeat_week_days = \'""" + json.dumps(dict_week_days) + """\'
                                ,expected_completion_time = \'""" + expected_completion_time + """\'
                                ,photo = \'""" + photo + """\'
                        WHERE gr_unique_id = \'""" +id+ """\';"""
            items = execute(query, 'post', conn)


            # TA notfication
            query1 = """UPDATE notifications
                             SET   before_is_enable = \'""" + str(user_before_is_enable).title() + """\'
                                    , before_is_set  = \'""" + str(user_before_is_set).title() + """\'
                                    , before_message = \'""" + user_before_message + """\'
                                    , before_time = \'""" + user_before_time + """\'
                                    , during_is_enable = \'""" + str(user_during_is_enable).title() + """\'
                                    , during_is_set = \'""" + str(user_during_is_set).title() + """\'
                                    , during_message = \'""" + user_during_message + """\'
                                    , during_time = \'""" + user_during_time + """\'
                                    , after_is_enable = \'""" + str(user_after_is_enable).title() + """\'
                                    , after_is_set = \'""" + str(user_after_is_set).title() + """\'
                                    , after_message = \'""" + user_after_message + """\'
                                    , after_time  = \'""" + user_after_time + """\'
                                WHERE gr_at_id = \'""" +id+ """\' and user_ta_id = \'""" +user_id+ """\';"""
            execute(query1, 'post', conn)
            print(query1)

            # User notfication
            query2 = """UPDATE notifications
                             SET   before_is_enable = \'""" + str(ta_before_is_enable).title() + """\'
                                    , before_is_set  = \'""" + str(ta_before_is_set).title() + """\'
                                    , before_message = \'""" + ta_before_message + """\'
                                    , before_time = \'""" + ta_before_time + """\'
                                    , during_is_enable = \'""" + str(ta_during_is_enable).title() + """\'
                                    , during_is_set = \'""" + str(ta_during_is_set).title() + """\'
                                    , during_message = \'""" + ta_during_message + """\'
                                    , during_time = \'""" + ta_during_time + """\'
                                    , after_is_enable = \'""" + str(ta_after_is_enable).title() + """\'
                                    , after_is_set = \'""" + str(ta_after_is_set).title() + """\'
                                    , after_message = \'""" + ta_after_message + """\'
                                    , after_time  = \'""" + ta_after_time + """\'
                                WHERE gr_at_id = \'""" +id+ """\' and user_ta_id  = \'""" +ta_people_id+ """\';"""
            print(query2)
            execute(query2, 'post', conn)
            response['message'] = 'Update to Goal and Routine was Successful'
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class AddNewAT(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            audio = data['audio']
            datetime_completed = data['datetime_completed']
            datetime_started = data['datetime_started']
            expected_completion_time = data['expected_completion_time']
            gr_id = data['gr_id']
            is_available = data['is_available']
            is_complete = data['is_complete']
            is_in_progress = data['is_in_progress']
            is_must_do = data['is_must_do']
            is_sublist_available = data['is_sublist_available']
            is_timed = data['is_timed']
            photo = data['photo']
            at_title = data['title']
            available_end_time = data['available_end_time']
            available_start_time = data['available_start_time']

            # ta_before_is_enable = data['ta_notifications']['before']['is_enable']
            # ta_before_is_set = data['ta_notifications']['before']['is_set']
            # ta_before_message = data['ta_notifications']['before']['message']
            # ta_before_time = data['ta_notifications']['before']['time']
            # ta_during_is_enable = data['ta_notifications']['during']['is_enable']
            # ta_during_is_set = data['ta_notifications']['during']['is_set']
            # ta_during_message = data['ta_notifications']['during']['message']
            # ta_during_time = data['ta_notifications']['during']['time']
            # ta_after_is_enable = data['ta_notifications']['after']['is_enable']
            # ta_after_is_set = data['ta_notifications']['after']['is_set']
            # ta_after_message = data['ta_notifications']['after']['message']
            # ta_after_time = data['ta_notifications']['after']['time']
            # user_before_is_enable = data['user_notifications']['before']['is_enable']
            # user_before_is_set = data['user_notifications']['before']['is_set']
            # user_before_message = data['user_notifications']['before']['message']
            # user_before_time = data['user_notifications']['before']['time']
            # user_during_is_enable = data['user_notifications']['during']['is_enable']
            # user_during_is_set = data['user_notifications']['during']['is_set']
            # user_during_message = data['user_notifications']['during']['message']
            # user_during_time = data['user_notifications']['during']['time']
            # user_after_is_enable = data['user_notifications']['after']['is_enable']
            # user_after_is_set = data['user_notifications']['after']['is_set']
            # user_after_message = data['user_notifications']['after']['message']
            # user_after_time = data['user_notifications']['after']['time']

            query = ["CALL get_at_id;"]
            NewATIDresponse = execute(query[0],  'get', conn)
            NewATID = NewATIDresponse['result'][0]['new_id']

            # query.append("""SELECT at_sequence
            #                 FROM actions_tasks
            #                 WHERE goal_routine_id = \'""" + gr_id + """\'
            #                 ORDER BY at_sequence DESC
            #                 LIMIT 1;""")
            # ATSequenceResponse = execute(query[1], 'get', conn)
            # at_sequence = ATSequenceResponse['result'][0]['at_sequence']
            # if(at_sequence >= 1):
            #     at_sequence += 1
            # else:
            #     at_sequence = 1

            query.append("""INSERT INTO actions_tasks(at_unique_id
                            , at_title
                            , goal_routine_id
                            , at_sequence
                            , is_available
                            , is_complete
                            , is_in_progress
                            , is_sublist_available
                            , is_must_do
                            , photo
                            , is_timed
                            , datetime_completed
                            , datetime_started
                            , expected_completion_time
                            , available_start_time
                            , available_end_time)
                        VALUES 
                        ( \'""" + NewATID + """\'
                        , \'""" + at_title + """\'
                        , \'""" + gr_id + """\'
                        , \'""" + '1' + """\'
                        , \'""" + str(is_available).title() + """\'
                        , \'""" + str(is_complete).title() + """\'
                        , \'""" + str(is_in_progress).title() + """\'
                        , \'""" + str(is_sublist_available).title() + """\'
                        , \'""" + str(is_must_do).title() + """\'
                        , \'""" + photo + """\'
                        , \'""" + str(is_timed).title() + """\'
                        , \'""" + datetime_completed + """\'
                        , \'""" + datetime_started + """\'
                        , \'""" + expected_completion_time + """\'
                        , \'""" + available_start_time + """\'
                        , \'""" + available_end_time + """\' );""")

            items = execute(query[1], 'post', conn)

            # # New Notification ID
            # NewNotificationIDresponse = execute("CALL get_notification_id;",  'get', conn)
            # NewNotificationID = NewNotificationIDresponse['result'][0]['new_id']

            # # TA notfication
            # query.append("""Insert into notifications
            #                     (notification_id
            #                         , user_ta_id
            #                         , gr_at_id
            #                         , before_is_enable
            #                         , before_is_set
            #                         , before_message
            #                         , before_time
            #                         , during_is_enable
            #                         , during_is_set
            #                         , during_message
            #                         , during_time
            #                         , after_is_enable
            #                         , after_is_set
            #                         , after_message
            #                         , after_time) 
            #                     VALUES
            #                     (     \'""" + NewNotificationID + """\'
            #                         , \'""" + ta_id + """\'
            #                         , \'""" + NewATID + """\'
            #                         , \'""" + ta_before_is_enable + """\'
            #                         , \'""" + ta_before_is_set + """\'
            #                         , \'""" + ta_before_message + """\'
            #                         , \'""" + ta_before_time + """\'
            #                         , \'""" + ta_during_is_enable + """\'
            #                         , \'""" + ta_during_is_set + """\'
            #                         , \'""" + ta_during_message + """\'
            #                         , \'""" + ta_during_time + """\'
            #                         , \'""" + ta_after_is_enable + """\'
            #                         , \'""" + ta_after_is_set + """\'
            #                         , \'""" + ta_after_message + """\'
            #                         , \'""" + ta_after_time + """\');""")
            # execute(query[3], 'post', conn)

            # # New notification ID
            # NewNotificationIDresponse = execute("CALL get_notification_id;",  'get', conn)
            # NewNotificationID = NewNotificationIDresponse['result'][0]['new_id']

            # # User notfication
            # query.append("""Insert into notifications
            #                     (notification_id
            #                         , user_ta_id
            #                         , gr_at_id
            #                         , before_is_enable
            #                         , before_is_set
            #                         , before_message
            #                         , before_time
            #                         , during_is_enable
            #                         , during_is_set
            #                         , during_message
            #                         , during_time
            #                         , after_is_enable
            #                         , after_is_set
            #                         , after_message
            #                         , after_time) 
            #                     VALUES
            #                     (     \'""" + NewNotificationID + """\'
            #                         , \'""" + user_id + """\'
            #                         , \'""" + NewATID + """\'
            #                         , \'""" + user_before_is_enable + """\'
            #                         , \'""" + user_before_is_set + """\'
            #                         , \'""" + user_before_message + """\'
            #                         , \'""" + user_before_time + """\'
            #                         , \'""" + user_during_is_enable + """\'
            #                         , \'""" + user_during_is_set + """\'
            #                         , \'""" + user_during_message + """\'
            #                         , \'""" + user_during_time + """\'
            #                         , \'""" + user_after_is_enable + """\'
            #                         , \'""" + user_after_is_set + """\'
            #                         , \'""" + user_after_message + """\'
            #                         , \'""" + user_after_time + """\');""")
            # execute(query[4], 'post', conn)


            response['message'] = 'successful'
            response['result'] = NewATID

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class UpdateAT(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            audio = data['audio']
            datetime_completed = data['datetime_completed']
            datetime_started = data['datetime_started']
            available_end_time = data['available_end_time']
            available_start_time = data['available_start_time']
            expected_completion_time = data['expected_completion_time']
            id = data['id']
            is_available = data['is_available']
            is_complete = data['is_complete']
            is_in_progress = data['is_in_progress']
            is_must_do = data['is_must_do']
            is_sublist_available = data['is_sublist_available']
            is_timed = data['is_timed']
            photo = data['photo']
            at_title = data['title']

            # ta_before_is_enable = data['ta_notifications']['before']['is_enable']
            # ta_before_is_set = data['ta_notifications']['before']['is_set']
            # ta_before_message = data['ta_notifications']['before']['message']
            # ta_before_time = data['ta_notifications']['before']['time']
            # ta_during_is_enable = data['ta_notifications']['during']['is_enable']
            # ta_during_is_set = data['ta_notifications']['during']['is_set']
            # ta_during_message = data['ta_notifications']['during']['message']
            # ta_during_time = data['ta_notifications']['during']['time']
            # ta_after_is_enable = data['ta_notifications']['after']['is_enable']
            # ta_after_is_set = data['ta_notifications']['after']['is_set']
            # ta_after_message = data['ta_notifications']['after']['message']
            # ta_after_time = data['ta_notifications']['after']['time']
            # user_before_is_enable = data['user_notifications']['before']['is_enable']
            # user_before_is_set = data['user_notifications']['before']['is_set']
            # user_before_message = data['user_notifications']['before']['message']
            # user_before_time = data['user_notifications']['before']['time']
            # user_during_is_enable = data['user_notifications']['during']['is_enable']
            # user_during_is_set = data['user_notifications']['during']['is_set']
            # user_during_message = data['user_notifications']['during']['message']
            # user_during_time = data['user_notifications']['during']['time']
            # user_after_is_enable = data['user_notifications']['after']['is_enable']
            # user_after_is_set = data['user_notifications']['after']['is_set']
            # user_after_message = data['user_notifications']['after']['message']
            # user_after_time = data['user_notifications']['after']['time']

            # query.append("""SELECT at_sequence
            #                 FROM actions_tasks
            #                 WHERE goal_routine_id = \'""" + gr_id + """\'
            #                 ORDER BY at_sequence DESC
            #                 LIMIT 1;""")
            # ATSequenceResponse = execute(query[1], 'get', conn)
            # at_sequence = ATSequenceResponse['result'][0]['at_sequence']
            # if(at_sequence >= 1):
            #     at_sequence += 1
            # else:
            #     at_sequence = 1

            gr_id_response = execute("""SELECT goal_routine_id from actions_tasks where at_unique_id = \'""" +id+ """\'""", 'get', conn)
            gr_id = gr_id_response['result'][0]['goal_routine_id']
            print(gr_id)
            query = """UPDATE actions_tasks
                        SET  at_title = \'""" + at_title + """\'
                            , goal_routine_id = \'""" + gr_id + """\'
                            , at_sequence = \'""" + '1' + """\'
                            , is_available = \'""" + str(is_available).title() + """\'
                            , is_complete = \'""" + str(is_complete).title() + """\'
                            , is_in_progress = \'""" + str(is_in_progress).title() + """\'
                            , is_sublist_available = \'""" + str(is_sublist_available).title() + """\'
                            , is_must_do = \'""" + str(is_must_do).title() + """\'
                            , photo = \'""" + photo + """\'
                            , is_timed = \'""" + str(is_timed).title() + """\'
                            , datetime_completed =  \'""" + datetime_completed + """\'
                            , datetime_started = \'""" + datetime_started + """\'
                            , expected_completion_time = \'""" + expected_completion_time + """\'
                            , available_start_time = \'""" + available_start_time + """\'
                            , available_end_time = \'""" + available_end_time + """\'
                            WHERE at_unique_id = \'""" +id+ """\';"""
            print(query)
            items = execute(query, 'post', conn)
            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Delete Goal/Routine
class DeleteGR(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            goal_routine_id = data['goal_routine_id']

            query = ["""DELETE FROM goals_routines WHERE gr_unique_id = \'""" + goal_routine_id + """\';"""]
            
            execute(query[0], 'post', conn)
            
            execute("""DELETE FROM notifications 
                        WHERE gr_at_id = \'""" + goal_routine_id + """\';""", 'post', conn)

            query.append("""SELECT at_unique_id FROM actions_tasks 
                            WHERE goal_routine_id = \'""" + goal_routine_id + """\';""")

            atResponse = execute(query[1], 'get', conn)

            for i in range(len(atResponse['result'])):
                at_id = atResponse['result'][i]['at_unique_id']
                execute("""DELETE FROM actions_tasks WHERE at_unique_id = \'""" + at_id + """\';""", 'post', conn)
                execute("""DELETE FROM notifications 
                            WHERE gr_at_id = \'""" + at_id + """\';""", 'post', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Delete Action/Task
class DeleteAT(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            at_id = data['at_id']

            query = ["""DELETE FROM actions_tasks WHERE at_unique_id = \'""" + at_id + """\';"""]
            
            execute(query[0], 'post', conn)

            # execute("""DELETE FROM notifications 
            #                 WHERE gr_at_id = \'""" + at_id + """\';""", 'post', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# day's view
class DailyView(Resource):
    def get(self, user_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            listGR = []
            theday = dt.date.today()
            dates = [theday]
            vr = VariousRepeatations()
            items = VariousRepeatations.checkAllDays(vr, dates, user_id, conn)
            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Week's view
class WeeklyView(Resource):
    def get(self, user_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            theday = dt.date.today()
            weekday = (theday.isoweekday() + 1)%7
            start = theday - dt.timedelta(days=weekday)
            dates = [start + dt.timedelta(days=d) for d in range(7)]
            
            vr = VariousRepeatations()
            items = VariousRepeatations.checkAllDays(vr, dates, user_id, conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Month's view
class MonthlyView(Resource):
    def get(self, user_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            m = datetime.now().month
            y = datetime.now().year
            ndays = (date(y, m+1, 1) - date(y, m, 1)).days
            d1 = date(y, m, 1)
            d2 = date(y, m, ndays)
            delta = d2 - d1
            dates =  [(d1 + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(delta.days + 1)]

            vr = VariousRepeatations()
            items = VariousRepeatations.checkAllDays(vr, dates, user_id, conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class VariousRepeatations():
    def checkAllDays(self, dates, user_id, conn):
        items = {}
        for date in dates:
            if(isinstance(date, str)):
                date = datetime.strptime(date, '%Y-%m-%d').date()
            cur_date = date
            cur_week = cur_date.isocalendar()[1]
            cur_month = cur_date.month
            cur_year = cur_date.year
            listGR = []

            # For never and day frequency
            query = ["""SELECT gr_title
                            , user_id
                            , gr_unique_id
                            , start_day_and_time
                            , repeat_frequency
                            , repeat_every from goals_routines
                        where `repeat` = 'TRUE' and repeat_ends = 'never' and repeat_frequency = 'day'
                        and user_id = \'""" + user_id + """\';"""]

            grResponse = execute(query[0], 'get', conn)

            for i in range(len(grResponse['result'])):
                datetime_str = grResponse['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                new_date = datetime_object
                while(new_date <= cur_date):
                    if(new_date == cur_date):
                        listGR.append(grResponse['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(days=grResponse['result'][i]['repeat_every'])


            # For never and week frequency

            query.append("""SELECT gr_unique_id
                                    , start_day_and_time
                                    , repeat_every
                                from (SELECT gr_title
                                        , user_id
                                        , gr_unique_id
                                        , start_day_and_time
                                        , repeat_frequency
                                        , repeat_every
                                        , substring_index(substring_index(repeat_week_days, ';', id), ';', -1) as week_days
                                    FROM goals_routines
                                            JOIN numbers ON char_length(repeat_week_days) - char_length(replace(repeat_week_days, ';', '')) >= id - 1
                                    where `repeat` = 'TRUE'
                                        and repeat_ends = 'never'
                                        and repeat_frequency = 'week') temp
                                where dayname(curdate()) = week_days and user_id = \'""" + user_id + """\';""")

            grResponse1 = execute(query[1], 'get', conn)

            for i in range(len(grResponse1['result'])):
                datetime_str = grResponse1['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                start_week = datetime_object.isocalendar()[1]
                new_week = start_week
                new_date = datetime_object
                while(new_date <= cur_date):
                    if (new_week - start_week) == int(grResponse1['result'][i]['repeat_every']):
                        start_week = new_week
                        if (new_week == cur_week):
                            listGR.append(grResponse1['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(weeks=grResponse1['result'][i]['repeat_every'])
                    new_week = new_date.isocalendar()[1]

            # For never and month frequency

            query.append("""SELECT gr_title
                                    , user_id
                                    , gr_unique_id
                                    , start_day_and_time
                                    , repeat_frequency
                                    , repeat_every
                                FROM goals_routines
                            WHERE `repeat` = 'TRUE'
                                    AND repeat_ends = 'never'
                                    AND repeat_frequency = 'month' and user_id = \'""" + user_id + """\';""")
            
            grResponse2 = execute(query[2], 'get', conn)


            for i in range(len(grResponse2['result'])):
                datetime_str = grResponse2['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                start_month = datetime_object.month
                new_month = start_week
                new_date = datetime_object
                while(new_date <= cur_date):
                    if (new_month - start_month) == int(grResponse2['result'][i]['repeat_every']):
                        start_month = new_month
                        if new_month == cur_month:
                            listGR.append(grResponse2['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(month=grResponse2['result'][i]['repeat_every'])
                    new_month = new_date.month

            # For never and year frequency

            query.append("""SELECT gr_title
                                    , user_id
                                    , gr_unique_id
                                    , start_day_and_time
                                    , repeat_frequency
                                    , repeat_every
                                FROM goals_routines
                            WHERE `repeat` = 'TRUE'
                                    AND repeat_ends = 'never'
                                    AND repeat_frequency = 'year' and user_id = \'""" + user_id + """\';""")
            
            grResponse3 = execute(query[3], 'get', conn)


            for i in range(len(grResponse3['result'])):
                datetime_str = grResponse3['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                start_year = datetime_object.year
                new_year = start_year
                new_date = datetime_object
                while(new_date <= cur_date):
                    if (new_year - start_year) == int(grResponse3['result'][i]['repeat_every']):
                        start_year = new_year
                        if cur_year == new_year:
                            listGR.append(grResponse3['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(year=grResponse3['result'][i]['repeat_every'])
                    new_year = new_date.year

            # For after and day frequency

            query.append("""SELECT gr_title
                            , user_id
                            , gr_unique_id
                            , start_day_and_time
                            , repeat_frequency
                            , repeat_occurences
                            , repeat_every from goals_routines
                        where `repeat` = 'TRUE' and repeat_ends = 'after' and repeat_frequency = 'day'
                        and user_id = \'""" + user_id + """\';""")
            
            grResponse4 = execute(query[4], 'get', conn)

            for i in range(len(grResponse4['result'])):
                datetime_str = grResponse4['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                new_date = datetime_object
                occurence = 1
                while new_date <= cur_date and occurence < int(grResponse4['result'][i]['repeat_occurences']):
                    if(new_date == cur_date):
                        listGR.append(grResponse4['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(days=grResponse4['result'][i]['repeat_every'])
                    occurence += 1

            # For after and week frequency

            query.append("""SELECT gr_unique_id
                                    , start_day_and_time
                                    , repeat_every
                                    , repeat_occurences
                                from (SELECT gr_title
                                        , user_id
                                        , gr_unique_id
                                        , start_day_and_time
                                        , repeat_frequency
                                        , repeat_every
                                        , repeat_occurences
                                        , substring_index(substring_index(repeat_week_days, ';', id), ';', -1) as week_days
                                    FROM goals_routines
                                            JOIN numbers ON char_length(repeat_week_days) - char_length(replace(repeat_week_days, ';', '')) >= id - 1
                                    where `repeat` = 'TRUE'
                                        and repeat_ends = 'after'
                                        and repeat_frequency = 'week') temp
                                where dayname(curdate()) = week_days and user_id = \'""" + user_id + """\';""")

            grResponse5 = execute(query[5], 'get', conn)

            for i in range(len(grResponse5['result'])):
                datetime_str = grResponse5['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                start_week = datetime_object.isocalendar()[1]
                new_week = start_week
                new_date = datetime_object
                occurence = 1
                while new_date <= cur_date and occurence < int(grResponse5['result'][i]['repeat_occurences']):
                    if (new_week - start_week) == int(grResponse5['result'][i]['repeat_every']):
                        start_week = new_week
                        occurence += 1
                        if (new_week == cur_week):
                            listGR.append(grResponse5['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(weeks=grResponse5['result'][i]['repeat_every'])
                    new_week = new_date.isocalendar()[1]

            # For after and month frequency

            query.append("""SELECT gr_title
                                    , user_id
                                    , gr_unique_id
                                    , start_day_and_time
                                    , repeat_frequency
                                    , repeat_every
                                    , repeat_occurences
                                FROM goals_routines
                            WHERE `repeat` = 'TRUE'
                                    AND repeat_ends = 'after'
                                    AND repeat_frequency = 'month' and user_id = \'""" + user_id + """\';""")
            
            grResponse6 = execute(query[6], 'get', conn)

            for i in range(len(grResponse6['result'])):
                datetime_str = grResponse6['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                start_month = datetime_object.month
                new_month = start_week
                new_date = datetime_object
                occurence = 1
                while new_date <= cur_date and occurence < int(grResponse6['result'][i]['repeat_occurences']):
                    if (new_month - start_month) == int(grResponse6['result'][i]['repeat_every']):
                        start_month = new_month
                        occurence += 1
                        if new_month == cur_month:
                            listGR.append(grResponse6['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(month=grResponse6['result'][i]['repeat_every'])
                    new_month = new_date.month

            # For after and year frequency

            query.append("""SELECT gr_title
                                    , user_id
                                    , gr_unique_id
                                    , start_day_and_time
                                    , repeat_frequency
                                    , repeat_every
                                    , repeat_occurences
                                FROM goals_routines
                            WHERE `repeat` = 'TRUE'
                                    AND repeat_ends = 'after'
                                    AND repeat_frequency = 'year' and user_id = \'""" + user_id + """\';""")
            
            grResponse7 = execute(query[7], 'get', conn)

            for i in range(len(grResponse7['result'])):
                datetime_str = grResponse7['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                start_year = datetime_object.year
                new_year = start_year
                new_date = datetime_object
                occurence = 1
                while(new_date <= cur_date) and occurence < int(grResponse7['result'][i]['repeat_occurences']):
                    if (new_year - start_year) == int(grResponse3['result'][i]['repeat_every']):
                        start_year = new_year
                        occurence += 1
                        if cur_year == new_year:
                            listGR.append(grResponse7['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(year=grResponse7['result'][i]['repeat_every'])
                    new_year = new_date.year

            # For on and day frequency

            query.append("""SELECT gr_title
                            , user_id
                            , gr_unique_id
                            , start_day_and_time
                            , repeat_frequency
                            , repeat_occurences
                            , repeat_ends_on
                            , repeat_every from goals_routines
                        where `repeat` = 'TRUE' and repeat_ends = 'on' and repeat_frequency = 'day'
                        and user_id = \'""" + user_id + """\';""")

            grResponse8 = execute(query[8], 'get', conn)

            for i in range(len(grResponse8['result'])):
                datetime_str = grResponse8['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                end_datetime = grResponse8['result'][i]['repeat_ends_on']
                end_datetime = end_datetime.replace(" GMT-0700 (Pacific Daylight Time)", "")
                end_datetime_object = datetime.strptime(end_datetime, "%a %b %d %Y %H:%M:%S").date()
                new_date = datetime_object
            
                while(new_date <= cur_date and cur_date <= end_datetime_object):
                    if(new_date == cur_date):
                        listGR.append(grResponse8['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(days=grResponse8['result'][i]['repeat_every'])

            
            # For on and week frequency

            query.append("""SELECT gr_unique_id
                                    , start_day_and_time
                                    , repeat_every
                                    , repeat_ends_on
                                from (SELECT gr_title
                                        , user_id
                                        , gr_unique_id
                                        , start_day_and_time
                                        , repeat_frequency
                                        , repeat_every
                                        , repeat_ends_on
                                        , substring_index(substring_index(repeat_week_days, ';', id), ';', -1) as week_days
                                    FROM goals_routines
                                            JOIN numbers ON char_length(repeat_week_days) - char_length(replace(repeat_week_days, ';', '')) >= id - 1
                                    where `repeat` = 'TRUE'
                                        and repeat_ends = 'on'
                                        and repeat_frequency = 'week') temp
                                where dayname(curdate()) = week_days and user_id = \'""" + user_id + """\';""")


            grResponse9 = execute(query[9], 'get', conn)

            for i in range(len(grResponse9['result'])):
                datetime_str = grResponse9['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                end_datetime = grResponse9['result'][i]['repeat_ends_on']
                end_datetime = end_datetime.replace(" GMT-0700 (Pacific Daylight Time)", "")
                end_datetime_object = datetime.strptime(end_datetime, "%a %b %d %Y %H:%M:%S").date()
                start_week = datetime_object.isocalendar()[1]
                new_week = start_week
                new_date = datetime_object
                occurence = 1
                while(new_date <= cur_date and cur_date <= end_datetime_object):
                    if (new_week - start_week) == int(grResponse5['result'][i]['repeat_every']):
                        start_week = new_week
                        occurence += 1
                        if (new_week == cur_week):
                            listGR.append(grResponse9['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(weeks=grResponse9['result'][i]['repeat_every'])
                    new_week = new_date.isocalendar()[1]

            # For on and month frequency

            query.append("""SELECT gr_title
                                    , user_id
                                    , gr_unique_id
                                    , start_day_and_time
                                    , repeat_frequency
                                    , repeat_every
                                    , repeat_ends_on
                                FROM goals_routines
                            WHERE `repeat` = 'True'
                                    AND repeat_ends = 'on'
                                    AND repeat_frequency = 'month' and user_id = \'""" + user_id + """\';""")
            
            grResponse10 = execute(query[10], 'get', conn)

            for i in range(len(grResponse10['result'])):
                datetime_str = grResponse10['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                end_datetime = grResponse10['result'][i]['repeat_ends_on']
                end_datetime = end_datetime.replace(" GMT-0700 (Pacific Daylight Time)", "")
                end_datetime_object = datetime.strptime(end_datetime, "%a %b %d %Y %H:%M:%S").date()
                start_month = datetime_object.month
                new_month = start_week
                new_date = datetime_object
                while(new_date <= cur_date and cur_date <= end_datetime):
                    if (new_month - start_month) == int(grResponse10['result'][i]['repeat_every']):
                        start_month = new_month
                        occurence += 1
                        if new_month == cur_month:
                            listGR.append(grResponse10['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(month=grResponse10['result'][i]['repeat_every'])
                    new_month = new_date.month

            # For on and year frequency

            query.append("""SELECT gr_title
                                    , user_id
                                    , gr_unique_id
                                    , start_day_and_time
                                    , repeat_frequency
                                    , repeat_every
                                    , repeat_ends_on
                                FROM goals_routines
                            WHERE `repeat` = 'True'
                                    AND repeat_ends = 'on'
                                    AND repeat_frequency = 'year' and user_id = \'""" + user_id + """\';""")
            
            grResponse11 = execute(query[11], 'get', conn)

            for i in range(len(grResponse11['result'])):
                datetime_str = grResponse11['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                end_datetime = grResponse11['result'][i]['repeat_ends_on']
                end_datetime = end_datetime.replace(" GMT-0700 (Pacific Daylight Time)", "")
                end_datetime_object = datetime.strptime(end_datetime, "%a %b %d %Y %H:%M:%S").date()
                start_year = datetime_object.year
                new_year = start_year
                new_date = datetime_object
                while(new_date <= cur_date and cur_date <= end_datetime_object):
                    if (new_year - start_year) == int(grResponse11['result'][i]['repeat_every']):
                        start_year = new_year
                        occurence += 1
                        if cur_year == new_year:
                            listGR.append(grResponse11['result'][i]['gr_unique_id'])
                    new_date = new_date + timedelta(year=grResponse11['result'][i]['repeat_every'])
                    new_year = new_date.year

            query.append("""SELECT gr_unique_id
                                    , start_day_and_time
                                FROM goals_routines
                            WHERE `repeat` = 'FALSE' and user_id = \'""" + user_id + """\';""")
            
            grResponse12 = execute(query[12], 'get', conn)

            for i in range(len(grResponse12['result'])):
                datetime_str = grResponse12['result'][i]['start_day_and_time']
                datetime_str = datetime_str.replace(",", "")
                datetime_object = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').date()
                if(datetime_object == cur_date):
                        listGR.append(grResponse12['result'][i]['gr_unique_id'])

            i  = len(query) - 1
            
            for id_gr in listGR:
                if id_gr in items.keys():

                    if (type(items[id_gr][0]['display_date']) == list):
                        items[id_gr][0]['display_date'].append(str(cur_date))
                    else: 
                        items[id_gr][0]['display_date'] = [items[id_gr][0]['display_date'], (str(cur_date))]

                else:
                    query.append("""SELECT * FROM goals_routines WHERE gr_unique_id = \'""" + id_gr + """\';""")
                    i += 1
                    new_item = (execute(query[i], 'get', conn))['result']
                    for y in range(len(new_item)):
                        new_item[y]['display_date'] = (str(cur_date))
                    items.update({id_gr:new_item})

        return items

# Add new people
class CreateNewPeople(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            ts  = getNow()
            data = request.get_json(force=True)

            user_id = data['user_id']
            email_id = data['email_id']
            name = data['first_name']
            last_name = data['last_name']
            employer = data['employer']
            relation_type = data['relationship']
            phone_number = data['phone_number']
            picture = data['picture']
            ta_people_type = 'people'
            important = 'False'

            email_list = []
            
            if picture != '':
                have_pic = 'TRUE'
            else:
                have_pic = 'FALSE'

            list = name.split()
            first_name = list[0]
            if len(list) == 1:
                last_name = ''
            else:
                last_name = list[1]

            query = ["Call get_relation_id;"]
            NewRelationIDresponse = execute(query[0], 'get', conn)
            NewRelationID = NewRelationIDresponse['result'][0]['new_id']

            query.append("""SELECT ta_email_id FROM ta_people;""")
            peopleResponse = execute(query[1], 'get', conn)
            email_list = []

            # userIDResponse = execute("SELECT user_unique_id from users where email_id = \'""" + email + """\';""", 'get', conn)
            # user_id = userIDResponse['result'][0]['user_unique_id']
            for i in range(len(peopleResponse['result'])):
                email_id_existing = peopleResponse['result'][i]['ta_email_id']
                email_list.append(email_id_existing)

            if email_id in email_list:
                
                typeResponse = execute("""SELECT ta_unique_id from ta_people WHERE ta_email_id = \'""" + email_id + """\';""", 'get', conn)
               
                relationResponse = execute("""SELECT id from relationship 
                                            WHERE ta_people_id = \'""" + typeResponse['result'][0]['ta_unique_id'] + """\'
                                            AND user_uid = \'""" + user_id + """\';""", 'get', conn)

                if len(relationResponse['result']) > 0:
                   
                    execute("""UPDATE relationship
                                SET r_timestamp = \'""" + str(ts) + """\'
                                , relation_type = \'""" + relation_type + """\'
                                , ta_have_pic = \'""" + str(have_pic).title() + """\'
                                , ta_picture = \'""" + picture + """\'
                                , important = \'""" + str(important).title() + """\'
                                WHERE user_uid = \'""" + user_id + """\' AND 
                                ta_people_id = \'""" + typeResponse['result'][0]['ta_unique_id'] + """\'""", 'post', conn)

                else:
                    
                    execute("""INSERT INTO relationship(
                        id
                        , r_timestamp
                        , ta_people_id
                        , user_uid
                        , relation_type
                        , ta_have_pic
                        , ta_picture
                        , important
                        , advisor)
                        VALUES ( 
                            \'""" + NewRelationID + """\'
                            , \'""" + str(ts) + """\'
                            , \'""" + typeResponse['result'][0]['ta_unique_id'] + """\'
                            , \'""" + user_id + """\'
                            , \'""" + relation_type + """\'
                            , \'""" + str(have_pic).title() + """\'
                            , \'""" + picture + """\'
                            , \'""" + str(important).title() + """\'
                            , \'""" + str(0) + """\')""", 'post', conn)

            else:
                NewPeopleIDresponse = execute("CALL get_ta_people_id;", 'get', conn)
                NewPeopleID = NewPeopleIDresponse['result'][0]['new_id']
                print(NewPeopleID)
                execute("""INSERT INTO ta_people(
                                        ta_unique_id
                                        , ta_timestamp
                                        , ta_email_id
                                        , ta_first_name
                                        , ta_last_name
                                        , employer
                                        , password_hashed
                                        , ta_phone_number)
                                        VALUES ( 
                                            \'""" + NewPeopleID + """\'
                                            , \'""" + ts + """\'
                                            , \'""" + email_id + """\'
                                            , \'""" + first_name + """\'
                                            , \'""" + last_name + """\'
                                            , \'""" + employer + """\'
                                            , \'""" + '' + """\'
                                            , \'""" + phone_number + """\')""", 'post', conn)

                execute("""INSERT INTO relationship(
                                        id
                                        , r_timestamp
                                        , ta_people_id
                                        , user_uid
                                        , relation_type
                                        , ta_have_pic
                                        , ta_picture
                                        , important
                                        , advisor)
                                        VALUES ( 
                                            \'""" + NewRelationID + """\'
                                            , \'""" + str(ts) + """\'
                                            , \'""" + NewPeopleID + """\'
                                            , \'""" + user_id + """\'
                                            , \'""" + relation_type + """\'
                                            , \'""" + str(have_pic).title() + """\'
                                            , \'""" + picture + """\'
                                            , \'""" + str(important).title() + """\'
                                            , \'""" + str(0) + """\')""", 'post', conn)

                
            response['message'] = 'successful'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Delete Important people
class DeletePeople(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            user_id = data['user_id']
            ta_people_id = data['ta_people_id']
            
            
            execute("""DELETE FROM relationship
                        WHERE user_uid = \'""" + user_id + """\' AND
                        ta_people_id = \'""" + ta_people_id + """\' ;""", 'post', conn)
        
            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Update time and time zone
class UpdateTime(Resource):
    def post(self, user_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            time_zone = data['time_zone']
            morning_time = data['morning_time']
            afternoon_time = data['afternoon_time']
            evening_time = data['evening_time']
            night_time = data['night_time']
            day_start = data['day_start']
            day_end = data['day_end']
            
            
            execute(""" UPDATE users
                        SET 
                        time_zone = \'""" + time_zone + """\'
                        , morning_time = \'""" + morning_time + """\'
                        , afternoon_time = \'""" + afternoon_time + """\'
                        , evening_time = \'""" + evening_time + """\'
                        , night_time = \'""" + night_time + """\'
                        , day_start = \'""" + day_start + """\'
                        , day_end = \'""" + day_end + """\'
                        WHERE user_unique_id = \'""" + user_id + """\';""", 'post', conn)
        
            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Update time and time zone
class CurrentStatus(Resource):
    def get(self, user_id):    
        response = {}
        items = {}

        try:
            conn = connect()
           
            
            goal_response = execute("""SELECT gr_unique_id, gr_title, is_in_progress, is_complete FROM goals_routines 
                        WHERE user_id = \'""" + user_id + """\';""", 'get', conn)

            for i in range(len(goal_response['result'])):
                at_response = execute(""" SELECT at_unique_id, at_title, is_in_progress, is_complete FROM actions_tasks 
                                WHERE goal_routine_id =  \'""" + goal_response['result'][i]['gr_unique_id'] + """\';""", 'get', conn)

                if len(at_response['result']) > 0:
                   
                    goal_response['result'][i]['actions_tasks'] = at_response['result']
                 

            response['message'] = 'successful'
            response['result'] = goal_response

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# Update time and time zone
class Reset(Resource):
    def post(self, gr_unique_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
           
            
            
            execute(""" UPDATE goals_routines
                        SET 
                        is_in_progress = \'""" + 'False' + """\'
                        , is_complete = \'""" + 'False' + """\'
                        WHERE gr_unique_id = \'""" + gr_unique_id + """\';""", 'post', conn)

            execute(""" UPDATE actions_actions
                        SET 
                        is_in_progress = \'""" + 'False' + """\'
                        , is_complete = \'""" + 'False' + """\'
                        WHERE goal_routine_id = \'""" + gr_unique_id + """\';""", 'post', conn)


            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# New TA signup
class NewTA(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            ts = getNow()

            email_id = data['email_id']
            password = data['password']
            first_name = data['first_name']
            last_name = data['last_name']
            phone_number = data['phone_number']
            employer = data['employer']


            ta_id_response = execute("""SELECT ta_unique_id, password_hashed FROM ta_people
                                            WHERE ta_email_id = \'""" +email_id+ """\';""", 'get', conn)
            
            if len(ta_id_response['result']) > 0:
                response['message'] = "Email ID already exists."
            
            else:
            
                salt = os.urandom(32)
            
                dk = hashlib.pbkdf2_hmac('sha256',  password.encode('utf-8') , salt, 100000, dklen=128)
                key = (salt + dk).hex()

                new_ta_id_response = execute("CALL get_ta_people_id;", 'get', conn)
                new_ta_id = new_ta_id_response['result'][0]['new_id']

                execute("""INSERT INTO ta_people(
                                            ta_unique_id
                                            , ta_timestamp
                                            , ta_email_id
                                            , ta_first_name
                                            , ta_last_name
                                            , employer
                                            , password_hashed
                                            , ta_phone_number)                                        
                                            VALUES ( 
                                                \'""" + new_ta_id + """\'
                                                , \'""" + ts + """\'
                                                , \'""" + email_id + """\'
                                                , \'""" + first_name + """\'
                                                , \'""" + last_name + """\'
                                                , \'""" + employer + """\'
                                                , \'""" + key + """\'
                                                , \'""" + phone_number + """\')""", 'post', conn)
                response['message'] = 'successful'
                response['result'] = new_ta_id

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# TA social sign up
class TASocialSignUP(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            ts = getNow()

            email_id = data['email_id']
            first_name = data['first_name']
            last_name = data['last_name']
            phone_number = data['phone_number']
            employer = data['employer']

            ta_id_response = execute("""SELECT ta_unique_id, password_hashed FROM ta_people
                                            WHERE ta_email_id = \'""" +email_id+ """\';""", 'get', conn)
            
            if len(ta_id_response['result']) > 0:
                response['message'] = "Email ID already exists."
           
            else: 
                new_ta_id_response = execute("CALL get_ta_people_id;", 'get', conn)
                new_ta_id = new_ta_id_response['result'][0]['new_id']

                execute("""INSERT INTO ta_people(
                                                ta_unique_id
                                                , ta_timestamp
                                                , ta_email_id
                                                , ta_first_name
                                                , ta_last_name
                                                , employer
                                                , ta_phone_number)
                                            VALUES ( 
                                                \'""" + new_ta_id + """\'
                                                , \'""" + ts + """\'
                                                , \'""" + email_id + """\'
                                                , \'""" + first_name + """\'
                                                , \'""" + last_name + """\'
                                                , \'""" + employer + """\'
                                                , \'""" + phone_number + """\')""", 'post', conn)
                response['message'] = 'successful'
                response['result'] = new_ta_id

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Existing TA login
class TALogin(Resource):
    def get(self, email_id, password):    
        response = {}
        items = {}

        try:
            conn = connect()
            # data = request.get_json(force=True)
            # email_id = data['email_id']
            # password = data['password']
            temp = False
            emails = execute("""SELECT ta_email_id from ta_people;""", 'get', conn)
            for i in range(len(emails['result'])):
                email = emails['result'][i]['ta_email_id']
                if email == email_id:
                    temp = True
            if temp == True:
                emailIDResponse = execute("""SELECT ta_unique_id, password_hashed from ta_people where ta_email_id = \'""" + email_id + """\'""", 'get', conn)
                password_storage = emailIDResponse['result'][0]['password_hashed']

                original = bytes.fromhex(password_storage)
                salt_from_storage = original[:32] 
                key_from_storage = original[32:]

                new_dk = hashlib.pbkdf2_hmac('sha256',  password.encode('utf-8') , salt_from_storage, 100000, dklen=128)
                
                if key_from_storage == new_dk:
                    response['result'] = emailIDResponse['result'][0]['ta_unique_id']
                    response['message'] = 'Correct Email and Password'
                else:
                    response['result'] = False  
                    response['message'] = 'Wrong Password'
  

            if temp == False:
                response['result'] = False 
                response['message'] = 'Email ID doesnt exist'
           
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# TA social login
class TASocialLogin(Resource):
    def get(self, email_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            # data = request.get_json(force=True)
            # email_id = data['email_id']
            # password = data['password']
            temp = False
            emails = execute("""SELECT ta_unique_id, ta_email_id from ta_people;""", 'get', conn)
            for i in range(len(emails['result'])):
                email = emails['result'][i]['ta_email_id']
                if email == email_id:
                    temp = True
                    ta_unique_id = emails['result'][i]['ta_unique_id']
            if temp == True:
                
                response['result'] = ta_unique_id
                response['message'] = 'Correct Email'
    
            if temp == False:
                response['result'] = False 
                response['message'] = 'Email ID doesnt exist'
           
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Creating new user
class CreateNewUser(Resource):
    def post(self):    
        response = {}
        items = {}
        timestamp = getNow()
        try:
            conn = connect()
            data = request.get_json(force=True)

           
            email_id = data['email_id']
            google_auth_token = data['google_auth_token']
            google_refresh_token = data['google_refresh_token']

            user_id_response = execute("""SELECT user_unique_id FROM users
                                            WHERE user_email_id = \'""" +email_id+ """\';""", 'get', conn)
            
            if len(user_id_response['result']) > 0:
                response['message'] = 'User already exists'

            else:
                user_id_response = execute("CAll get_user_id;", 'get', conn)
                new_user_id = user_id_response['result'][0]['new_id']


                execute("""INSERT INTO users(
                                user_unique_id
                                , user_timestamp
                                , user_email_id
                                , google_auth_token
                                , google_refresh_token
                                , user_have_pic
                                , user_picture
                                , user_social_media)
                            VALUES ( 
                                \'""" + new_user_id + """\'
                                , \'""" + timestamp + """\'
                                , \'""" + email_id + """\'
                                , \'""" + google_auth_token + """\'
                                , \'""" + google_refresh_token + """\'
                                , \'""" + 'False' + """\'
                                , \'""" + '' + """\'
                                , \'""" + 'GOOGLE' + """\')""", 'post', conn)
                

                response['message'] = 'successful'
                response['result'] = new_user_id

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Update new user
class UpdateAboutMe(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()

            data = request.get_json(force=True)

            timestamp = getNow()

            people_id = []
            people_have_pic = []
            people_name = []
            people_pic = []
            people_relationship = []
            people_important = []
            people_user_id = []
            people_phone_number = []

            relation_type = []
            user_id = data['user_id']
            first_name = data['first_name']
            last_name = data['last_name']
            have_pic = data['have_pic']
            message_card = data['message_card']
            message_day = data['message_day']
            picture = data['picture']

            # user_photo_url = helper_upload_meal_img(picture, user_id)

            if len(data['people']) > 0:
                for i in range(len(data['people'])):
                    people_id.append(data['people'][i]['ta_people_id'])
                    people_name.append(data['people'][i]['name'])
                    people_relationship.append(data['people'][i]['relationship'])
                    people_phone_number.append(data['people'][i]['phone_number'])
                    people_important.append(data['people'][i]['important'])
                    people_have_pic.append(data['people'][i]['have_pic'])
                    people_pic.append(data['people'][i]['pic'])

            afternoon_time = data['timeSettings']["afternoon"]
            day_end = data['timeSettings']["dayEnd"]
            day_start = data['timeSettings']["dayStart"]
            evening_time = data['timeSettings']["evening"]
            morning_time = data['timeSettings']["morning"]
            night_time = data['timeSettings']["night"]
            time_zone = data['timeSettings']["timeZone"]

            # Updating user data
            execute("""UPDATE  users
                            SET 
                                user_first_name = \'""" + first_name + """\'
                                , user_have_pic = \'""" + str(have_pic).title() + """\'
                                , user_picture = \'""" + str(picture) + """\'
                                , message_card = \'""" + str(message_card) + """\'
                                , message_day = \'""" + str(message_day) + """\'
                                , user_last_name =  \'""" + last_name + """\'
                                , time_zone = \'""" + str(time_zone) + """\'
                                , morning_time = \'""" + str(morning_time) + """\'
                                , afternoon_time = \'""" + str(afternoon_time) + """\'
                                , evening_time = \'""" + str(evening_time) + """\'
                                , night_time = \'""" + str(night_time) + """\'
                                , day_start = \'""" + str(day_start) + """\'
                                , day_end = \'""" + str(day_end) + """\'
                            WHERE user_unique_id = \'""" + user_id + """\' ;""", 'post', conn)

            for i in range(len(people_id)):
                list = people_name[i].split(" ", 1)
                first_name = list[0]
                if len(list) == 1:
                    last_name = ''
                else:
                    last_name = list[1]

                execute("""UPDATE  ta_people
                            SET 
                                ta_first_name = \'""" + first_name + """\'
                                , ta_timestamp = \'""" + timestamp + """\'
                                , ta_last_name = \'""" + last_name + """\'
                                , ta_phone_number =  \'""" + str(people_phone_number[i]) + """\'
                            WHERE ta_unique_id = \'""" + people_id[i] + """\' ;""", 'post', conn)

                relationResponse = execute("""SELECT id FROM relationship 
                            WHERE ta_people_id = \'""" + people_id[i] + """\' 
                            and user_uid = \'""" + user_id + """\';""", 'get', conn)
                                            
                if len(relationResponse['result']) > 0:
                
                    items = execute("""UPDATE  relationship
                                    SET 
                                        r_timestamp = \'""" + timestamp + """\'
                                        , relation_type = \'""" + people_relationship[i] + """\'
                                        , ta_have_pic =  \'""" + str(people_have_pic[i]).title() + """\'
                                        , ta_picture = \'""" + people_pic[i] + """\'
                                        , important = \'""" + str(people_important[i]).title() + """\'
                                    WHERE ta_people_id = \'""" + people_id[i] + """\' 
                                    and user_uid = \'""" + user_id + """\' ;""", 'post', conn)

                if len(relationResponse['result']) == 0:
                    print("P")
                    NewRelationIDresponse = execute("Call get_relation_id;", 'get', conn)
                    NewRelationID = NewRelationIDresponse['result'][0]['new_id']

                    execute("""INSERT INTO relationship
                                        (id
                                        , ta_people_id
                                        , user_uid
                                        , r_timestamp
                                        , relation_type
                                        , ta_have_pic
                                        , ta_picture
                                        , important
                                        , advisor)
                                        VALUES 
                                        ( \'""" + NewRelationID + """\'
                                        , \'""" + people_id[i] + """\'
                                        , \'""" + user_id + """\'
                                        , \'""" + timestamp + """\'
                                        , \'""" + people_relationship[i] + """\'
                                        , \'""" + str(people_have_pic[i]).title() + """\'
                                        , \'""" + people_pic[i] + """\'
                                        , \'""" + str(people_important[i]).title() + """\'
                                        , \'""" + str(0) + """\');""", 'post', conn)
            
            response['message'] = 'successful'
            response['result'] = 'Important people changed'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Update new user
class UpdateAboutMe2(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()

            timestamp = getNow()

            people_id = []
            people_have_pic = []
            people_name = []
            people_pic = []
            people_relationship = []
            people_important = []
            people_user_id = []
            people_phone_number = []
            relation_type = []

            user_id = request.form.get('user_id')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            have_pic = request.form.get('have_pic')
            message_card =  request.form.get('message_card')
            message_day = request.form.get('message_day')
            picture = request.files.get('picture')
            people = request.form.get('people')
            time_settings = request.form.get("timeSettings")

            user_photo_url = helper_upload_meal_img(picture, user_id)

            people = json.loads(people)
            if len(people) > 0:
                for i in range(len(people)):
                    people_id.append(people[i]['ta_people_id'])
                    people_name.append(people[i]['name'])
                    people_relationship.append(people[i]['relationship'])
                    people_phone_number.append(people[i]['phone_number'])
                    people_important.append(people[i]['important'])
                    people_have_pic.append(people[i]['have_pic'])
                    people_pic.append(people[i]['pic'])

            time_settings = json.loads(time_settings)
            afternoon_time = time_settings["afternoon"]
            day_end = time_settings["dayEnd"]
            day_start = time_settings["dayStart"]
            evening_time = time_settings["evening"]
            morning_time = time_settings["morning"]
            night_time = time_settings["night"]
            time_zone = time_settings["timeZone"]

            # Updating user data
            execute("""UPDATE  users
                            SET 
                                user_first_name = \'""" + first_name + """\'
                                , user_timestamp = \'""" + timestamp + """\'
                                , user_have_pic = \'""" + str(have_pic).title() + """\'
                                , user_picture = \'""" + str(user_photo_url) + """\'
                                , message_card = \'""" + str(message_card) + """\'
                                , message_day = \'""" + str(message_day) + """\'
                                , user_last_name =  \'""" + last_name + """\'
                                , time_zone = \'""" + str(time_zone) + """\'
                                , morning_time = \'""" + str(morning_time) + """\'
                                , afternoon_time = \'""" + str(afternoon_time) + """\'
                                , evening_time = \'""" + str(evening_time) + """\'
                                , night_time = \'""" + str(night_time) + """\'
                                , day_start = \'""" + str(day_start) + """\'
                                , day_end = \'""" + str(day_end) + """\'
                            WHERE user_unique_id = \'""" + user_id + """\' ;""", 'post', conn)
            
            for i in range(len(people_id)):
                list = people_name[i].split(" ", 1)
                first_name = list[0]
                if len(list) == 1:
                    last_name = ''
                else:
                    last_name = list[1]

                execute("""UPDATE  ta_people
                            SET 
                                ta_first_name = \'""" + first_name + """\'
                                , ta_timestamp = \'""" + timestamp + """\'
                                , ta_last_name = \'""" + last_name + """\'
                                , ta_phone_number =  \'""" + str(people_phone_number[i]) + """\'
                            WHERE ta_unique_id = \'""" + people_id[i] + """\' ;""", 'post', conn)

                relationResponse = execute("""SELECT id FROM relationship 
                            WHERE ta_people_id = \'""" + people_id[i] + """\' 
                            and user_uid = \'""" + user_id + """\';""", 'get', conn)
                                            
                if len(relationResponse['result']) > 0:
                
                    items = execute("""UPDATE  relationship
                                    SET 
                                        r_timestamp = \'""" + timestamp + """\'
                                        , relation_type = \'""" + people_relationship[i] + """\'
                                        , ta_have_pic =  \'""" + str(people_have_pic[i]).title() + """\'
                                        , ta_picture = \'""" + people_pic[i] + """\'
                                        , important = \'""" + str(people_important[i]).title() + """\'
                                    WHERE ta_people_id = \'""" + people_id[i] + """\' 
                                    and user_uid = \'""" + user_id + """\' ;""", 'post', conn)

                if len(relationResponse['result']) == 0:
                    NewRelationIDresponse = execute("Call get_relation_id;", 'get', conn)
                    NewRelationID = NewRelationIDresponse['result'][0]['new_id']

                    execute("""INSERT INTO relationship
                                        (id
                                        , ta_people_id
                                        , user_uid
                                        , r_timestamp
                                        , relation_type
                                        , ta_have_pic
                                        , ta_picture
                                        , important
                                        , advisor)
                                        VALUES 
                                        ( \'""" + NewRelationID + """\'
                                        , \'""" + people_id[i] + """\'
                                        , \'""" + user_id + """\'
                                        , \'""" + timestamp + """\'
                                        , \'""" + people_relationship[i] + """\'
                                        , \'""" + str(people_have_pic[i]).title() + """\'
                                        , \'""" + people_pic[i] + """\'
                                        , \'""" + str(people_important[i]).title() + """\'
                                        , \'""" + str(0) + """\');""", 'post', conn)
            
            response['message'] = 'successful'
            response['result'] = 'Update to about me successful'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Update new user
class UpdateNameTimeZone(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            timestamp = getNow()
            conn = connect()
            data = request.get_json(force=True)
            # with open('/data.txt', 'w+') as outfile:
            #     json.dump(data, outfile)
            # ta_email = data['ta_email']


            ta_people_id = data['ta_people_id']
            user_unique_id = data['user_unique_id']
            first_name = data['first_name']
            last_name = data['last_name']
            time_zone = data["timeZone"]

            items = execute("""UPDATE  users
                            SET 
                                user_first_name = \'""" + first_name + """\'
                                , user_last_name =  \'""" + last_name + """\'
                                , time_zone = \'""" + time_zone + """\'
                                , user_timestamp = \'""" + timestamp + """\'
                                , morning_time = \'""" + '06:00' + """\'
                                , afternoon_time = \'""" + '11:00' + """\'
                                , evening_time = \'""" + '16:00' + """\'
                                , night_time = \'""" + '21:00' + """\'
                                , day_start = \'""" + '00:00' + """\'
                                , day_end = \'""" + '23:59' + """\'
                            WHERE user_unique_id = \'""" + user_unique_id + """\' ;""", 'post', conn)

            NewRelationIDresponse = execute("Call get_relation_id;", 'get', conn)
            NewRelationID = NewRelationIDresponse['result'][0]['new_id']

            execute("""INSERT INTO relationship
                        (id
                        , r_timestamp
                        , ta_people_id
                        , user_uid
                        , relation_type
                        , ta_have_pic
                        , ta_picture
                        , important
                        , advisor)
                        VALUES 
                        ( \'""" + NewRelationID + """\'
                        , \'""" + timestamp + """\'
                        , \'""" + ta_people_id + """\'
                        , \'""" + user_unique_id + """\'
                        , \'""" + 'advisor' + """\'
                        , \'""" + 'False' + """\'
                        , \'""" + '' + """\'
                        , \'""" + 'False' + """\'
                        , \'""" + str(1) + """\');""", 'post', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

#User login
class UserLogin(Resource):
    def get(self, email_id):    
        response = {}
        items = {}

        try:
            conn = connect()
            
            temp = False
            emails = execute("""SELECT user_unique_id, user_email_id from users;""", 'get', conn)
            for i in range(len(emails['result'])):
                email = emails['result'][i]['user_email_id']
                if email == email_id:
                    temp = True
                    user_unique_id = emails['result'][i]['user_unique_id']
            if temp == True:
                
                response['result'] = user_unique_id
    
            if temp == False:
                response['result'] = False 
                response['message'] = 'Email ID doesnt exist'
           
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# returns users token
class Usertoken(Resource):
    def get(self, user_id = None):
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
                    
            query = """SELECT user_unique_id
                                , user_email_id
                                , google_auth_token
                                , google_refresh_token
                        FROM
                        users WHERE user_unique_id = \'""" + user_id + """\';"""
            
            items = execute(query, 'get', conn)
            print(items)
            response['message'] = 'successful'
            response['email_id'] = items['result'][0]['user_email_id']
            response['google_auth_token'] = items['result'][0]['google_auth_token']
            response['google_refresh_token'] = items['result'][0]['google_refresh_token']

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# # Creating new user
# class CreateNewUsers(Resource):
#     def post(self):    
#         response = {}
#         items = {}
#         timestamp = getNow()
#         try:
#             conn = connect()
#             data = request.get_json(force=True)

#             ta_people_id = data["ta_people_id"]
#             email_id = data['email_id']
#             google_auth_token = data['google_auth_token']
#             google_refresh_token = data['google_refresh_token']
#             first_name = data['first_name']
#             last_name = data['last_name']
#             time_zone = data["timeZone"]

#             UserIDResponse = execute("CAll get_user_id;", 'get', conn)
#             NewUserID = UserIDResponse['result'][0]['new_id']
            
#             execute("""INSERT INTO users(
#                             user_unique_id
#                             , user_timestamp
#                             , user_email_id
#                             , user_first_name
#                             , user_last_name
#                             , google_auth_token
#                             , google_refresh_token)
#                         VALUES ( 
#                             \'""" + NewUserID + """\'
#                             , \'""" + timestamp + """\'
#                             , \'""" + email_id + """\'
#                             , \'""" + first_name + """\'
#                             , \'""" + last_name + """\'
#                             , \'""" + google_auth_token + """\'
#                             , \'""" + google_refresh_token + """\')""", 'post', conn)

#             NewRelationIDresponse = execute("Call get_relation_id;", 'get', conn)
#             NewRelationID = NewRelationIDresponse['result'][0]['new_id']

#             print(NewRelationID)
#             execute("""INSERT INTO relationship
#                         (id
#                         , r_timestamp
#                         , ta_people_id
#                         , user_uid
#                         , relation_type
#                         , ta_have_pic
#                         , ta_picture
#                         , important)
#                         VALUES 
#                         ( \'""" + NewRelationID + """\'
#                         , \'""" + timestamp + """\'
#                         , \'""" + ta_people_id + """\'
#                         , \'""" + NewUserID + """\'
#                         , \'""" + 'advisor' + """\'
#                         , \'""" + 'FALSE' + """\'
#                         , \'""" + '' + """\'
#                         , \'""" + 'FALSE' + """\');""", 'post', conn)
#             response['message'] = 'successful'
#             return response, 200
#         except:
#             raise BadRequest('Request failed, please try again later.')
#         finally:
#             disconnect(conn)

# Add coordinates
class AddCoordinates(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            x = data['x']
            y = data['y']
            z = data['z']
            timestamp = data['timestamp']
            
            execute(""" INSERT INTO coordinates
                        (     x
                            , y
                            , z
                            , timestamp)
                            VALUES (
                                \'""" +str(x)+ """\'
                                ,\'""" +str(y)+ """\'
                                , \'""" +str(z)+ """\'
                                , \'""" +str(timestamp)+ """\'
                            );""", 'post', conn)
        
            response['message'] = 'successful'
            response['result'] = "Added in database"

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Add new Goal/Routine of a user
class UpdateGRWatchMobile(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            datetime_completed = data['datetime_completed']
            datetime_started = data['datetime_started']
            id = data['id']
            print(id)
            is_complete = data['is_complete']
            is_in_progress = data['is_in_progress']


            if datetime_started == "":
                query = """UPDATE goals_routines
                            SET 
                                is_complete = \'""" + str(is_complete).title() + """\'
                                ,is_in_progress = \'""" + str(is_in_progress).title() + """\'
                                ,datetime_completed = \'""" + datetime_completed + """\'
                        WHERE gr_unique_id = \'""" +id+ """\';"""
                execute(query, 'post', conn)

            elif datetime_completed == "":
                query = """UPDATE goals_routines
                            SET 
                                is_complete = \'""" + str(is_complete).title() + """\'
                                ,is_in_progress = \'""" + str(is_in_progress).title() + """\'
                                ,datetime_started = \'""" + datetime_started + """\'
                        WHERE gr_unique_id = \'""" +id+ """\';"""
                execute(query, 'post', conn)

            else:
                # Update G/R to database
                query = """UPDATE goals_routines
                                SET 
                                    is_complete = \'""" + str(is_complete).title() + """\'
                                    ,is_in_progress = \'""" + str(is_in_progress).title() + """\'
                                    ,datetime_started = \'""" + datetime_started + """\'
                                    ,datetime_completed = \'""" + datetime_completed + """\'
                            WHERE gr_unique_id = \'""" +id+ """\';"""
                execute(query, 'post', conn)

            response['message'] = 'Update to Goal and Routine was Successful'
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class UpdateATWatchMobile(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            datetime_completed = data['datetime_completed']
            datetime_started = data['datetime_started']
            id = data['id']
            is_complete = data['is_complete']
            is_in_progress = data['is_in_progress']

            if datetime_started == "":
                query = """UPDATE actions_tasks
                            SET  
                                is_complete = \'""" + str(is_complete).title() + """\'
                                , datetime_completed =  \'""" + datetime_completed + """\'
                                WHERE at_unique_id = \'""" +id+ """\';"""
                execute(query, 'post', conn)

            elif datetime_completed == "":
                query = """UPDATE actions_tasks
                            SET  
                                is_complete = \'""" + str(is_complete).title() + """\'
                                , datetime_started = \'""" + datetime_started + """\'
                                WHERE at_unique_id = \'""" +id+ """\';"""
                execute(query, 'post', conn)

            else:

                query = """UPDATE actions_tasks
                            SET  
                                is_complete = \'""" + str(is_complete).title() + """\'
                                , datetime_completed =  \'""" + datetime_completed + """\'
                                , datetime_started = \'""" + datetime_started + """\'
                                WHERE at_unique_id = \'""" +id+ """\';"""
                execute(query, 'post', conn)

            response['message'] = 'Update action and task successful'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# # Creating new user
# class UpdateTokens(Resource):
#     def post(self):    
#         response = {}
#         items = {}
#         timestamp = getNow()
#         try:
#             conn = connect()
#             data = request.get_json(force=True)

           
#             email_id = data['email_id']
#             google_auth_token = data['google_auth_token']
#             google_refresh_token = data['google_refresh_token']

#             user_id_response = execute("""SELECT user_unique_id FROM users
#                                             WHERE user_email_id = \'""" +email_id+ """\';""", 'get', conn)
            
#             if len(user_id_response['result']) > 0:
#                 response['message'] = 'User already exists'

#             else:
#                 user_id_response = execute("CAll get_user_id;", 'get', conn)
#                 new_user_id = user_id_response['result'][0]['new_id']


#                 execute("""INSERT INTO users(
#                                 user_unique_id
#                                 , user_timestamp
#                                 , user_email_id
#                                 , google_auth_token
#                                 , google_refresh_token
#                                 , user_have_pic
#                                 , user_picture)
#                             VALUES ( 
#                                 \'""" + new_user_id + """\'
#                                 , \'""" + timestamp + """\'
#                                 , \'""" + email_id + """\'
#                                 , \'""" + google_auth_token + """\'
#                                 , \'""" + google_refresh_token + """\'
#                                 , \'""" + 'False' + """\'
#                                 , \'""" + '' + """\')""", 'post', conn)

#                 response['message'] = 'successful'
#                 response['result'] = new_user_id

#             return response, 200
#         except:
#             raise BadRequest('Request failed, please try again later.')
#         finally:
#             disconnect(conn)

class Login(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            email = data['email']
            social_id = data['social_id']
            # password = data.get('password')
            refresh_token = data.get('mobile_refresh_token')
            access_token = data.get('mobile_access_token')
            signup_platform = data.get('signup_platform')

            if email == "":

                query = """
                        SELECT user_unique_id,
                            user_last_name,
                            user_first_name,
                            user_email_id,
                            user_social_media,
                            google_auth_token,
                            google_refresh_token
                        FROM users
                        WHERE social_id = \'""" + social_id + """\';
                        """
              
                items = execute(query, 'get', conn)
               

            else: 
                query = """
                        SELECT user_unique_id,
                            user_last_name,
                            user_first_name,
                            user_email_id,
                            user_social_media,
                            google_auth_token,
                            google_refresh_token
                        FROM users
                        WHERE user_email_id = \'""" + email + """\';
                        """

              
                items = execute(query, 'get', conn)

            # print('Password', password)
            print(items)

            if items['code'] != 280:
                response['message'] = "Internal Server Error."
                response['code'] = 500
                return response
            elif not items['result']:
                items['message'] = 'User Not Found. Please signup'
                items['result'] = ''
                items['code'] = 404
                return items
            else:
                print(items['result'])
                print('sc: ', items['result'][0]['user_social_media'])
                  
            # #     # checks if login was by social media
            #     if password and items['result'][0]['user_social_media'] != 'NULL' and items['result'][0]['user_social_media'] != None:
            #         response['message'] = "Need to login by Social Media"
            #         response['code'] = 401
            #         return response

            #    # nothing to check
            #     elif (password is None and refresh_token is None) or (password is None and items['result'][0]['user_social_media'] == 'NULL'):
            #         response['message'] = "Enter password else login from social media"
            #         response['code'] = 405
            #         return response

            #     # compare passwords if user_social_media is false
            #     elif (items['result'][0]['user_social_media'] == 'NULL' or items['result'][0]['user_social_media'] == None) and password is not None:

            #         if items['result'][0]['password_hashed'] != password:
            #             items['message'] = "Wrong password"
            #             items['result'] = ''
            #             items['code'] = 406
            #             return items

            #         # if ((items['result'][0]['email_verified']) == '0') or (items['result'][0]['email_verified'] == "FALSE"):
            #         #     response['message'] = "Account need to be verified by email."
            #         #     response['code'] = 407
            #         #     return response

            #     # compare the refresh token because it never expire.
            #     elif (items['result'][0]['user_social_media']) != 'NULL':
            #         '''
            #         keep
            #         if signup_platform != items['result'][0]['user_social_media']:
            #             items['message'] = "Wrong social media used for signup. Use \'" + items['result'][0]['user_social_media'] + "\'."
            #             items['result'] = ''
            #             items['code'] = 401
            #             return items
            #         '''
            #         if (items['result'][0]['google_refresh_token'] != refresh_token):
            #             print("From database", items['result'][0]['google_refresh_token'])
            #             print("from postman", refresh_token)
            #             items['message'] = "Cannot Authenticated. Token is invalid"
            #             items['result'] = ''
            #             items['code'] = 408
            #             return items

            #     else:
            #         string = " Cannot compare the password or refresh token while log in. "
            #         print("*" * (len(string) + 10))
            #         print(string.center(len(string) + 10, "*"))
            #         print("*" * (len(string) + 10))
            #         response['message'] = string
            #         response['code'] = 500
            #         return response
            #     # del items['result'][0]['password_hashed']
            #     # del items['result'][0]['email_verified']



                if email == "":
                    execute("""UPDATE users SET mobile_refresh_token = \'""" +refresh_token+ """\'
                                            , mobile_auth_token =  \'""" +access_token+ """\'
                            WHERE social_id =  \'""" +social_id+ """\'""", 'post', conn)
                    query = "SELECT * from users WHERE social_id = \'" + social_id + "\';"
                    items = execute(query, 'get', conn)
                else:
                    print(email)
                    execute("""UPDATE users SET mobile_refresh_token = \'""" +refresh_token+ """\'
                                            , mobile_auth_token =  \'""" +access_token+ """\'
                                            , social_id =  \'""" +social_id+ """\'
                                            , user_social_media =  \'""" +signup_platform+ """\'


                            WHERE user_email_id =  \'""" +email+ """\'""", 'post', conn)

                    query = "SELECT * from users WHERE user_email_id = \'" + email + "\';"
                    items = execute(query, 'get', conn)
                items['message'] = "Authenticated successfully."
                items['code'] = 200
                return items
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class GoogleCalenderEvents(Resource):
    def post(self):

        try:
            conn = connect()
            data = request.get_json(force=True)

            timestamp = getNow()
            user_unique_id = data["id"]
            start = data["start"]
            end = data["end"]

            items = execute("""SELECT user_email_id, google_refresh_token, google_auth_token, access_issue_time, access_expires_in FROM users WHERE user_unique_id = \'""" +user_unique_id+ """\'""", 'get', conn )
            
            if len(items['result']) == 0:
                return "No such user exists"
            print(items)
            if items['result'][0]['access_expires_in'] == None or items['result'][0]['access_issue_time'] == None:
                f = open('credentials.json',)
                data = json.load(f)
                client_id = data['web']['client_id']
                client_secret = data['web']['client_secret']
                refresh_token = items['result'][0]['google_refresh_token']
        
                params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": items['result'][0]['google_refresh_token'],
                }
            
                authorization_url = "https://www.googleapis.com/oauth2/v4/token"
                r = requests.post(authorization_url, data=params)
                auth_token = ""
                if r.ok:
                        auth_token = r.json()['access_token']
                expires_in = r.json()['expires_in']
            
                execute("""UPDATE users SET 
                                google_auth_token = \'""" +str(auth_token)+ """\'
                                , access_issue_time = \'""" +str(timestamp)+ """\'
                                , access_expires_in = \'""" +str(expires_in)+ """\'
                                WHERE user_unique_id = \'""" +user_unique_id+ """\';""", 'post', conn)
                items = execute("""SELECT user_email_id, google_refresh_token, google_auth_token, access_issue_time, access_expires_in FROM users WHERE user_unique_id = \'""" +user_unique_id+ """\'""", 'get', conn )
                print(items)
                baseUri = "https://www.googleapis.com/calendar/v3/calendars/primary/events?orderBy=startTime&singleEvents=true&"            
                timeMaxMin = "timeMax="+end+"&timeMin="+start
                url = baseUri + timeMaxMin
                bearerString = "Bearer " + items['result'][0]['google_auth_token']
                headers = {"Authorization": bearerString, "Accept": "application/json"} 
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                calendars = response.json().get('items')
                return calendars

            else:
                access_issue_min = int(items['result'][0]['access_expires_in'])/60
                access_issue_time = datetime.strptime(items['result'][0]['access_issue_time'],"%Y-%m-%d %H:%M:%S")
                timestamp = datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S")
                diff = (timestamp - access_issue_time).total_seconds() / 60
                print(diff)
                if int(diff) > int(access_issue_min):
                    f = open('credentials.json',)
                    data = json.load(f)
                    client_id = data['web']['client_id']
                    client_secret = data['web']['client_secret']
                    refresh_token = items['result'][0]['google_refresh_token']
            
                    params = {
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": items['result'][0]['google_refresh_token'],
                    }
                
                    authorization_url = "https://www.googleapis.com/oauth2/v4/token"
                    r = requests.post(authorization_url, data=params)
                    auth_token = ""
                    if r.ok:
                            auth_token = r.json()['access_token']
                    expires_in = r.json()['expires_in']
                
                    execute("""UPDATE users SET 
                                    google_auth_token = \'""" +str(auth_token)+ """\'
                                    , access_issue_time = \'""" +str(timestamp)+ """\'
                                    , access_expires_in = \'""" +str(expires_in)+ """\'
                                    WHERE user_unique_id = \'""" +user_unique_id+ """\';""", 'post', conn)
                    
                items = execute("""SELECT user_email_id, google_refresh_token, google_auth_token, access_issue_time, access_expires_in FROM users WHERE user_unique_id = \'""" +user_unique_id+ """\'""", 'get', conn )
                print(items)
                baseUri = "https://www.googleapis.com/calendar/v3/calendars/primary/events?orderBy=startTime&singleEvents=true&"            
                timeMaxMin = "timeMax="+end+"&timeMin="+start
                url = baseUri + timeMaxMin
                bearerString = "Bearer " + items['result'][0]['google_auth_token']
                headers = {"Authorization": bearerString, "Accept": "application/json"} 
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                calendars = response.json().get('items')
                return calendars
          
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# @app.route('/test')
# def test_api_request():
#   if 'credentials' not in flask.session:
#     return flask.redirect('authorize')

#   # Load credentials from the session.
#   credentials = google.oauth2.credentials.Credentials(
#       **flask.session['credentials'])

#   drive = googleapiclient.discovery.build(
#       API_SERVICE_NAME, API_VERSION, credentials=credentials)

#   files = drive.files().list().execute()

#   # Save credentials back to session in case access token was refreshed.
#   # ACTION ITEM: In a production app, you likely want to save these
#   #              credentials in a persistent database instead.
#   flask.session['credentials'] = credentials_to_dict(credentials)

#   return flask.jsonify(**files)


# @app.route('/oauth2callback')
# def oauth2callback():
#     # Specify the state when creating the flow in the callback so that it can
#     # verified in the authorization server response.
#     state = flask.session['state']

#     flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
#         'credentials.json', scopes=SCOPES, state=state)
#     flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

#     # Use the authorization server's response to fetch the OAuth 2.0 tokens.
#     authorization_response = flask.request.url
#     flow.fetch_token(authorization_response=authorization_response)

#     # Store credentials in the session.
#     # ACTION ITEM: In a production app, you likely want to save these
#     #              credentials in a persistent database instead.
#     credentials = flow.credentials
#     flask.session['credentials'] = credentials_to_dict(credentials)

#     return flask.redirect(flask.url_for('test_api_request'))


# @app.route('/revoke')
# def revoke():
#   if 'credentials' not in flask.session:
#     return ('You need to <a href="/authorize">authorize</a> before ' +
#             'testing the code to revoke credentials.')

#   credentials = google.oauth2.credentials.Credentials(
#     **flask.session['credentials'])

#   revoke = requests.post('https://oauth2.googleapis.com/revoke',
#       params={'token': credentials.token},
#       headers = {'content-type': 'application/x-www-form-urlencoded'})

#   status_code = getattr(revoke, 'status_code')
#   if status_code == 200:
#     return('Credentials successfully revoked.' + print_index_table())
#   else:
#     return('An error occurred.' + print_index_table())


# @app.route('/clear')
# def clear_credentials():
#   if 'credentials' in flask.session:
#     del flask.session['credentials']
#   return ('Credentials have been cleared.<br><br>' +
#           print_index_table())


# def credentials_to_dict(credentials):
#   return {'token': credentials.token,
#           'refresh_token': credentials.refresh_token,
#           'token_uri': credentials.token_uri,
#           'client_id': credentials.client_id,
#           'client_secret': credentials.client_secret,
#           'scopes': credentials.scopes}

# class access_refresh_update(Resource):

#     def post(self):

#         try:
#             conn = connect()
#             data = request.get_json(force=True)

#             query = """
#                     UPDATE users SET google_access_token = \'""" + data['access_token'] + """\'
#                     , google_refresh_token = \'""" + data['refresh_token'] + """\'
#                     , user_timestamp =  \'""" + data['social_timestamp'] + """\' 
#                     WHERE (user_unique_id = \'""" + data['uid'] + """\'); ;
#                     """
#             print(query)
#             items = execute(query, 'post', conn)
#             if items['code'] == 281:
#                 items['message'] = 'Access and refresh token updated successfully'
#                 print(items['code'])
#                 items['code'] = 200
#             else:
#                 items['message'] = 'Check sql query'
#                 items['code'] = 400


#             return items

#         except:
#             raise BadRequest('Request failed, please try again later.')
#         finally:
#             disconnect(conn)


# class SignUp(Resource):
#     def post(self):
#         response = {}
#         items = []
#         try:
#             conn = connect()
#             data = request.get_json(force=True)
#             print(data)
#             email = data['email']
#             firstName = data['first_name']
#             lastName = data['last_name']
#             phone = data['phone_number']
#             # address = data['address']
#             # unit = data['unit'] if data.get('unit') is not None else 'NULL'
#             # city = data['city']
#             # state = data['state']
#             # zip_code = data['zip_code']
#             # latitude = data['latitude']
#             # longitude = data['longitude']
#             # referral = data['referral_source']
#             # role = data['role']
#             social_timestamp = data['social_timestamp'] if data.get('social_timestamp') is not None else 'NULL'
#             cust_id = data['cust_id'] if data.get('cust_id') is not None else 'NULL'

#             # if data.get('social') is None or data.get('social') == "FALSE" or data.get('social') == False:
#             #     social_signup = False
#             # else:
#             #     social_signup = True


#             get_user_id_query = "CALL get_user_id();"
#             NewUserIDresponse = execute(get_user_id_query, 'get', conn)

#             if NewUserIDresponse['code'] == 490:
#                 string = " Cannot get new User id. "
#                 print("*" * (len(string) + 10))
#                 print(string.center(len(string) + 10, "*"))
#                 print("*" * (len(string) + 10))
#                 response['message'] = "Internal Server Error."
#                 return response, 500
#             NewUserID = NewUserIDresponse['result'][0]['new_id']
#             social_signup  = True

#             if social_signup == False:

#                 salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

#                 password = sha512((data['password'] + salt).encode()).hexdigest()
#                 print('password------', password)
#                 algorithm = "SHA512"
#                 access_token = 'NULL'
#                 refresh_token = 'NULL'
#                 user_social_signup = 'NULL'
#             else:

#                 access_token = data['access_token']
#                 refresh_token = data['refresh_token']
#                 # salt = 'NULL'
#                 # password = 'NULL'
#                 # algorithm = 'NULL'
#                 user_social_signup = data['social']

#             if cust_id != 'NULL' and cust_id:

#                 NewUserID = cust_id

#                 query = '''
#                             SELECT google_access_token, google_refresh_token
#                             FROM users
#                             WHERE user_unique_id = \'''' + cust_id + '''\';
#                        '''
#                 it = execute(query, 'get', conn)
#                 print('it-------', it)

#                 access_token = it['result'][0]['google_access_token']
#                 refresh_token = it['result'][0]['google_refresh_token']


#                 customer_insert_query =  ['''
#                                     UPDATE users 
#                                     SET 
#                                     customer_created_at = \'''' + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + '''\',
#                                     user_first_name = \'''' + firstName + '''\',
#                                     user_last_name = \'''' + lastName + '''\',
#                                     user_social_media = \'''' + user_social_signup + '''\',
#                                     user_timestamp  =  \'''' + social_timestamp + '''\'
#                                     WHERE user_unique_id = \'''' + cust_id + '''\';
#                                     ''']


#             else:

#                 # check if there is a same customer_id existing
#                 query = """
#                         SELECT user_email_id FROM users
#                         WHERE user_email_id = \'""" + email + "\';"
#                 print('email---------')
#                 items = execute(query, 'get', conn)
#                 if items['result']:

#                     items['result'] = ""
#                     items['code'] = 409
#                     items['message'] = "Email address has already been taken."

#                     return items

#                 if items['code'] == 480:

#                     items['result'] = ""
#                     items['code'] = 480
#                     items['message'] = "Internal Server Error."
#                     return items


#                 # write everything to database
#                 customer_insert_query = ["""
#                                         INSERT INTO sf.customers 
#                                         (
#                                             user_unique_id,
#                                             user_first_name,
#                                             user_last_name,
#                                             customer_email_id,
#                                             user_social_media,
#                                             google_access_token,
#                                             user_timestamp,
#                                             google_refresh_token
#                                         )
#                                         VALUES
#                                         (
                                        
#                                             \'""" + NewUserID + """\',
#                                             \'""" + firstName + """\',
#                                             \'""" + lastName + """\',
#                                             \'""" + email + """\',
#                                             \'""" + user_social_signup + """\',
#                                             \'""" + access_token + """\',
#                                             \'""" + social_timestamp + """\',
#                                             \'""" + refresh_token + """\');"""]

#             items = execute(customer_insert_query[0], 'post', conn)

#             if items['code'] != 281:
#                 items['result'] = ""
#                 items['code'] = 480
#                 items['message'] = "Error while inserting values in database"

#                 return items


#             items['result'] = {
#                 'first_name': firstName,
#                 'last_name': lastName,
#                 'customer_uid': NewUserID,
#                 'access_token': access_token,
#                 'refresh_token': refresh_token
#             }
#             items['message'] = 'Signup successful'
#             items['code'] = 200

#             # Twilio sms service

#             #resp = url_for('sms_service', phone_num='+17327818408', _external=True)
#             #resp = sms_service('+1'+phone, firstName)
#             #print("resp --------", resp)



#             print('sss-----', social_signup)

#             if social_signup == False:
#                 token = s.dumps(email)
#                 msg = Message("Email Verification", sender='ptydtesting@gmail.com', recipients=[email])

#                 print('MESSAGE----', msg)
#                 print('message complete')
#                 link = url_for('confirm', token=token, hashed=password, _external=True)
#                 print('link---', link)
#                 msg.body = "Click on the link {} to verify your email address.".format(link)
#                 print('msg-bd----', msg.body)
#                 mail.send(msg)



#             return items
#         except:
#             print("Error happened while Sign Up")
#             if "NewUserID" in locals():
#                 execute("""DELETE FROM users WHERE user_unique_id = '""" + NewUserID + """';""", 'post', conn)
#             raise BadRequest('Request failed, please try again later.')
#         finally:
#             disconnect(conn)


# Define API routes

# Still uses getRdsConn()
# Needs to be converted to V2 APIs
#api.add_resource(Meals, '/api/v1/meals')
#api.add_resource(Accounts, '/api/v1/accounts')

# New APIs, uses connect() and disconnect()
# Create new api template URL
# api.add_resource(TemplateApi, '/api/v2/templateapi')

# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)

# GET requests
api.add_resource(GoalsRoutines, '/api/v2/getgoalsandroutines', '/api/v2/getgoalsandroutines/<string:user_id>') # working
api.add_resource(AboutMe, '/api/v2/aboutme', '/api/v2/aboutme/<string:user_id>') #working
api.add_resource(ListAllTA, '/api/v2/listAllTA', '/api/v2/listAllTA/<string:user_id>') #working
api.add_resource(ListAllPeople, '/api/v2/listPeople', '/api/v2/listPeople/<string:user_id>') #working
api.add_resource(ActionsTasks, '/api/v2/actionsTasks/<string:goal_routine_id>') #working
# api.add_resource(DailyView, '/api/v2/dailyView/<user_id>') #working
# api.add_resource(WeeklyView, '/api/v2/weeklyView/<user_id>') #working
# api.add_resource(MonthlyView, '/api/v2/monthlyView/<user_id>') #working
api.add_resource(AllUsers, '/api/v2/usersOfTA/<string:email_id>') #working
api.add_resource(TALogin, '/api/v2/loginTA/<string:email_id>/<string:password>') #working
api.add_resource(TASocialLogin, '/api/v2/loginSocialTA/<string:email_id>') #working
api.add_resource(Usertoken, '/api/v2/usersToken/<string:user_id>') #working
api.add_resource(UserLogin, '/api/v2/userLogin/<string:email_id>') #working
# api.add_resource(CurrentStatus, '/api/v2/currentStatus/<string:user_id>') #working
api.add_resource(GoogleCalenderEvents, '/api/v2/calenderEvents')


# POST requests
api.add_resource(AnotherTAAccess, '/api/v2/anotherTAAccess') #working
api.add_resource(AddNewAT, '/api/v2/addAT')
api.add_resource(AddNewGR, '/api/v2/addGR')
api.add_resource(UpdateGR, '/api/v2/updateGR')
api.add_resource(UpdateAT, '/api/v2/updateAT')
api.add_resource(DeleteAT, '/api/v2/deleteAT')
api.add_resource(DeleteGR, '/api/v2/deleteGR')
api.add_resource(CreateNewPeople, '/api/v2/addPeople') #working
api.add_resource(DeletePeople, '/api/v2/deletePeople')
api.add_resource(UpdateTime, '/api/v2/updateTime/<user_id>')
api.add_resource(NewTA, '/api/v2/addNewTA') #working
api.add_resource(TASocialSignUP, '/api/v2/addNewSocialTA') #working
api.add_resource(CreateNewUser, '/api/v2/addNewUser') #working
api.add_resource(UpdateAboutMe, '/api/v2/updateAboutMe')
api.add_resource(UpdateNameTimeZone, '/api/v2/updateNewUser')
api.add_resource(AddCoordinates, '/api/v2/addCoordinates')
api.add_resource(UpdateGRWatchMobile, '/api/v2/udpateGRWatchMobile')
api.add_resource(UpdateATWatchMobile, '/api/v2/updateATWatchMobile')
api.add_resource(Login, '/api/v2/login')
api.add_resource(UpdateAboutMe2, '/api/v2/update')
# api.add_resource(access_refresh_update, '/api/v2/accessRefreshUpdate')


# api.add_resource(CreateNewUsers, '/api/v2/createNewUser')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4000)