import boto3
import json
import jwt
import logging
import time

logger = logging.getLogger("handler_logger")
logger.setLevel(logging.DEBUG)

dynamodb = boto3.resource("dynamodb")


def _get_body(event):
    try:
        return json.loads(event.get("body", ""))
    except:
        logger.debug("event body could not be JSON decoded.")
        return {}


def _get_response(status_code, body):
    if not isinstance(body, str):
        body = json.dumps(body)
    return {"statusCode": status_code, "body": body}


def _send_to_connection(connection_id, data, event):
    gatewayapi = boto3.client("apigatewaymanagementapi",
            endpoint_url = "https://" + event["requestContext"]["domainName"] +
                    "/" + event["requestContext"]["stage"])
    return gatewayapi.post_to_connection(ConnectionId=connection_id,
            Data=json.dumps(data).encode('utf-8'))


def connection_manager(event, context):
    """
    Handles connecting and disconnecting for the Websocket.

    Connect verifes the passed in token, and if successful,
    adds the connectionID to the database.

    Disconnect removes the connectionID from the database.
    """
    connectionID = event["requestContext"].get("connectionId")
    token = event.get("queryStringParameters", {}).get("token")

    if event["requestContext"]["eventType"] == "CONNECT":
        logger.info("Connect requested (CID: {}, Token: {})"\
                .format(connectionID, token))

        # Ensure connectionID and token are set
        if not connectionID:
            logger.error("Failed: connectionId value not set.")
            return _get_response(500, "connectionId value not set.")
        if not token:
            logger.debug("Failed: token query parameter not provided.")
            return _get_response(400, "token query parameter not provided.")

        # Verify the token
        try:
            payload = jwt.decode(token, "FAKE_SECRET", algorithms="HS256")
            logger.info("Verified JWT for '{}'".format(payload.get("username")))
        except:
            logger.debug("Failed: Token verification failed.")
            return _get_response(400, "Token verification failed.")

        # Add connectionID to the database
        table = dynamodb.Table("serverless-chat_Connections")
        table.put_item(Item={"ConnectionID": connectionID})
        return _get_response(200, "Connect successful.")

    elif event["requestContext"]["eventType"] == "DISCONNECT":
        logger.info("Disconnect requested (CID: {})".format(connectionID))

        # Ensure connectionID is set
        if not connectionID:
            logger.error("Failed: connectionId value not set.")
            return _get_response(500, "connectionId value not set.")

        # Remove the connectionID from the database
        table = dynamodb.Table("serverless-chat_Connections")
        table.delete_item(Key={"ConnectionID": connectionID})
        return _get_response(200, "Disconnect successful.")

    else:
        logger.error("Connection manager received unrecognized eventType '{}'"\
                .format(event["requestContext"]["eventType"]))
        return _get_response(500, "Unrecognized eventType.")


def default_message(event, context):
    """
    Send back error when unrecognized WebSocket action is received.
    """
    logger.info("Unrecognized WebSocket action received.")
    return _get_response(400, "Unrecognized WebSocket action.")


def get_recent_messages(event, context):
    """
    Return the 10 most recent chat messages.
    """
    connectionID = event["requestContext"].get("connectionId")
    logger.info("Retrieving most recent messages for CID '{}'"\
            .format(connectionID))

    # Ensure connectionID is set
    if not connectionID:
        logger.error("Failed: connectionId value not set.")
        return _get_response(500, "connectionId value not set.")

    # Get the 10 most recent chat messages
    table = dynamodb.Table("serverless-chat_Messages")
    response = table.query(KeyConditionExpression="Room = :room",
            ExpressionAttributeValues={":room": "general"},
            Limit=10, ScanIndexForward=False)
    items = response.get("Items", [])

    # Extract the relevant data and order chronologically
    messages = [{"username": x["Username"], "content": x["Content"]}
            for x in items]
    messages.reverse()

    # Send them to the client who asked for it
    data = {"messages": messages}
    _send_to_connection(connectionID, data, event)

    return _get_response(200, "Sent recent messages to '{}'."\
            .format(connectionID))


def send_message(event, context):
    """
    When a message is sent on the socket, verify the passed in token,
    and forward it to all connections if successful.
    """
    logger.info("Message sent on WebSocket.")

    # Ensure all required fields were provided
    body = _get_body(event)
    if not isinstance(body, dict):
        logger.debug("Failed: message body not in dict format.")
        return _get_response(400, "Message body not in dict format.")
    for attribute in ["token", "content"]:
        if attribute not in body:
            logger.debug("Failed: '{}' not in message dict."\
                    .format(attribute))
            return _get_response(400, "'{}' not in message dict"\
                    .format(attribute))

    # Verify the token
    try:
        payload = jwt.decode(body["token"], "FAKE_SECRET", algorithms="HS256")
        username = payload.get("username")
        logger.info("Verified JWT for '{}'".format(username))
    except:
        logger.debug("Failed: Token verification failed.")
        return _get_response(400, "Token verification failed.")

    # Get the next message index
    # (Note: there is technically a race condition where two
    # users post at the same time and use the same index, but
    # accounting for that is outside the scope of this project)
    table = dynamodb.Table("serverless-chat_Messages")
    response = table.query(KeyConditionExpression="Room = :room",
            ExpressionAttributeValues={":room": "general"},
            Limit=1, ScanIndexForward=False)
    items = response.get("Items", [])
    index = items[0]["Index"] + 1 if len(items) > 0 else 0

    # Add the new message to the database
    timestamp = int(time.time())
    content = body["content"]
    table.put_item(Item={"Room": "general", "Index": index,
            "Timestamp": timestamp, "Username": username,
            "Content": content})

    # Get all current connections
    table = dynamodb.Table("serverless-chat_Connections")
    response = table.scan(ProjectionExpression="ConnectionID")
    items = response.get("Items", [])
    connections = [x["ConnectionID"] for x in items if "ConnectionID" in x]

    # Send the message data to all connections
    message = {"username": username, "content": content}
    logger.debug("Broadcasting message: {}".format(message))
    data = {"messages": [message]}
    for connectionID in connections:
        _send_to_connection(connectionID, data, event)
    return _get_response(200, "Message sent to {} connections."\
            .format(len(connections)))

def ping(event, context):
    """
    Sanity check endpoint that echoes back 'PONG' to the sender.
    """
    logger.info("Ping requested.")
    return _get_response(200, "PONG!")

