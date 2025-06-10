$(document).ready(function () {
    $("#creditCardTable").tablesorter({
        theme: "bootstrap",
        headerTemplate: "{content}",
        widgets: ["zebra", "columns"],
        widgetOptions: {
            zebra: ["even", "odd"],
        },
        // Default sort: first column (Card Name) ascending
        sortList: [[0, 0]],
        headers: {
            5: { sorter: false } // Disable sorting on Bonus Categories (6th column, 0-indexed)
        }
    });
}); 