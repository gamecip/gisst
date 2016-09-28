/**
 * Created by erickaltman on 4/3/16.
 */

importScripts('async.js');
importScripts('stringview.js');
importScripts('sha1.js');

function addPerformanceVideoURL(perfUUID){ return "/performance/" + perfUUID + '/add_video_data'}

function asyncSaveVideoFile(targetURL, data, callback){
    var tasks = [];
    var chunkIndex = 0;
    var chunkSize = 1048576;
    var totalBytesSent = 0;
    var sha1 = SHA1Generator.calcSHA1FromByte(data.buffer);

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
        tasks.push(createSaveFileChunkTask(targetURL, sha1, chunkIndex, chunkData, self.totalChunks));
        totalBytesSent += chunkSize;
        chunkIndex++;
    }

    async.parallel(tasks, function(err, results){
        callback(err, results)
    })
}

function createSaveFileChunkTask(targetURL, sha1Hash, chunkId, chunkData, totalChunks){
    return function(cb){
        var xhr = new XMLHttpRequest();
        var fdata = new FormData();
        fdata.append('total_chunks', '' + totalChunks); //convert to strings
        fdata.append('chunk_id', '' + chunkId);
        fdata.append('chunk_data', StringView.bytesToBase64(chunkData));
        fdata.append('sha1_hash', sha1Hash);
        fdata.append('chunk_size', chunkData.length);
        xhr.open("POST", targetURL, true);
        xhr.onload = function(e){
            self.chunksSent++;
            // PROGRESS Message
            self.postMessage({type: 'progress',
                chunkId: chunkId,
                totalChunks: self.totalChunks,
                percent: self.chunksSent / self.totalChunks,
                uuid: self.perfUUID
            });
            cb(null, xhr.response)
        };
        xhr.send(fdata);
    }
}

self.chunksSent = 0;

onmessage = function(e){
    self.perfUUID = e.data.perfUUID;
    var targetURL = addPerformanceVideoURL(self.perfUUID);
    
    self.postMessage({type: "dataCheck", data: e.data});

    asyncSaveVideoFile(targetURL, e.data.data, function(err, results){
        if(err){
            // ERROR Message
            self.postMessage({type: 'error', uuid: self.perfUUID, message: err})
        }else{
            // FINISHED Message
            self.postMessage({type: 'finished', uuid: self.perfUUID})
        }
    })
};

