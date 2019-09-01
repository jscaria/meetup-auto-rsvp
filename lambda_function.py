import json
from botocore.vendored import requests
import logging
import os
import boto3
import datetime
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ses = boto3.client('ses')


def lambda_handler(event, context):
    events_url = "https://api.meetup.com/{0!s}/events?sign=true&photo-host=public&page=10".format(os.environ['GROUP_NAME'])
    rsvp_url = "https://api.meetup.com/2/rsvp/"
    
    headers = {
        "Authorization": "Bearer {0!s}".format(os.environ["OAUTH_ACCESS_TOKEN"])
    }
    
    events_request = requests.get(events_url, headers=headers)
    events_response = events_request.json()
    
    logger.debug("events_response: " + json.dumps(events_response, indent=4))
    '''
    [
      {
        "local_time": "11:00",
        "local_date": "2018-09-09",
        "link": "https://www.meetup.com/<group_name>/events/<event_id>/",
        "visibility": "public_limited",
        "group": {
          "created": 1373082291000,
          "name": "<group_nane>",
          "id": 0,
          "join_mode": "approval",
          "lat": 37.31,
          "lon": -122,
          "urlname": "<group_url>",
          "who": "<people>",
          "localized_location": "<location>",
          "region": "en_US",
          "timezone": "US/Pacific"
        },
        "waitlist_count": 0,
        "yes_rsvp_count": 23,
        "duration": 7200000,
        "time": 1536516000000,
        "utc_offset": -25200000,
        "name": "<name>",
        "id": "<id>"
      }
    ]
    '''
    
    rsvp = "YES"
    responses = []
    successful_rsvp = False

    for entry in events_response:
      event_id = entry["id"]
      logger.debug("event: event_id={0!s}&rsvp={1!s}".format(event_id, rsvp))
    
      data = {
          "event_id": event_id,
          "rsvp": rsvp
      }

      rsvp_request = requests.post(rsvp_url, headers=headers, data=data)
      rsvp_response = rsvp_request.json()
      local_response = {
        "statusCode": rsvp_request.status_code,
        "body": rsvp_response
      }
      
      responses.append(local_response)
      
      if "code" not in rsvp_response or rsvp_response["code"] != "event_past":
        subject = 'Lambda function - ' + str(rsvp_request.status_code)
        data = json.dumps(rsvp_response, indent=4)
        
        if rsvp_request.status_code == 201:
          ts = int(rsvp_response["event"]["time"]/1000)
          tz = pytz.timezone("US/Pacific")
          event_time = datetime.datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc) # in UTC
          event_time_in_local = event_time.astimezone(tz) # converted to US/Pacific
          event_time_string = event_time_in_local.strftime('%m-%d-%Y @ %H:%M')
          subject = 'RSVP {0!s} to {1!s} on {2!s}'.format(rsvp_response["response"], rsvp_response["event"]["name"], event_time_string)
        
        response = ses.send_email(
          Source = os.environ['EMAIL_FROM'],
          Destination={
            'ToAddresses': [
              os.environ['EMAIL_TO'],
            ],
          },
          Message={
            'Subject': {
              'Data': subject
            },
            'Body': {
              'Text': {
                'Data': data
              }
            }
          }
        )
      
      if rsvp_request.status_code == 201:
        successful_rsvp = True
        return responses

    return responses