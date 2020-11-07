from __future__ import print_function

import base64
import json
import logging
import _pickle as cPickle
from datetime import datetime
import decimal
import uuid
import boto3
from copy import deepcopy
import time
import ast

s3_client = boto3.client('s3')
s3_bucket = "Enter Your Buckets Name"
rekog_client = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

dynamodb = boto3.resource('dynamodb')
ddb_table = dynamodb.Table("ENter Your Table Name")

def process_image(event,context):
    frame_package=''
    item = {}
    for records in event['Records']:
        frame_package_b64 = records['kinesis']['data']
        frame_package = cPickle.loads(base64.b64decode(frame_package_b64))
        print(frame_package)    
        x = str(frame_package['rekog_labels'])
        y = x.replace('"',"'")
        frame_package['rekog_labels'] = y
        s3_key = frame_package['s3_key']
        img_bytes = frame_package['img_bytes']
        notification_type = frame_package['notification_type'] 
        notification_message = frame_package['notification']
        notification_title = frame_package['notification_title'] 
        
        s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=img_bytes)
        del frame_package['img_bytes']
        #if (frame_package['notification_title']!='nothing'):
        response = ddb_table.put_item(Item = frame_package)    
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully processed  records.')
    }

def lambda_handler(event, context):
    print(event)
    return process_image(event, context)
	
