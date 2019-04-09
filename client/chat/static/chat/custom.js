/* custom.js */

var socket;

// Connect to the websocket and setup listeners
function setupWebsocket(sessionKey, username) {
    socket = new ReconnectingWebSocket("wss://0hhv85vkol.execute-api.us-east-1.amazonaws.com/dev?sessionid=" + sessionKey);

    socket.onopen = function(event) {
        console.log("Socket is open!");
        data = {"action": "getRecentMessages"};
        socket.send(JSON.stringify(data));
    }

    socket.onmessage = function(message) {
        var data = JSON.parse(message.data);
        data["messages"].forEach(function(message) {
            if ($("#message-container").children(0).attr("id") == "empty-message") {
                $("#message-container").empty();
            }
            if (message["username"] === username) {
                $("#message-container").append("<div class='message self-message'><b>(You)</b> " + message["content"]);
            } else {
                $("#message-container").append("<div class='message'><b>(" + message["username"] + ")</b> " + message["content"]);
            }
            $("#message-container").children().last()[0].scrollIntoView();
        });
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
