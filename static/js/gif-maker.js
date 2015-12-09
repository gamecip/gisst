/**
 * Created by erickaltman on 12/8/15.
 */

$(function(){
    videojs("video_file", {}, function(){
        var videoDiv = $('#video_file_html5_api');
        var startMarker = $('#startMarkerButton');
        var endMarker = $('#endMarkerButton');
        var makeGIF = $('#makeGifButton');
        var gifDeposit = $('#gifDeposit');
        var startTimeText = $('#startTime');
        var endTimeText = $('#endTime');

        startMarker.click(function(e){
            startTimeText.text(Math.floor(videoDiv[0].currentTime));
        });

        endMarker.click(function(e){
            endTimeText.text(Math.ceil(videoDiv[0].currentTime));
        });

        makeGIF.click(function(e){
            e.preventDefault();
            var start = parseInt(startTimeText.text());
            var end = parseInt(endTimeText.text());
            if(end - start > 0 && start < end){
                $.ajax({
                    type: "POST",
                    url: "/gif",
                    data: {
                        startTime: startTimeText.text(),
                        endTime: endTimeText.text(),
                        source_hash: $('td:contains("replay_source_file_ref")').next().text(),
                        uuid: $('td').filter(function(index) { return $(this).text() === "uuid";}).next().text()
                    },
                    success: addGifToPage
                });
                gifDeposit.append("<p>Giffing...</p>");
            }
        });

        function addGifToPage(data){
            gifDeposit.empty();
            gifDeposit.append("<img src='"+data['gif_location']+"'/>");
        }


    });
});
