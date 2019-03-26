var originalResults;
var actionRegex = /^(\/?[A-Za-z]{3}\/?|)$/;

function clearResults() {
    $("#results").html(originalResults);
}

function cleanQueryText(queryText) {
    var cleaned = queryText.trim();
    if (cleaned.length > 0 && cleaned[0] === "/") {
        cleaned = cleaned.substr(1);
    }
    return cleaned;
}

function isValidSearchQuery(queryText) {
    return (queryText !== "/") && (queryText !== "") &&
        !queryText.includes(".");
}

function isValidActionQuery(queryText) {
    return queryText.match(actionRegex) != null;
}

function performSearch(queryText) {
    if (!isValidSearchQuery(queryText)) {
        clearResults();
        return;
    }
    $.get(queryText, function(data) {
        if (data === "" || data === "\n") {
            clearResults();
        } else {
            var splitData = data.split("\n").slice(0, -1);
            $("#results").html("")
            for (var i = 0; i < splitData.length; i++) {
                var courseSplit = splitData[i].split(/\s+/);
                var courseId = courseSplit.slice(0, 2).join(" ");
                var courseTitle = courseSplit.slice(2).join(" ");
                $("#results").append("<p><b>" + courseId + "</b>" +
                    courseTitle + "</p>");
                if (i < splitData.length - 1) {
                    $("#results").append("<hr/>");
                }
            }
        }
    });
}

function performCount(queryText) {
    if (!isValidActionQuery(queryText)) {
        clearResults();
        return;
    }
    $.get("count/" + queryText, function(data) {
        if (data === "" || data === "\n") {
            clearResults();
        } else {
            var splitData = data.split("\n").slice(0, -1);
            $("#results").html("")
            for (var i = 0; i < splitData.length; i++) {
                var resultSplit = splitData[i].split(/\s+/);
                $("#results").append("<p><b>" + resultSplit[0] + "</b>" +
                    resultSplit[1] + "</p>");
                if (i < splitData.length - 1) {
                    $("#results").append("<hr/>");
                }
            }
        }
    });
}

function performClear(queryText) {
    if (!isValidActionQuery(queryText)) {
        $("#results").html("<p>Failed to clear query counts</p>");
        return;
    }
    $.get("clear/" + queryText, function(data) {
        if (data === "\n") {
            $("#results").html("<p>Done</p>");
        } else {
            $("#results").html("<p>Failed to clear query counts</p>");
        }
    });
}

$(document).ready(function() {
    originalResults = $("#results").html();
    $("#search-bar").on('keypress', function(e) {
        if (e.which == 13) {
            $(this).attr("disabled", "disabled");
            performSearch(cleanQueryText($(this).val()));
            $(this).removeAttr("disabled");
        }
    });
    $("#search-btn").click(function() {
        performSearch(cleanQueryText($("#search-bar").val()));
    });
    $("#count-btn").click(function() {
        performCount(cleanQueryText($("#search-bar").val()));
    });
    $("#clear-btn").click(function() {
        performClear(cleanQueryText($("#search-bar").val()));
    });
});
