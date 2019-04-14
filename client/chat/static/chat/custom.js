/* custom.js */

var socket;

// Connect to the WebSocket and setup listeners
function setupWebSocket(endpoint, username, token) {
    socket = new ReconnectingWebSocket(endpoint + "?token=" + token);

    socket.onopen = function(event) {
        console.log("Socket is open!");
        data = {"action": "getRecentMessages"};
        socket.send(JSON.stringify(data));
    };

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
function postMessage(token) {
    var content = $("#post-bar").val();
    if (content !== "") {
        data = {"action": "sendMessage", "token": token, "content": content};
        socket.send(JSON.stringify(data));
        $("#post-bar").val("");
    }
}
