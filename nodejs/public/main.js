$(function () {

    $("#chart").height($(window).height() - $("#header").height() * 2);

    var data_points = [{
        values: [],
        key: 'AAPL'
    }];

    var chart = nv.models.lineChart()
        .interpolate('monotone')
        .margin({
            bottom: 100
        })
        .useInteractiveGuideline(true)
        .showLegend(true)
        .color(d3.scale.category10().range());

    chart.xAxis
        .axisLabel('Time')
        .tickFormat(formatDateTick);

    chart.yAxis
        .axisLabel('Price');

    nv.addGraph(loadGraph);

    function loadGraph() {
        "use strict";
        d3.select('#chart svg')
            .datum(data_points)
            .transition()
            .duration(5)
            .call(chart);

        nv.utils.windowResize(chart.update);
        return chart;
    }

    function newDataCallback(message) {
        "use strict";
        var parsed = JSON.parse(message);
        var timestamp = parsed['timestamp'];
        var average = parsed['average'];
        var point = {};
        point.x = timestamp;
        point.y = average;

        console.log(point);

        data_points[0].values.push(point);
        if (data_points[0].length > 100) {
            data_points[0].values.shift()
        }
        loadGraph();
    }

    function formatDateTick(time) {
        "use strict";
        var date = new Date(time * 1000);
        return d3.time.format('%H:%M:%S')(date);
    }

    var socket = io();

    // - Whenever the server emits 'data', update the flow graph
    socket.on('data', function (data) {
    	newDataCallback(data);
    });
});