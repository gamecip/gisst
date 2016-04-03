/**
 * Created by erickaltman on 4/3/16.
 */

importScripts('async.js');
importScripts('stringview.js');
importScripts('sha1.js');

function addPerformanceVideoURL(perfUUID){ return "/performance/" + perfUUID + '/add_video_data'}

function asyncSaveVideoFile(perfUUID, targetURL, data, callback){
    var tasks = [];
    var chunkIndex = 0;
    var chunkSize = 1048576;
    var totalBytesSent = 0;
    var md5 = SHA1Generator.calcSHA1FromByte(data.buffer);

    self.totalChunks = Math.ceil(data.buffer.length / chunkSize);

    while(totalBytesSent < data.buffer.length){
        var adjustedChunkSize;
        var dataRemaining = data.buffer.length - chunkIndex * chunkSize;
        if(dataRemaining >= 0 && dataRemaining < chunkSize){
            adjustedChunkSize = dataRemaining;
        } else if(dataRemaining < 0){
            adjustedChunkSize = chunkSize - dataRemaining;
        } else {
            adjustedChunkSize = chunkSize;
        }

        var chunkData = new Uint8Array(data.buffer, chunkIndex * chunkSize, adjustedChunkSize);
        tasks.push(createSaveFileChunkTask(targetURL, md5, chunkIndex, chunkData, self.totalChunks));
        totalBytesSent += chunkSize;
        chunkIndex++;
    }

    async.parallel(tasks, function(err, results){
        callback(err, results)
    })
}

function createSaveFileChunkTask(targetURL, md5Hash, chunkId, chunkData, totalChunks){
    return function(cb){
        var xhr = new XMLHttpRequest();
        var params = "total_chunks=" + totalChunks +
                "&chunk_id=" + chunkId +
                "&chunk_data=" + StringView.bytesToBase64(chunkData) +
                "&md5_hash=" + md5Hash +
                "&chunk_size=" + chunkData.length;
        xhr.open("POST", targetURL, true);
        xhr.onload = function(e){
            self.chunksSent++;
            // PROGRESS Message
            self.postMessage({type: 'progress',
                chunkId: chunkId,
                totalChunks: totalChunks,
                percent: self.chunksSent / self.totalChunks});
            cb(null, xhr.response)
        };
        xhr.send(params);
    }
}

var totalChunks;
var chunksSent = 0;

onmessage = function(e){
    var performanceUUID = e.data.performanceUUID;
    var targetURL = addPerformanceVideoURL(performanceUUID);

    asyncSaveVideoFile(performanceUUID, targetURL, e.data, function(err, results){
        if(err){
            // ERROR Message
            self.postMessage({type: 'error', message: err})
        }else{
            // FINISHED Message
            self.postMessage({type: 'finished'})
        }
    })
};

