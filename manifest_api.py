from flask import Flask, request, render_template, url_for, redirect
from flask_restful import Resource, Api
from flask_mail import Mail, Message  # used for email
# used for serializer email and error handling
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_cors import CORS
import boto3, botocore

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

# def helper_upload_meal_images(file, bucket, key):
       
#     filename = 'https://s3-us-west-1.amazonaws.com/' \
#             + str(bucket) + '/' + str(key)
#     print(filename)
#     upload_file = s3.put_object(
#                         Bucket=bucket,
#                         Body=file,
#                         Key=key,
#                         ACL='public-read',
#                         ContentType='image/jpeg'
#                     )
#     return filename

# def allowed_file(filename):
#     """Checks if the file is allowed to upload"""
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
            # file = "/Users/rohan/Downloads/Sunny Beach Traceable 1.jpg"
            # helper_upload_meal_images(file, S3_BUCKET, "p")

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


            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Get Routines Request failed, please try again later.')
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
                query = """SELECT ta_people_id
                                , ta_email_id AS email_id
                                , people_name
                                , ta_have_pic AS have_pic
                                , ta_picture AS picture
                                , important
                                , user_unique_id
                                , relation_type
                                FROM
                            users
                            LEFT JOIN
                            (SELECT ta_people_id
                                , ta_email_id
                                , CONCAT(ta_first_name, SPACE(1), ta_last_name) as people_name
                                , ta_have_pic
                                , ta_picture
                                , important
                                , user_uid
                                , relation_type
                            FROM relationship
                            JOIN ta_people
                            ON ta_people_id = ta_unique_id
                            WHERE relation_type!='advisor' and important = 'True') r
                            ON user_unique_id = r.user_uid
                            WHERE user_unique_id =  \'""" +user_id+ """\';"""

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
                        WHERE relation_type = 'advisor' and ta_email_id = \'""" + email_id + """\';"""
            
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
                            and relation_type = 'advisor';"""

                query2 = """SELECT DISTINCT ta_unique_id
                                    , CONCAT(ta_first_name, SPACE(1), ta_last_name) as name
                                    , ta_first_name
                                    , ta_last_name
                            FROM ta_people
                            JOIN relationship on ta_unique_id = ta_people_id
                            WHERE relation_type = 'advisor';"""

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
                                        , important)
                            VALUES 
                                        ( \'""" + str(new_relation_id) + """\'
                                        , \'""" + str(timestamp) + """\'
                                        , \'""" + str(ta_id) + """\'
                                        , \'""" + str(user_id) + """\'
                                        , \'""" + 'advisor' + """\'
                                        , \'""" + 'FALSE' + """\'
                                        , \'""" + '' + """\'
                                        , \'""" + '' + """\');""")
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
                            WHERE relation_type != 'advisor' and user_uid = \'""" + user_id+  """\';"""
            
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

            gr_title = data['gr_title']
            user_id = data['user_id']
            ta_id = data['ta_id']
            is_available = data['is_available']
            is_displayed_today = data['is_displayed_today']
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
            start_day_and_time = data['start_day_and_time']
            repeat_week_days = data['repeat_week_days']
            end_day_and_time = data['end_day_and_time']
            expected_completion_time = data['expected_completion_time']
            ta_before_is_enable = data['ta_notifications']['before']['is_enable']
            ta_before_is_set = data['ta_notifications']['before']['is_set']
            ta_before_message = data['ta_notifications']['before']['message']
            ta_before_time = data['ta_notifications']['before']['time']
            ta_during_is_enable = data['ta_notifications']['during']['is_enable']
            ta_during_is_set = data['ta_notifications']['during']['is_set']
            ta_during_message = data['ta_notifications']['during']['message']
            ta_during_time = data['ta_notifications']['during']['time']
            ta_after_is_enable = data['ta_notifications']['after']['is_enable']
            ta_after_is_set = data['ta_notifications']['after']['is_set']
            ta_after_message = data['ta_notifications']['after']['message']
            ta_after_time = data['ta_notifications']['after']['time']
            user_before_is_enable = data['user_notifications']['before']['is_enable']
            user_before_is_set = data['user_notifications']['before']['is_set']
            user_before_message = data['user_notifications']['before']['message']
            user_before_time = data['user_notifications']['before']['time']
            user_during_is_enable = data['user_notifications']['during']['is_enable']
            user_during_is_set = data['user_notifications']['during']['is_set']
            user_during_message = data['user_notifications']['during']['message']
            user_during_time = data['user_notifications']['during']['time']
            user_after_is_enable = data['user_notifications']['after']['is_enable']
            user_after_is_set = data['user_notifications']['after']['is_set']
            user_after_message = data['user_notifications']['after']['message']
            user_after_time = data['user_notifications']['after']['time']

            datetime_completed = 'Sun, 23 Feb 2020 00:08:43 GMT'
            datetime_started = 'Sun, 23 Feb 2020 00:08:43 GMT'

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
                            , repeat_ends
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
                        ( \'""" + str(new_gr_id) + """\'
                        , \'""" + str(gr_title) + """\'
                        , \'""" + str(user_id) + """\'
                        , \'""" + str(is_available) + """\'
                        , \'""" + 'FALSE' + """\'
                        , \'""" + 'FALSE' + """\'
                        , \'""" + str(is_displayed_today) + """\'
                        , \'""" + str(is_persistent) + """\'
                        , \'""" + str(is_sublist_available) + """\'
                        , \'""" + str(is_timed) + """\'
                        , \'""" + str(photo) + """\'
                        , \'""" + str(repeat) + """\'
                        , \'""" + str(repeat_ends) + """\'
                        , \'""" + str(repeat_ends_on) + """\'
                        , \'""" + str(repeat_every) + """\'
                        , \'""" + str(repeat_frequency) + """\'
                        , \'""" + str(repeat_occurences) + """\'
                        , \'""" + str(start_day_and_time) + """\'
                        , \'""" + str(repeat_week_days) + """\'
                        , \'""" + str(datetime_completed) + """\'
                        , \'""" + str(datetime_started) + """\'
                        , \'""" + str(end_day_and_time) + """\'
                        , \'""" + str(expected_completion_time) + """\');""")

            execute(query[1], 'post', conn)

            # New Notification ID
            new_notification_id_response = execute("CALL get_notification_id;",  'get', conn)
            new_notfication_id = new_notification_id_response['result'][0]['new_id']

            # TA notfication
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
                                (     \'""" + new_notfication_id + """\'
                                    , \'""" + ta_id + """\'
                                    , \'""" + new_gr_id + """\'
                                    , \'""" + ta_before_is_enable + """\'
                                    , \'""" + ta_before_is_set + """\'
                                    , \'""" + ta_before_message + """\'
                                    , \'""" + ta_before_time + """\'
                                    , \'""" + ta_during_is_enable + """\'
                                    , \'""" + ta_during_is_set + """\'
                                    , \'""" + ta_during_message + """\'
                                    , \'""" + ta_during_time + """\'
                                    , \'""" + ta_after_is_enable + """\'
                                    , \'""" + ta_after_is_set + """\'
                                    , \'""" + ta_after_message + """\'
                                    , \'""" + ta_after_time + """\');""")
            execute(query[2], 'post', conn)

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
                                    , \'""" + NewGRID + """\'
                                    , \'""" + user_before_is_enable + """\'
                                    , \'""" + user_before_is_set + """\'
                                    , \'""" + user_before_message + """\'
                                    , \'""" + user_before_time + """\'
                                    , \'""" + user_during_is_enable + """\'
                                    , \'""" + user_during_is_set + """\'
                                    , \'""" + user_during_message + """\'
                                    , \'""" + user_during_time + """\'
                                    , \'""" + user_after_is_enable + """\'
                                    , \'""" + user_after_is_set + """\'
                                    , \'""" + user_after_message + """\'
                                    , \'""" + user_after_time + """\');""")
            items = execute(query[3], 'post', conn)


            response['message'] = 'successful'
            response['result'] = items

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

            user_id = data['user_id']
            ta_id = data['ta_id']
            at_title = data['at_title']
            goal_routine_id = data['goal_routine_id']
            is_available = data['is_available']
            is_sublist_available = data['is_sublist_available']
            is_must_do = data['is_must_do']
            photo = data['photo']
            is_timed = data['is_timed']
            expected_completion_time = data['expected_completion_time']
            ta_before_is_enable = data['ta_notifications']['before']['is_enable']
            ta_before_is_set = data['ta_notifications']['before']['is_set']
            ta_before_message = data['ta_notifications']['before']['message']
            ta_before_time = data['ta_notifications']['before']['time']
            ta_during_is_enable = data['ta_notifications']['during']['is_enable']
            ta_during_is_set = data['ta_notifications']['during']['is_set']
            ta_during_message = data['ta_notifications']['during']['message']
            ta_during_time = data['ta_notifications']['during']['time']
            ta_after_is_enable = data['ta_notifications']['after']['is_enable']
            ta_after_is_set = data['ta_notifications']['after']['is_set']
            ta_after_message = data['ta_notifications']['after']['message']
            ta_after_time = data['ta_notifications']['after']['time']
            user_before_is_enable = data['user_notifications']['before']['is_enable']
            user_before_is_set = data['user_notifications']['before']['is_set']
            user_before_message = data['user_notifications']['before']['message']
            user_before_time = data['user_notifications']['before']['time']
            user_during_is_enable = data['user_notifications']['during']['is_enable']
            user_during_is_set = data['user_notifications']['during']['is_set']
            user_during_message = data['user_notifications']['during']['message']
            user_during_time = data['user_notifications']['during']['time']
            user_after_is_enable = data['user_notifications']['after']['is_enable']
            user_after_is_set = data['user_notifications']['after']['is_set']
            user_after_message = data['user_notifications']['after']['message']
            user_after_time = data['user_notifications']['after']['time']


            datetime_completed = 'Sun, 23 Feb 2020 00:08:43 GMT'
            datetime_started = 'Sun, 23 Feb 2020 00:08:43 GMT'
            query = ["CALL get_at_id;"]
            NewATIDresponse = execute(query[0],  'get', conn)
            NewATID = NewATIDresponse['result'][0]['new_id']

            query.append("""SELECT at_sequence
                            FROM actions_tasks
                            WHERE goal_routine_id = \'""" + goal_routine_id + """\'
                            ORDER BY at_sequence DESC
                            LIMIT 1;""")
            ATSequenceResponse = execute(query[1], 'get', conn)
            at_sequence = ATSequenceResponse['result'][0]['at_sequence']
            if(at_sequence >= 1):
                at_sequence += 1
            else:
                at_sequence = 1
            
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
                            , expected_completion_time)
                        VALUES 
                        ( \'""" + NewATID + """\'
                        , \'""" + at_title + """\'
                        , \'""" + goal_routine_id + """\'
                        , \'""" + str(at_sequence) + """\'
                        , \'""" + is_available + """\'
                        , \'""" + 'FALSE' + """\'
                        , \'""" + 'FALSE' + """\'
                        , \'""" + is_sublist_available + """\'
                        , \'""" + is_must_do + """\'
                        , \'""" + photo + """\'
                        , \'""" + is_timed + """\'
                        , \'""" + datetime_completed + """\'
                        , \'""" + datetime_started + """\'
                        , \'""" + expected_completion_time + """\');""")

            items = execute(query[2], 'post', conn)

            # New Notification ID
            NewNotificationIDresponse = execute("CALL get_notification_id;",  'get', conn)
            NewNotificationID = NewNotificationIDresponse['result'][0]['new_id']

            # TA notfication
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
                                    , \'""" + ta_id + """\'
                                    , \'""" + NewATID + """\'
                                    , \'""" + ta_before_is_enable + """\'
                                    , \'""" + ta_before_is_set + """\'
                                    , \'""" + ta_before_message + """\'
                                    , \'""" + ta_before_time + """\'
                                    , \'""" + ta_during_is_enable + """\'
                                    , \'""" + ta_during_is_set + """\'
                                    , \'""" + ta_during_message + """\'
                                    , \'""" + ta_during_time + """\'
                                    , \'""" + ta_after_is_enable + """\'
                                    , \'""" + ta_after_is_set + """\'
                                    , \'""" + ta_after_message + """\'
                                    , \'""" + ta_after_time + """\');""")
            execute(query[3], 'post', conn)

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
                                    , \'""" + NewATID + """\'
                                    , \'""" + user_before_is_enable + """\'
                                    , \'""" + user_before_is_set + """\'
                                    , \'""" + user_before_message + """\'
                                    , \'""" + user_before_time + """\'
                                    , \'""" + user_during_is_enable + """\'
                                    , \'""" + user_during_is_set + """\'
                                    , \'""" + user_during_message + """\'
                                    , \'""" + user_during_time + """\'
                                    , \'""" + user_after_is_enable + """\'
                                    , \'""" + user_after_is_set + """\'
                                    , \'""" + user_after_message + """\'
                                    , \'""" + user_after_time + """\');""")
            execute(query[4], 'post', conn)


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
                execute("""DELETE FROM actions_tasks WHERE at_unique_id = \'""" + at_id + """\';""", None, 'post', conn)
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

            execute("""DELETE FROM notifications 
                            WHERE gr_at_id = \'""" + at_id + """\';""", 'post', conn)

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
                            WHERE `repeat` = 'TRUE'
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
                            WHERE `repeat` = 'TRUE'
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
            ts  = dt.datetime.now()
            data = request.get_json(force=True)
            user_id = data['user_id']
            email_id = data['email_id']
            first_name = data['first_name']
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

            name = []
            name = first_name.split()
            first_name = name[0]
            last_name = name[1]

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
               
                execute("""INSERT INTO relationship(
                    id
                    , r.timestamp
                    , ta_people_id
                    , user_uid
                    , relation_type
                    , ta_have_pic
                    , ta_picture
                    , important)
                    VALUES ( 
                        \'""" + NewRelationID + """\'
                        , \'""" + str(ts) + """\'
                        , \'""" + typeResponse['result'][0]['unique_id'] + """\'
                        , \'""" + user_id + """\'
                        , \'""" + relation_type + """\'
                        , \'""" + have_pic + """\'
                        , \'""" + picture + """\'
                        , \'""" + important + """\')""", 'post', conn)

            else:
                NewPeopleIDresponse = execute("CALL get_ta_people_id;", 'get', conn)
                NewPeopleID = NewPeopleIDresponse['result'][0]['new_id']
                print(NewPeopleID)
                execute("""INSERT INTO ta_people(
                                        ta_unique_id
                                        , ta_email_id
                                        , ta_first_name
                                        , ta_last_name
                                        , employer
                                        , password_hashed
                                        , ta_phone_number)
                                        VALUES ( 
                                            \'""" + NewPeopleID + """\'
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
                                        , important)
                                        VALUES ( 
                                            \'""" + NewRelationID + """\'
                                            , \'""" + str(ts) + """\'
                                            , \'""" + NewPeopleID + """\'
                                            , \'""" + user_id + """\'
                                            , \'""" + relation_type + """\'
                                            , \'""" + have_pic + """\'
                                            , \'""" + picture + """\'
                                            , \'""" + important + """\')""", 'post', conn)

                
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

# New TA signup
class NewTA(Resource):
    def post(self):    
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            email_id = data['email_id']
            password = data['password']
            first_name = data['first_name']
            last_name = data['last_name']
            phone_number = data['phone_number']
            employer = data['employer']
            salt = os.urandom(32)
           
            dk = hashlib.pbkdf2_hmac('sha256',  password.encode('utf-8') , salt, 100000, dklen=128)
            key = (salt + dk).hex()

            NewPeopleIDresponse = execute("CALL get_ta_people_id;", 'get', conn)
            NewPeopleID = NewPeopleIDresponse['result'][0]['new_id']

            execute("""INSERT INTO ta_people(
                                        ta_unique_id
                                        , ta_email_id
                                        , ta_first_name
                                        , ta_last_name
                                        , employer
                                        , password_hashed
                                        , ta_phone_number)                                        
                                        VALUES ( 
                                            \'""" + NewPeopleID + """\'
                                            , \'""" + email_id + """\'
                                            , \'""" + first_name + """\'
                                            , \'""" + last_name + """\'
                                            , \'""" + employer + """\'
                                            , \'""" + key + """\'
                                            , \'""" + phone_number + """\')""", 'post', conn)
            response['message'] = 'successful'
            response['result'] = items

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
            email_id = data['email_id']
            first_name = data['first_name']
            last_name = data['last_name']
            phone_number = data['phone_number']
            employer = data['employer']
           
            NewPeopleIDresponse = execute("CALL get_ta_people_id;", 'get', conn)
            NewPeopleID = NewPeopleIDresponse['result'][0]['new_id']

            execute("""INSERT INTO ta_people(
                                            ta_unique_id
                                            , ta_email_id
                                            , ta_first_name
                                            , ta_last_name
                                            , employer
                                            , ta_phone_number)
                                        VALUES ( 
                                            \'""" + NewPeopleID + """\'
                                            , \'""" + email_id + """\'
                                            , \'""" + first_name + """\'
                                            , \'""" + last_name + """\'
                                            , \'""" + employer + """\'
                                            , \'""" + phone_number + """\')""", 'post', conn)
            response['message'] = 'successful'
            response['result'] = items

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
                emailIDResponse = execute("""SELECT password_hashed from ta_people where ta_email_id = \'""" + email_id + """\'""", 'get', conn)
                password_storage = emailIDResponse['result'][0]['password_hashed']

                original = bytes.fromhex(password_storage)
                salt_from_storage = original[:32] 
                key_from_storage = original[32:]

                new_dk = hashlib.pbkdf2_hmac('sha256',  password.encode('utf-8') , salt_from_storage, 100000, dklen=128)
                
                if key_from_storage == new_dk:
                    response['result'] = True
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
            emails = execute("""SELECT ta_email_id from ta_people;""", 'get', conn)
            for i in range(len(emails['result'])):
                email = emails['result'][i]['ta_email_id']
                if email == email_id:
                    temp = True
            if temp == True:
                
                response['result'] = True
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

        try:
            conn = connect()
            data = request.get_json(force=True)
            email_id = data['email_id']
            google_auth_token = data['google_auth_token']
            google_refresh_token = data['google_refresh_token']
            first_name = data['first_name']
            last_name = data['last_name']

            UserIDResponse = execute("CAll get_user_id();", 'get', conn)
            NewUserID = UserIDResponse['result'][0]['new_id']
            temp = False
            emails = execute("""SELECT user_email_id from users;""", 'get', conn)
            for i in range(len(emails['result'])):
                email = emails['result'][i]['user_email_id']
                if email == email_id:
                    temp = True
            if temp == False:
                execute("""INSERT INTO users(
                                            user_unique_id
                                            , user_email_id
                                            , user_first_name
                                            , user_last_name
                                            , google_auth_token
                                            , google_refresh_token)
                                        VALUES ( 
                                            \'""" + NewUserID + """\'
                                            , \'""" + email_id + """\'
                                            , \'""" + first_name + """\'
                                            , \'""" + last_name + """\'
                                            , \'""" + google_auth_token + """\'
                                            , \'""" + google_refresh_token + """\')""", 'post', conn)
            if temp == True:
                 execute("""UPDATE  users
                            SET 
                                user_first_name = \'""" + first_name + """\'
                                , user_last_name =  \'""" + last_name + """\'
                                , google_auth_token = \'""" + google_auth_token + """\'
                                , google_refresh_token = \'""" + google_refresh_token + """\'
                            WHERE user_email_id = \'""" + email_id + """\' ;""", 'post', conn)

            
            response['message'] = 'successful'
            response['result'] = items

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
            relation_type = []
            user_id = data['user_id']
            first_name = data['first_name']
            last_name = data['last_name']
            have_pic = data['have_pic']
            message_card = data['message_card']
            message_day = data['message_day']
            picture = data['picture']
            if len(data['people']) > 0:
                for i in range(len(data['people'])):
                    people_id.append(data['people'][i]['ta_people_id'])
                    people_name.append(data['people'][i]['name'])
                    people_relationship.append(data['people'][i]['relationship'])
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

            execute("""UPDATE  users
                            SET 
                                user_first_name = \'""" + first_name + """\'
                                , user_have_pic = \'""" + have_pic + """\'
                                , user_picture = \'""" + picture + """\'
                                , message_card = \'""" + message_card + """\'
                                , message_day = \'""" + message_day + """\'
                                , user_last_name =  \'""" + last_name + """\'
                                , time_zone = \'""" + time_zone + """\'
                                , morning_time = \'""" + morning_time + """\'
                                , afternoon_time = \'""" + afternoon_time + """\'
                                , evening_time = \'""" + evening_time + """\'
                                , night_time = \'""" + night_time + """\'
                                , day_start = \'""" + day_start + """\'
                                , day_end = \'""" + day_end + """\'
                            WHERE user_unique_id = \'""" + user_id + """\' ;""", 'post', conn)

            for i in range(len(people_id)):

                temp = True

                relationResponse = execute("""SELECT relation_type FROM relationship 
                            WHERE ta_people_id = \'""" + people_id[i] + """\' 
                            and user_uid = \'""" + user_id + """\';""", 'get', conn)

                for r in range(len(relationResponse['result'])):
                    relation_type.append(relationResponse['result'][r]['relation_type'])

                if len(relationResponse['result']) == 0:
                    NewRelationIDresponse = execute("Call get_relation_id;", 'get', conn)
                    NewRelationID = NewRelationIDresponse['result'][0]['new_id']
                    print(NewRelationID)
                    execute("""INSERT INTO relationship
                                        (id
                                        , ta_people_id
                                        , user_uid
                                        , r_timestamp
                                        , relation_type
                                        , ta_have_pic
                                        , ta_picture
                                        , important)
                                        VALUES 
                                        ( \'""" + NewRelationID + """\'
                                        , \'""" + people_id[i] + """\'
                                        , \'""" + user_id + """\'
                                        , \'""" + timestamp + """\'
                                        , \'""" + people_relationship[i] + """\'
                                        , \'""" + people_have_pic[i] + """\'
                                        , \'""" + people_pic[i] + """\'
                                        , \'""" + people_important[i] + """\');""", 'post', conn)
                    print("relation added")

                for r in range(len(relationResponse['result'])):
                    relation_type.append(relationResponse['result'][r]['relation_type'])
                    if relationResponse['result'][r]['relation_type'] != 'advisor':
                        temp = False
                        print(temp)
                        print(people_id[i])
                        print(relationResponse['result'][r]['relation_type'])
                        # items = execute("""UPDATE  relationship
                        #     SET 
                        #         r_timestamp = \'""" + timestamp + """\'
                        #         , relation_type = \'""" + people_relationship[i] + """\'
                        #         , ta_have_pic =  \'""" + people_have_pic[i] + """\'
                        #         , ta_picture = \'""" + people_pic[i] + """\'
                        #         , important = \'""" + people_important[i] + """\'
                        #     WHERE ta_people_id = \'""" + people_id[i] + """\' 
                        #     and user_uid = \'""" + user_id + """\';""", 'post', conn)
                        # print(relationResponse['result'][r]['relation_type'])
                        # print(temp)

                    if temp == True:
                        query = ["Call get_relation_id;"]
                        NewRealtionIDresponse = execute(query[0], 'get', conn)
                        NewRealtionID = NewRealtionIDresponse['result'][0]['new_id']
                        print(NewRealtionID)
                        execute("""INSERT INTO relationship
                                            (id
                                            , ta_people_id
                                            , user_uid
                                            , r_timestamp
                                            , relation_type
                                            , ta_have_pic
                                            , ta_picture
                                            , important)
                                            VALUES 
                                            ( \'""" + NewRealtionID + """\'
                                            , \'""" + people_id[i] + """\'
                                            , \'""" + user_id + """\'
                                            , \'""" + timestamp + """\'
                                            , \'""" + people_relationship[i] + """\'
                                            , \'""" + people_have_pic[i] + """\'
                                            , \'""" + people_pic[i] + """\'
                                            , \'""" + people_important[i] + """\');""", 'post', conn)
                        print("relation added")
            
            response['message'] = 'successful'
            response['result'] = items

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
            conn = connect()
            data = request.get_json(force=True)
            ta_id = data["ta_email"]
            email_id = data['email']
            first_name = data['first_name']
            last_name = data['last_name']
            time_zone = data["timeZone"]
            print(email_id)
            items = execute("""UPDATE  users
                            SET 
                                user_first_name = \'""" + first_name + """\'
                                , user_last_name =  \'""" + last_name + """\'
                                , time_zone = \'""" + time_zone + """\'
                            WHERE user_email_id = \'""" + email_id + """\' ;""", 'post', conn)
            
            userIDResponse = execute("SELECT user_unique_id from users where user_email_id = \'""" + email_id + """\';""", 'get', conn)
            print(userIDResponse)
            user_id = userIDResponse['result'][0]['user_unique_id']
            print(user_id)
            NewRelationIDresponse = execute("Call get_relation_id;", 'get', conn)
            NewRelationID = NewRelationIDresponse['result'][0]['new_id']

            TAIDResponse = execute("""SELECT ta_unique_id from ta_people where ta_email_id = \'""" + ta_id + """\';""", 'get', conn)
            ta_unique_id = TAIDResponse['result'][0]['unique_id']
            print(ta_unique_id)
            execute("""INSERT INTO relationship
                        (id
                        , ta_people_id
                        , user_uid
                        , relation_type
                        , ta_have_pic
                        , ta_picture
                        , important)
                        VALUES 
                        ( \'""" + NewRelationID + """\'
                        , \'""" + ta_unique_id + """\'
                        , \'""" + user_id + """\'
                        , \'""" + 'advisor' + """\'
                        , \'""" + 'FALSE' + """\'
                        , \'""" + '' + """\'
                        , \'""" + '' + """\');""", 'post', conn)

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

            response['message'] = 'successful'
            response['email_id'] = items['result'][0]['user_email_id']
            response['google_auth_token'] = items['result'][0]['google_auth_token']
            response['google_refresh_token'] = items['result'][0]['google_refresh_token']

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


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
api.add_resource(DailyView, '/api/v2/dailyView/<user_id>') #working
api.add_resource(WeeklyView, '/api/v2/weeklyView/<user_id>') #working
api.add_resource(MonthlyView, '/api/v2/monthlyView/<user_id>') #working
api.add_resource(AllUsers, '/api/v2/usersOfTA/<string:email_id>') #working
api.add_resource(TALogin, '/api/v2/loginTA/<string:email_id>/<string:password>') #working
api.add_resource(TASocialLogin, '/api/v2/loginSocialTA/<string:email_id>') #working
api.add_resource(Usertoken, '/api/v2/usersToken/<string:user_id>') #working
api.add_resource(UserLogin, '/api/v2/userLogin/<string:email_id>') #working

# POST requests
api.add_resource(AnotherTAAccess, '/api/v2/anotherTAAccess') #working
api.add_resource(AddNewAT, '/api/v2/addAT')
api.add_resource(AddNewGR, '/api/v2/addGR')
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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4000)