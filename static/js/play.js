/**
 * Citetool Editor Performance and State Creation Tool
 * Created by erickaltman on 2/29/16.
 */
var CiteManager;
$(function() {

CiteManager = (function(modules){
    
    //MM------------MODULE MANAGEMENT
    var ui = modules.ui;
    

    //CNG-----------CONSTANTS/GLOBALS--------------------
    var SINGULAR_STATE = "singleState";
    var DEPENDENT_STATE = "dependentState";
    var LZMA_WORKER_PATH = "/static/js/lzma_worker.js";

    /*Reference Tracking for LZMA Compression
     * (declaring workers inside local scope can mark them for garbage collection)
     * This prevents that by keeping the references to the worker alive (in scope)
     */
    var lzmas = {};
    var lzmaCount = 0;

    //UTF-----------UTILITY FUNCTIONS--------------------

    // API Call URLs
    //JSON
    function jsonGameInfoURL(uuid){ return "/json/game_info/" + uuid; }
    function jsonStateInfoURL(uuid){ return "/json/state_info/" + uuid; }
    function jsonPerformanceInfoURL(uuid){ return "/json/performance_info/" + uuid; }

    function asyncGetStateInfo(context, info, callback){
        $.get(jsonStateInfoURL(info.record.uuid), "", function(info){ callback(null, context, info)})
    }

    function asyncGetGameInfo(context, info, callback){
        $.get(jsonGameInfoURL(info.record.uuid), "", function(info){ callback(null, context, info)} )
    }

    function asyncGetPerformanceInfo(uuid, callback){
        $.get(jsonPerformanceInfoURL(uuid), "", function(info){ callback(info)})
    }

    //Record Creation
    function addStateRecordURL(gameUUID){ return "/state/" + gameUUID + '/add' }
    function addStateDataURL(stateUUID){ return "/state/" + stateUUID + '/add_data' }
    function addStateScreenURL(stateUUID){ return "/state/" + stateUUID + '/add_screen_data' }
    function addPerformanceRecordURL(gameUUID){ return "/performance/" + gameUUID + '/add'}
    function updatePerformanceRecordURL(perfUUID){ return "/performance/" + perfUUID + '/update'}
    function updateGameRecordURL(gameUUID){ return "/game/" + gameUUID + '/update'}
    function updateStateRecordURL(stateUUID){ return "/state/" + stateUUID + '/update'}

    function addStateRecordAJAX(context, stateInfo, callback){
        var dataObject = {};
        //  Copy additional descriptions if needed
        for(var key in stateInfo.record){
            dataObject[key] = stateInfo.record[key]
        }
        //Need to wrap callback function to pass null for err and ignore all but returned JSON data
        $.post(addStateRecordURL(context.currentGame.record.uuid),
            dataObject,
            function(sInfo){ callback(null, context, sInfo)});
    }

    function addPerformanceRecordAJAX(context, record, callback){
        $.post(addPerformanceRecordURL(context.currentGame.record.uuid),
            {record: JSON.stringify(record)},
            function(info){
                callback(null, context, info)
            });
    }
    

    //Compression Functions
    function decompressStateByteArray(context, info, data, callback){
        var lzma = new LZMA(LZMA_WORKER_PATH);
        if(data.compressed){
            lzma.decompress(data.buffer,
                function on_finish(result, err){
                    if (err) console.log("Error with decompression of state data for " + info.uuid);
                    var d = {};
                    //Copy keys that we don't care about
                    for(var key in data){
                        d[key] = data[key];
                    }
                    //Change the ones we do
                    d.buffer = result;
                    d.data_length = result.length;
                    d.compressed = false;
                    d.encoding = "";
                    lzma.worker().terminate(); //needed since lzma.js does not check for existing worker, and it is not garbage collected (don't know if still true???)
                    //Return new data object
                    callback(err, context, info, d)
                },
                function on_progress(percent){
                    //TODO: progress update for state load might not be needed
                })
        }else{
            //Nothing to decompress, so just ignore
            callback(null, context, info, data)
        }
    }

    function singleCompressByteArray(buffer, callback){
        console.log("STARTING SINGLE COMPRESSION");
        var lzmasKey = "lzma" + lzmaCount;
        lzmaCount++; //hopefully this will work, not particularly thread safe, but async js is not really threaded anyway
        lzmas[lzmasKey] = new LZMA(LZMA_WORKER_PATH);
        lzmas[lzmasKey].compress(buffer, 1,
            function(r, e){
                lzmas[lzmasKey].worker().terminate();
                delete lzmas[lzmasKey];
                callback(e, r)});
        //function(per){console.log(per)}); turn on if there's any issue with compression
    }

    function singleDecompressByteArray(buffer, callback){
        var lzma = new LZMA(LZMA_WORKER_PATH);
        lzma.decompress(buffer, function(r, e){ lzma.worker().terminate(); callback(e, r)})
    }

    function runLengthEncode(buffer){
        var runStarts = new Uint8Array(buffer.length);
        var runLengths = new Uint32Array(buffer.length);
        var curByte = buffer[0];
        var curRunLength = 0;
        var runStartsIndex = 0;
        var runLengthsIndex = 0;

        for(var i = 0, len = buffer.length; i < len; i++){
            if(curByte == buffer[i]){
                curRunLength++;
            }else {
                runStarts[runStartsIndex] = curByte;
                runLengths[runLengthsIndex] = curRunLength;
                curByte = buffer[i];
                curRunLength = 1;
                runStartsIndex++;
                runLengthsIndex++;
            }
        }
        // Store last values
        runStarts[runStartsIndex] = curByte;
        runLengths[runLengthsIndex] = curRunLength;
        if(runStartsIndex != runLengthsIndex) throw Error('Run length encode error, RS: '+runStartsIndex+' not equal to RL: '+runLengthsIndex);
        // Shorten arrays if possible
        if(runStartsIndex < buffer.length)
            runStarts = runStarts.slice(0, runStartsIndex + 1);
        runLengths = runLengths.slice(0, runLengthsIndex + 1);
        return {starts: runStarts, lengths: new Uint8Array(runLengths.buffer), totalLength: buffer.length}
    }

    function runLengthDecode(runStarts, runLengths, totalLength){
        var buffer = new Uint8Array(totalLength);
        var rl = new Uint32Array(runLengths.buffer);
        var index = 0;
        for(var i = 0, len = runStarts.length; i < len; i++){
            var byte = runStarts[i];
            for(var j = 0, len1 = rl[i]; j < len1; j++){
                buffer[index] = byte;
                index++;
            }
        }
        if(index != totalLength) throw Error("Run Length Decode Error, i: "+index+" not equal to tl: "+totalLength);
        return buffer;
    }

    function runLengthCompressByteArray(data, callback){
        var tasks;
        if(!data.compressed)
        {
            var encoded = runLengthEncode(data.buffer);
            tasks = [
                async.apply(singleCompressByteArray, encoded.starts),
                async.apply(singleCompressByteArray, encoded.lengths)
            ];
        }
        async.parallel(tasks, function(err, results){
            if(tasks){
                data.encodedObj = {
                    starts: results[0],
                    lengths: results[1],
                    totalLength: encoded.totalLength
                };
                data.compressed = true;
            }
            callback(null, data);
        });
    }

    function runLengthDecompressByteArray(context, info, data, callback){
        var tasks;
        if(data.compressed)
        {
            tasks = [
                async.apply(singleDecompressByteArray, data.encodedObj.starts),
                async.apply(singleDecompressByteArray, data.encodedObj.lengths)
            ];
        }
        async.parallel(tasks, function(err, results){
            if(tasks){
                data.buffer = runLengthDecode(results[0], results[1], data.encodedObj.totalLength);
                data.compressed = false;
                data.encoding = "";
                data.encodedObj = "";
            }
            callback(null, context, info, data);
        });
    }


    //EMC-----------EMULATION CONTEXT MANAGEMENT---------
    var contextFactory = (function(){
        var counter = 0;
        var contextHash = {};
        return {
            getNewContext: function(){
                var nc = {
                    id: counter,
                    emu: "",
                    lastState: "",
                    availableStates: [],
                    availablePerformances: [],
                    currentGame: "",
                    currentPerformance: "",
                    hasRecording: false
                };
                contextHash[counter] = nc;
                counter++;
                return nc;
            },
            currentContexts: function(){
                return contextHash;
            }
        }
    })();

    function updateState(context, info, data){
        if(!context.lastState) context.lastState = {};
        context.lastState.record = info.record;
        context.lastState.data = data;
        context.lastState.fileMapping = info.fileMapping || "";
        context.lastState.fileInformation = info.fileInformation || "";
        context.lastState.fileURL = info.stateFileURL;
        context.availableStates = info.availableStates;

        if(!(info.record.uuid in statesCache)){
            statesCache[info.record.uuid] = {info: info, data: data};
        }
    }

    function updateGame(context, info){
        if(!context.currentGame) context.currentGame = {};
        context.currentGame.record = info.record;
        context.currentGame.isSingleFile = $.isEmptyObject(info.fileMapping);
        context.currentGame.fileURL = info.gameFileURL;
        if(!$.isEmptyObject(info.fileMapping)) context.currentGame.fileMapping = info.fileMapping;
        if(!$.isEmptyObject(info.fileInformation)) context.currentGame.fileInformation = info.fileInformation;
        context.availableStates = info.availableStates;
        context.availablePerformances = info.availablePerformances;
    }

    function updatePerformance(context, info){
        if(!context.currentPerformance) context.currentPerformance = {};
        context.currentPerformance.record = info.record;
        context.currentPerformance.linkedStates = info.linkedStates ? info.linkedStates : [];
        context.availablePerformances = info.availablePerformances ? info.availablePerformances : [];
    }

    //UCM-----UI CREATION AND MANAGEMENT---------

    function createUIForContext(rootDivId, contextId){
        ui.createUI(rootDivId, contextId)
    }

    //SSF-----------SAVE STATE FUNCTIONS----------------

    var saveStateDataQueue = async.queue(processSaveStateData, 2);

    function initSaveState(context, record, callback){
        var saveTimeInt = Date.now();
        record.emulator = context.emu.emulator;
        if(!record.description)
            record.description = "State for " + context.currentGame.record.title + " at clock time: " + new Date(saveTimeInt).toUTCString();

        context.emu.saveState(function(stateData){
            //Get state data description
            if(context.emu.usesHeapSave){
                if(context.emu.emterpreted)
                    record.emt_stack_pointer = stateData.emtStack;
                record.stack_pointer = stateData.stack;
                record.time = stateData.time;
            }

            addStateRecordAJAX(context, {record: record},
                function(err, context, info){
                    if(!context.emu.usesHeapSave){
                        saveStateDataQueue.push(createSaveStateDataTask(context,
                            info,
                            {buffer: stateData, compressed: false},
                            CiteState.canvasCaptureScreen(context.emu)
                        ), callback)
                    }else{
                        saveStateDataQueue.push(createSaveStateDataTask(context,
                            info,
                            {
                                buffer: new Uint8Array(stateData.heap),
                                compressed: false,
                                emtStack: stateData.emtStack,
                                stack: stateData.stack,
                                time: stateData.time
                            },
                            CiteState.canvasCaptureScreen(context.emu)
                        ), callback)
                    }
                });
        });
    }

    //State Save Task Factory Functions (just to make sure task object is consistent)
    function createSaveStateDataTask(context, gameInfo, stateData, screenData){
        //might add stateInfo as parameter if more complementary information is needed
        return {context: context, info: gameInfo, data: stateData, screen: screenData}
    }

    function asyncSaveStateData(info, data, callback){
        //Convert ByteArray to Base64 for transfer
        var tempArray = data.buffer;
        data.data_length = data.buffer.length;

        data.buffer = StringView.bytesToBase64(data.buffer);
        $.post(addStateDataURL(info.record.uuid), data, function(i){
            data.buffer = tempArray;
            callback(null, i, data)
        })
    }
    
    function asyncSaveStateScreenData(info, screen, callback){
        var post_data = {
            buffer: StringView.bytesToBase64(screen.data),
            width: screen.width,
            height: screen.height
        };
        $.post(addStateScreenURL(info.record.uuid), post_data, function(i){
            callback(null, i)
        })
    }

    //Manage the compression and uploading of save state data
    function processSaveStateData(task, callback){
        //Single save states do not need worker since low overhead
        if(task.context.emu.usesHeapSave){
            var saveStateWorker = new Worker("/static/js/save-state-worker.js");
            saveStateWorker.onmessage = function(e){
                var data = e.data;
                if(data.type === "stdout"){
                    console.log("[SAVE STATE W]: "+e.data.message);
                }else if(data.type === "error"){
                    console.log("[SAVE STATE W]: Error with "+data.uuid+" "+data.message);
                }else if(data.type === "finished"){
                    saveStateWorker.terminate();
                    asyncSaveStateScreenData(task.info, task.screen, function(){
                        asyncGetStateInfo(task.context, task.info, function(e, c, i){
                            updateState(c, i, data.data);
                            if(callback)
                                callback(null, c, i, data.data);
                        });
                    })
                }
            };

            if(task.context.emu.hasFileSystem){
                var fi;
                if(task.context.lastState){
                    fi = task.context.lastState.fileInformation;
                }else{
                    fi = task.context.currentGame.fileInformation;
                }
                task.context.emu.saveExtraFiles(task.context.emu.listExtraFiles(),
                    function(fm){
                        runLengthCompressByteArray(task.data, function(err, d){
                            saveStateWorker.postMessage({
                                data: d,
                                fileMapping: fm,
                                fileInformation: fi,
                                uuid: task.info.record.uuid
                            });
                        });
                    });

            }else{
                runLengthCompressByteArray(task.data, function(err, d){
                    saveStateWorker.postMessage({
                        data: d,
                        fileMapping: null,
                        fileInformation: null,
                        uuid: task.info.record.uuid
                    })
                });
            }
            //uses built-in save state
        }else {
            asyncSaveStateData(task.info, task.data, function(err, ti, td){
                if(err) console.log("Error with state save of " + task.info.record.uuid);
                asyncSaveStateScreenData(task.info, task.screen, function(){
                    asyncGetStateInfo(task.context, task.info, function(e, c, i){
                        updateState(c, i, td);
                        if(callback)
                            callback(null, c, i, td);
                    });
                })
            });
        }
    }

    //LSF------------LOAD STATE FUNCTIONS---------------
    var statesCache = {};

    function asyncLoadState(context, info, data, callback){
        // Decompress data if needed, otherwise just pass as is (decompress function will ignore uncompressed data)
        // Do not modify the data object directly, as it will get passed along to the cache
        // and we don't want uncompressed data in the cache since that might blow up the browser
        //TODO: Clean this up if runLength actually works
        function prepLoadState(err, c, i, d){
            var dataToLoad = {};
            if(!context.emu.usesHeapSave){
                dataToLoad = d.buffer;
            } else{
                dataToLoad.heap = d.buffer;
                dataToLoad.time = d.time;
                dataToLoad.emtStack = d.emtStack;
                dataToLoad.stack = d.stack;
                console.log("Loading state : " + info.record.description + "\nTime: " + new Date(d.time).toUTCString() +
                    "\nCompressed: " + d.compressed + "\nHeap Size:" + d.buffer.length + "\nStack: " + d.stack +
                    "\nEmtStack: " + d.emtStack
                )
            }
            //pass dataToLoad with uncompressed buffer to loadState, but pass original data object down the line
            context.emu.loadState(dataToLoad, function(){
                updateState(context, info, data);
                callback(context, info, data)
            })
        }
        // If run length encoded handle that
        // else just do a normal decode
        if('encodedObj' in data && data.encodedObj){
            runLengthDecompressByteArray(context, info, data, prepLoadState);
        }else{
            decompressStateByteArray(context, info, data, prepLoadState);
        }
    }

    function initLoadState(context, uuid, callback){
        //check cache
        if(uuid in statesCache && statesCache[uuid]){
            loadStateFromCache(context, statesCache[uuid], callback);
        } else {
            //init async if not found
            for(var i = 0; i < context.availableStates.length; i++){
                var state = context.availableStates[i];
                if(state.uuid === uuid){ //rely on var scoping to function
                    break;
                }
            }
            loadStateFromServer(createStateLoadTask(context, {record: state}), callback);
        }
    }

    //State Load Task, Identical to above for now
    function createStateLoadTask(context, stateInfo, stateData, stateType){
        return {context: context, info: stateInfo, data: stateData, type: stateType}
    }

    function preLoadStateFromServer(task, callback){
        async.waterfall([
            async.apply(asyncGetStateInfo, task.context, task.info),
            asyncLoadStateArray
        ], callback);
    }

    function asyncPreLoadStateFromServer(context, info, callback){
        preLoadStateFromServer(createStateLoadTask(context, info), callback)
    }

    function loadStateFromServer(task, callback){
        preLoadStateFromServer(task, function(err, context, info, data){
            if(task.context.emu.usesHeapSave){
                data.emtStack = info.record.emt_stack_pointer;
                data.stack = info.record.stack_pointer;
                data.time = info.record.time;
                data.compressed = info.record.compressed;
            }
            asyncLoadState(context, info, data, callback);
        })
    }

    function loadStateFromCache(context, cache, callback){
        //  Need to refresh state record before loading data from cache
        //  State's data is constant, but it's record info may change (i.e. be linked to a performance / have more sibling states)
        asyncGetStateInfo(context, cache.info, function(err, c, info){
            asyncLoadState(context, info, cache.data, callback);
        });
    }

    //Needed to separate state data load from emulator load so that we can loadState immediately on
    //emulation start up
    function loadStateForStartUp(context, info, data, callback){

        function prepForStartEmulation(err, c, i, d){
            //Need new dataObject so that cache is correct
            var dataToLoad = {};
            if(!c.emu.usesHeapSave){
                dataToLoad.heap = d.buffer;
                dataToLoad.emtStack = d.emtStack = info.record.emt_stack_pointer;
                dataToLoad.time = d.time = info.record.time;
                dataToLoad.stack = d.stack = info.record.stack_pointer;
            }else{
                dataToLoad = d.buffer;
            }
            //add compressed data to cache
            updateState(c, i, d);
            //overwrite lastState data with uncompressed data (will get replaced with cached data on next load)
            c.lastState.data = dataToLoad;
            callback(null, c);
        }

        data.compressed = info.record.compressed;

        if('encodedObj' in data){
            runLengthDecompressByteArray(context, info, data, prepForStartEmulation)
        }else{
            decompressStateByteArray(context, info, data, prepForStartEmulation)
        }
    }

    function asyncLoadStateArray(context, info, callback){
        var filesAcquired = 0;
        var filesRequired = 0;
        var rlStarts, rlLengths;

        if('stateFileURL' in info){
            makeXHRDataRequest(info.stateFileURL, singleOnload).send();
        }else if('rlStartsURL' in info && 'rlLengthsURL' in info){
            filesRequired = 2;
            makeXHRDataRequest(info.rlStartsURL, rlStartOnload).send();
            makeXHRDataRequest(info.rlLengthsURL, rlLengthOnload).send();
        }

        function makeXHRDataRequest(url, onload){
            var xhr = new XMLHttpRequest();
            xhr.open('GET', url, true);
            xhr.responseType = 'arraybuffer';
            xhr.onload = onload;
            return xhr;
        }

        function singleOnload(e){
            callback(null, context, info, {buffer: new Uint8Array(this.response), compressed: info.record.compressed})
        }

        function rlStartOnload(e){
            filesAcquired++;
            rlStarts = new Uint8Array(this.response);
            if(filesRequired == filesAcquired){
                callback(null, context, info, {encodedObj: {starts: rlStarts, lengths: rlLengths, totalLength: info.record.rl_total_length}})
            }
        }

        function rlLengthOnload(e){
            filesAcquired++;
            rlLengths = new Uint8Array(this.response);
            if(filesRequired == filesAcquired){
                callback(null, context, info, {encodedObj: {starts: rlStarts, lengths: rlLengths, totalLength: info.record.rl_total_length}})
            }
        }
    }

    //RPF------------RECORD PERFORMANCE FUNCTIONS--------------

    var savePerformanceDataQueue = async.queue(processPerformanceDataSave, 2);

    function asyncStartRecording(context, callback){
        console.log("RECORDING: " + context.emu.recording);
        if(!context.emu.recording){
            var options = {};
            context.emu.startRecording(function(){
                context.startedRecordingTime = Date.now(); //should this be before or after callback?
                callback(null, context)
            }, options);
        }else{
            callback(new Error("Cannot start recording on context "+context.id+" it is already recording"), context)
        }
    }

    function asyncStopRecording(context, callback){
        if(context.emu.recording){
            context.startedRecordingTime = 0;
            context.emu.finishRecording(function(videoData){
                callback({buffer: videoData, compressed: false})
            });
        }else{
            callback(new Error("Cannot stop recording on context "+context.id+" because it hasn't started"), context, {})
        }
    }

    function processPerformanceDataSave(task, callback){
        var saveWorker = new Worker("/static/js/save-video-worker.js");
        saveWorker.onmessage = function(e){
            var data = e.data;
            if(data.type === "progress"){
                console.log("Performance: " + data.uuid + " video save is " + data.percent + "% complete.")
            }else if(data.type === "error"){
                console.log("Error with performance " + data.uuid + " " + data.message);
            }else if(data.type === "finished"){
                console.log("Performance: " + data.uuid + " video save is complete.");
                saveWorker.terminate();
                if(callback)
                    callback();
            }else if(data.type === "stdout"){
                console.log(data.data);
            }
        };

        saveWorker.postMessage({
            perfUUID: task.uuid,
            data: task.data
        });
    }

    //EMF---------EMULATION MANAGEMENT FUNCTIONS--------------

    function asyncStartEmulation(context, callback){
        CiteState.cite.apply(this, prepArgsForCiteState(context, callback, {mute:true, recorder: {}}))
    }

    function asyncStartEmulationWithRecording(context, callback){
        var options = {mute: false, recorder:{autoStart: true}};
        if(context.emu.requiresSDL2){
            //Add callback to start recording once SDL context is loaded
            //if necessary
            triggerOnSDL2Available(context, function (context, timestamp){
                asyncStartRecording(context, callback);
            });
            options.recorder = {};
            //Initiate emulator setup without recording
            CiteState.cite.apply(this, prepArgsForCiteState(context, null, options))
        }else{
            CiteState.cite.apply(this, prepArgsForCiteState(context, callback, options))
        }
    }

    function prepArgsForCiteState(context, cb, options){
        var args = [
            context.id + "_emulationContainer",
            function(emu){
                context.emu = emu;
                if(cb)
                    cb(context);
            },
            context.currentGame.fileURL,
            null, //blank unless saveStateURL, used for NES / SNES and other systems with small save states
            null, //blank unless compressedSaveStateData, used for DOS and other large save states
            null  //blank unless dependent files
            //options are next argument if needed
        ];
        var hasFileSystem = context.emu.hasFileSystem;
        if(context.lastState){
            if(hasFileSystem){
                args[3] = context.lastState.data;
            }else{
                args[4] = context.lastState.data;
                if(!$.isEmptyObject(context.lastState.fileMapping)){
                    args[5] = context.lastState.fileMapping;
                }
            }
        }else if(!$.isEmptyObject(context.currentGame.fileMapping)){
            args[5] = context.currentGame.fileMapping;
        }
        if(options){
            args.push(options)
        }
        return args;
    }

    //DBF-----------DEBUGGING FUNCTIONS-----------------

    //SDL2 available check
    //hack to check when the audio node is ready to record and callback (mostly for autostart recording in DOSBOX)
    var checkSDL2Req = window.requestAnimationFrame(checkSDL2);
    var SDL2Callbacks = [];
    
    function checkSDL2(timestamp){
        if(window["SDL2"]){
            window.cancelAnimationFrame(checkSDL2Req);
            for(var co in SDL2Callbacks){
                var callbackObj = SDL2Callbacks[co];
                console.log("Triggering callback for context: "+callbackObj.context.id);
                callbackObj.context.SDL2Available = true;
                callbackObj.cb(callbackObj.context, timestamp);
            }
            SDL2Callbacks = [];
        }else{
            checkSDL2Req = window.requestAnimationFrame(checkSDL2);
        }
    }
    
    function triggerOnSDL2Available(context, cb){
        SDL2Callbacks.push({context:context, cb:cb})
    }


    //right apply for async partials, taken from:
    //http://aeflash.com/2013-06/async-and-functional-javascript.html
    function rightAsyncPartial(fn, thisArg){
        var boundArgs = Array.prototype.slice.call(arguments, 2);
        return function(){
            var args = Array.prototype.slice.call(arguments, 0);
            var callback = args.pop();
            //call fn with the args in the right order, (this, args...., callback)
            fn.apply(thisArg, args.concat(boundArgs).push(callback))
        }
    }

    //Debugging Timer For Actions
    var timingHash = {};

    function startTiming(name){
        timingHash[name] = Date.now();
        console.log("Started Timing Task: "+name+" at "+timingHash[name])
    }

    function stopTiming(name){
        var timeElapsed = Date.now() - timingHash[name];
        console.log("Task "+name+" completed in " + timeElapsed/1000.0 + " sec");
        delete timingHash[name];
    }

    //PSF--------PAGE SPECIFIC FUNCTIONS--------
    //todo: move these to a separate module for this page

    function initPageLoad(context, cb){
        //Get information about game for loading
        asyncGetGameInfo(context, {record: {uuid: gameUUID}},
            function(err, c, i){
                if(err) console.log("Error loading game " + gameUUID);
                updateGame(c, i);
                var tasks = [];
                // if loading into a previous save state, load state information and data
                if(stateUUID){
                    tasks = [
                        async.apply(asyncPreLoadStateFromServer, c, {record: {uuid: stateUUID}}),
                        loadStateForStartUp
                    ];
                }
                // after all that see if there's an error
                async.waterfall(tasks, function(err, c){
                    if(err) console.log("Error preloading state for page.");
                    cb();
                })
            });
    }

    return {
        // Direct exported functions are first (might move some of these to global scope?)
        jsonGameInfoURL: jsonGameInfoURL,
        jsonPerformanceInfoURL: jsonPerformanceInfoURL,
        jsonStateInfoURL: jsonStateInfoURL,
        initPageLoad: initPageLoad,
        createUIForContext: createUIForContext,
        // Functions that relate to or interact with internal context information
        getNewContext: function(){
            return contextFactory.getNewContext();
        },
        startEmulation: function(contextId, cb){
            asyncStartEmulation(this.getContextById(contextId), cb);
        },
        startEmulationWithState: function(contextId, stateUUID, cb){
            var me = this;
            asyncPreLoadStateFromServer(this.getContextById(contextId), {record: {uuid: stateUUID}},
                function(err, c, i, d){ //pre load returns compressed data, loadStateForStartUp
                    loadStateForStartUp(c, i, d, function(){
                        me.startEmulation(contextId, cb);
                    });
                })
        },
        loadPreviousState: function(contextId, cb){
            var ctx = this.getContextById(contextId);
            if(!ctx.lastState){
                cb(c)
            }
            if(ctx.emu.recording){
                this.startNewPerformanceWhileRecording(contextId, ctx.lastState.record.uuid, cb);
            }else{
                //If we aren't recording a performance, just load the state
                this.loadState(contextId, ctx.lastState.record.uuid, cb);
            }
        },
        saveState: function(contextId, cb){
            var record = {};
            var ctx = this.getContextById(contextId);
            if(ctx.emu.recording){
                var ti = Date.now() - ctx.startedRecordingTime;
                record.performance_uuid = ctx.currentPerformance.record.uuid;
                record.performance_time_index = ti;
                record.description = "State for performance: " + i.record.uuid + " at time index:" + ti + " at clock time: " + new Date(Date.now()).toUTCString();
            }
            initSaveState(ctx, record, function(err, c, i, d){cb(c)});
        },
        loadState: function(contextId, uuid, cb){
            initLoadState(this.getContextById(contextId), uuid, cb);
        },
        mute: function(contextId){
            var emu = this.getContextById(contextId).emu;
            if(emu){
                emu.setMuted(!emu.isMuted());
                return emu.isMuted();
            }else{
                return false;
            }
        },
        getContextById: function(id){
            return contextFactory.currentContexts()[id];
        },
        //All recording functions are repetitive and explicit because I kept confusing myself
        //with order of operations

        //Called to start a new performance on state load while recording
        //Links loaded state as source for new performance, links old performance as
        //derivative
        startNewPerformanceWhileRecording: function(contextId, loadStateUUID, cb){
            var oldPerformanceUUID = this.getContextById(contextId).currentPerformance.record.uuid;
            var title = "A performance of: " + this.getContextById(contextId).currentGame.record.title;
            //Create record for new performance
            addPerformanceRecordAJAX(this.getContextById(contextId), {previous_performance_uuid: oldPerformanceUUID, title: title}, function(err, c, i){
                var end_ti = Date.now() - c.startedRecordingTime;
                var newPerformanceUUID = i.record.uuid;
                var record = {
                    performance_uuid: oldPerformanceUUID,
                    performance_time_index: end_ti,
                    description: "State for performance: " + oldPerformanceUUID + " at time index: " + end_ti + " at clock time: " + new Date(Date.now()).toUTCString(),
                    action: 'save'
                };

                //Save state terminal
                initSaveState(c, record);

                //Update performance in context
                updatePerformance(c, i);

                //Stop current recording
                asyncStopRecording(c, function(videoData){
                    savePerformanceDataQueue.push({
                        uuid: oldPerformanceUUID,
                        data: videoData
                    })
                });

                //Load incoming state
                initLoadState(c, loadStateUUID, function(c, i, d){

                    //Link start load as start of new performance
                    this.updateCiteRecord(contextId, 'state', loadStateUUID,
                        {
                            performance_uuid: newPerformanceUUID,
                            performance_time_index: 0,
                            action: 'load'
                        }
                    );

                    //Start next recording
                    console.log("Calling after state load.");
                    asyncStartRecording(c, function(err, c){
                        cb(c);
                    });
                }.bind(this));
            }.bind(this))
        },
        startRecording: function(contextId, recordCb, stateCb){
            addPerformanceRecordAJAX(this.getContextById(contextId), {title: "A performance of " + this.getContextById(contextId).currentGame.record.title}, function(err, c, i){
                updatePerformance(c, i);
                if(c.emu){
                    var record = {
                        performance_uuid: i.record.uuid,
                        performance_time_index: 0,
                        description: "State for performance: " + i.record.uuid + " at time index: 0 at clock time: " + new Date(Date.now()).toUTCString()
                    };
                    initSaveState(c, record, stateCb);
                    asyncStartRecording(c, function(err, c){
                        recordCb(c);
                    })
                }else{
                    asyncStartEmulationWithRecording(c, function(err, c){
                        recordCb(c);
                    })
                }
            });
        },
        stopRecording: function(contextId, recordCb, stateCb){
            var ctx = this.getContextById(contextId);
            var ti = Date.now() - ctx.startedRecordingTime;
            var record = {
                performance_uuid: ctx.currentPerformance.record.uuid,
                performance_time_index: ti,
                description: "State for performance: " + ctx.currentPerformance.record.uuid + " at time index: " + ti + " at clock time: " + new Date(Date.now()).toUTCString()
            };
            initSaveState(ctx, record, stateCb);

            asyncStopRecording(ctx, function(videoData){
                savePerformanceDataQueue.push({
                    uuid: ctx.currentPerformance.record.uuid,
                    data: videoData
                }, function(){
                    $.get(jsonPerformanceInfoURL(ctx.currentPerformance.record.uuid),
                        function(i){
                            updatePerformance(ctx, i);
                            recordCb(ctx);
                    })
                })
            });

        },
        updateCiteRecord: function(contextId, recordType, uuid, updateData, cb){
            var ctx = this.getContextById(contextId);
            if(!$.isEmptyObject(updateData)){
                if(recordType === 'game'){
                    $.post(updateGameRecordURL(uuid), {update_fields: JSON.stringify(updateData)}, function(result){
                        asyncGetGameInfo(ctx, {record: JSON.parse(result)}, function(err, c, i){
                            updateGame(ctx, i);
                            if(cb)
                                cb(result);
                        });
                    });
                }else if(recordType === 'performance'){
                    $.post(updatePerformanceRecordURL(uuid), {update_fields: JSON.stringify(updateData)}, function(result){
                        asyncGetGameInfo(ctx, {record: {uuid: JSON.parse(result).game_uuid }}, function(err, c, i){
                            updateGame(ctx, i);
                            if(cb)
                                cb(result);
                        });
                    });
                }else if(recordType === 'state'){
                    $.post(updateStateRecordURL(uuid), {update_fields: JSON.stringify(updateData)}, function(result){
                        asyncGetGameInfo(ctx, {record: {uuid: result.game_uuid}}, function(err, c, i){
                            updateGame(ctx, i);
                            if(ctx.lastState && ctx.lastState.record.uuid === uuid){
                                ctx.lastState.record = result;
                            }
                            if(cb)
                                cb(result);
                        });
                    });
                }else{
                    console.log("Need a valid record type to update a record!")
                }
            }
        }
    }

}({ui:UI}));

    //Load initial page information into model
    var stateUUID = $('body').data('state-uuid');
    var gameUUID = $('body').data('game-uuid');
    var context0 = CiteManager.getNewContext();
    CiteState.scriptRoot = '/static/js/cite-game/';

    CiteManager.initPageLoad(context0, function(){ //Load page information
        CiteManager.createUIForContext(document.getElementById('uiBase'), context0.id); //Load UI
    });
});

