/* custom.js */

var socket;

// Connect to the websocket and setup listeners
function setupWebsocket(sessionKey, username) {
    socket = new ReconnectingWebSocket("wss://0hhv85vkol.execute-api.us-east-1.amazonaws.com/dev?sessionid=" + sessionKey);

    socket.onopen = function(event) {
        console.log("Socket is open!");
        console.log(event);
    }

    socket.onmessage = function(message) {
        var data = JSON.parse(message.data);
        if ($("#message-container").children(0).attr("id") == "empty-message") {
            $("#message-container").empty();
        }
        if (data["username"] === username) {
            $("#message-container").append("<div class='message self-message'><b>(You)</b> " + data["content"]);
        } else {
            $("#message-container").append("<div class='message'><b>(" + data["username"] + ")</b> " + data["content"]);
        }
    };
}

// Sends a message to the websocket using the text in the post bar
function postMessage(sessionKey, username) {
    var content = $("#post-bar").val();
    if (content !== "") {
        data = {"action": "sendMessage", "username": username, "content": content};
        socket.send(JSON.stringify(data));
        $("#post-bar").val("");
    }
}
