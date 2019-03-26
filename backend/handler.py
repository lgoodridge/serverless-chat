import boto3
import decimal
import json
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
    def _clean_data(data):
        if isinstance(data, list):
            return [_clean_data(x) for x in data]
        if isinstance(data, dict):
            return {k: _clean_data(v) for k, v in data.items()}
        if isinstance(data, decimal.Decimal):
            return int(data)
        return data
    if not isinstance(body, str):
        body = json.dumps(_clean_data(body))
    return {"statusCode": status_code, "body": body}


def _send_to_connection(connection_id, data, event):
    gatewayapi = boto3.client("apigatewaymanagementapi",
            endpoint_url= "https://" + event["requestContext"]["domainName"] +
                    "/" + event["requestContext"]["stage"])
    return gatewayapi.post_to_connection(ConnectionId=connection_id,
            Data=json.dumps(data).encode('utf-8'))


def connection_manager(event, context):
    """
    Handles connecting and disconnecting for the Websocket.

    Connect validates the passed in sessionID, and if successful,
    adds the connectionID to the database, and returns the ten
    most recent chat messages.

    Disconnect removes the connectionID from the database.
    """
    sessionID = event.get("queryStringParameters", {}).get("sessionid")
    connectionID = event["requestContext"].get("connectionId")

    if event["requestContext"]["eventType"] == "CONNECT":
        logger.info("Connect requested (SID: {}, CID: {})"\
                .format(sessionID, connectionID))

        # Ensure sessionID and connectionID are set
        if not sessionID:
            logger.debug("Failed: sessionid query parameter not provided.")
            return _get_response(400, "sessionid query parameter not provided.")
        if not connectionID:
            logger.error("Failed: connectionId value not set.")
            return _get_response(500, "connectionId value not set.")

        # Ensure sessionID is in the database
        table = dynamodb.Table("serverless-chat_Sessions")
        response = table.get_item(Key={"SessionID": sessionID})
        if not response.get("Item"):
            logger.debug("Failed: sessionid '{}' not registered."\
                    .format(sessionID))
            return _get_response(400, "sessionid not registered.")

        # Add connectionID to the database
        table = dynamodb.Table("serverless-chat_Connections")
        table.put_item(Item={"ConnectionID": connectionID})

        # Fetch the 10 most recent chat messages
        table = dynamodb.Table("serverless-chat_Messages")
        response = table.query(KeyConditionExpression="Room = :room",
                ExpressionAttributeValues={":room": "general"},
                Limit=10, ScanIndexForward=False)
        items = response.get("Items", [])
        return _get_response(200, items)

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
    Send back error when unrecognized websocket action is received.
    """
    logger.info("Unrecognized websocket action received.")
    return _get_response(400, "Unrecognized websocket action.")


def send_message(event, context):
    """
    When a message is sent on the socket, forward it to all connections.
    """
    logger.info("Message sent on websocket.")

    # Ensure all required fields were provided
    body = _get_body(event)
    if not isinstance(body, dict):
        logger.debug("Failed: message body not in dict format.")
        return _get_response(400, "Message body not in dict format.")
    for attribute in ["username", "content"]:
        if attribute not in body:
            logger.debug("Failed: '{}' not in message dict."\
                    .format(attribute))
            return _get_response(400, "'{}' not in message dict"\
                    .format(attribute))
    
    # Get all current connections
    table = dynamodb.Table("serverless-chat_Connections")
    response = table.scan(ProjectionExpression="ConnectionID")
    items = response.get("Items", [])
    connections = [x["ConnectionID"] for x in items if "ConnectionID" in x]
    
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
    table.put_item(Item={"Room": "general", "Index": index,
            "Timestamp": timestamp, "Username": body["username"],
            "Content": body["content"]})

    # Send the message data to all connections
    logger.debug("Broadcasted message: {}".format(body))
    for connectionID in connections:
        _send_to_connection(connectionID, body, event)
    return _get_response(200, "Message sent to {} connections."\
            .format(len(connections)))

def ping(event, context):
    """
    Sanity check endpoint that echoes back 'PONG' to the sender.
    """
    logger.info("Ping requested.")
    return _get_response(200, "PONG!")


def register_session(event, context):
    """
    Registers a user with a given session ID.
    """
    logger.info("Register session endpoint requested.")
    body = _get_body(event)

    # Ensure all attributes were provided
    if len(body) == 0:
        logger.debug("Failed: POST data not provided.")
        return _get_response(400, "POST data not provided.")
    for attribute in ["secret", "sessionid", "username"]:
        if attribute not in body:
            logger.debug("Failed: '{}' parameter not provided."\
                    .format(attribute))
            return _get_response(400, "'{}' parameter not provided."\
                    .format(attribute))

    # Ensure the shared secret is correct
    if body["secret"] != "SHARED_SECRET":
        logger.debug("Failed: shared secret was incorrect.")
        return _get_response(403, "Forbidden: incorrect shared secret.")

    # Add the session ID to the database
    timestamp = int(time.time())
    ttl = timestamp + (60 * 60 * 24)
    table = dynamodb.Table("serverless-chat_Sessions")
    table.put_item(Item={
            "SessionID": body["sessionid"],
            "Username": body["username"],
            "Timestamp": timestamp,
            "TTL": ttl,
    })
    return _get_response(200, "Register successful.")
