/**
 * Created by erickaltman on 5/7/16.
 */

/*
* Things to accomplish with this
* move all save state code to this worker, see what you can do with the post information
* 
* This includes save state for:
*   DOS games
*
* Other things include message to save state containing state array:
*   save-worker.postMessage
*   queue should spawn new worker for each save state task
* 
* */

importScripts('async.js');
importScripts('stringview.js');
importScripts('sha1.js');

function addStateRecordURL(gameUUID){ return "/state/" + gameUUID + '/add' }
function addStateDataURL(stateUUID){ return "/state/" + stateUUID + '/add_data' }
function addRLStateDataURL(stateUUID){ return "/state/" + stateUUID + '/add_rl_data'}
function addExtraFileRecordURL(stateUUID){ return "/extra_file/" + stateUUID + '/add'}


//post Message function, needs all information about state save

function asyncSaveStateRunLengthData(encodedObj, callback){
    
    var fdata = new FormData();
    fdata.append('rl_starts', StringView.bytesToBase64(encodedObj.starts));
    fdata.append('rl_lengths', StringView.bytesToBase64(encodedObj.lengths));
    fdata.append('rl_starts_length', encodedObj.starts.length);
    fdata.append('rl_lengths_length', encodedObj.lengths.length);
    fdata.append('total_length', encodedObj.totalLength);
    
    var xhr = new XMLHttpRequest();
    xhr.open("POST", addRLStateDataURL(uuid), true);
    xhr.onload = function(e){
        callback(null, xhr.response);
    };
    xhr.send(fdata);
    
}

function asyncFileSaveTasks(fi, fm, cb){
    var tasks = [];
    // Organize individual POSTs for files
    for(var file in fm){
        var cleanFilePath;
        if(file.match(/^\//)) cleanFilePath = file.slice(1); //if there is a leading slash remove it
        var fileObj = {
            extra_file_data: StringView.bytesToBase64(fm[file]),
            sha1_hash: SHA1Generator.calcSHA1FromByte(fm[file]),
            data_length: fm[file].length,
            rel_file_path: cleanFilePath
        };
        // Make sure it's a known file otherwise make an assumption about executable
        if(cleanFilePath in fi)
        {
            fileObj.is_executable = fi[cleanFilePath].isExecutable;
            fileObj.main_executable = fi[cleanFilePath].mainExecutable;
        }else{
            var ext = cleanFilePath.split(".").pop();
            if(ext === "EXE" || ext == "exe")
            {
                fileObj.is_executable = true;
                fileObj.main_executable = false;
            }
        }
        self.postMessage({type:'stdout', 
            message:"Creating file save for: " +cleanFilePath+ " with hash: " + fileObj.sha1_hash});
        tasks.push(createFilePathPostTask(fileObj, uuid))
    }

    //Run POSTs in parallel and aggregate results
    async.series(tasks, function(err, results){
        if (err)
            self.postMessage({type:'stdout', message: "Error with async file saves for state " + uuid});
        cb(err);
    });
}

function createFilePathPostTask(fileObject){
    return function(cb){
        var xhr = new XMLHttpRequest();
        var fdata = new FormData();
        for(var prop in fileObject){
            if(fileObject.hasOwnProperty(prop)){
                var val = fileObject[prop];
                if(typeof(val) !== 'string') val = '' + val; //coerce to string
                fdata.append(prop, val)
            }
        }
        xhr.open("POST", addExtraFileRecordURL(uuid), true);
        xhr.onload = function(e){
            cb(null, xhr.response);
        };
        xhr.send(fdata);
    }
}

var uuid;

onmessage = function(e){
    self.postMessage({type:'stdout', message:'received run length data'});
    var fm = e.data.fileMapping;
    uuid = e.data.uuid;
    var fi = e.data.fileInformation;
    var data = e.data.data;
    
    var tasks = [
        async.apply(asyncSaveStateRunLengthData, data.encodedObj),
        async.apply(asyncFileSaveTasks, fi, fm)
    ];
    
    async.series(tasks, function(err, results){
        self.postMessage({type:"finished", data: data})
    })
};
