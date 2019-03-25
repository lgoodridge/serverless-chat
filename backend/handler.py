import json

def ping(event, context):
    body = {
        "message": "PONG!",
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
