/**
 * Citetool Editor Performance and State Creation Tool
 * Created by erickaltman on 2/29/16.
 */
var CiteManager;
$(function() {

CiteManager = (function(modules){

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

    function asyncGetPerformanceInfo(context, info, callback){
        $.get(jsonPerformanceInfoURL(info.record.uuid), "", function(info){ callback(null, context, info)})
    }

    //Record Creation
    function addStateRecordURL(gameUUID){ return "/state/" + gameUUID + '/add' }
    function addStateDataURL(stateUUID){ return "/state/" + stateUUID + '/add_data' }
    function addStateScreenURL(stateUUID){ return "/state/" + stateUUID + '/add_screen_data' }
    function addPerformanceRecordURL(gameUUID){ return "/performance/" + gameUUID + '/add'}
    function updatePerformanceRecordURL(perfUUID){ return "/performance/" + perfUUID + '/update'}

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

    function addPerformanceRecordAJAX(context, callback){
        var title = context.ui.performanceTitle.val() || "A performance of " + context.currentGame.record.title;
        var description = context.ui.performanceDescription.val() || "";
        $.post(addPerformanceRecordURL(context.currentGame.record.uuid),
            {title: title, description: description},
            function(info){
                callback(null, context, info)
            });
    }

    //Compression Functions
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


    //EMC-----------EMULATION CONTEXT MANAGEMENT---------
    var contextFactory = (function(){
        var counter = 0;
        var contextHash = {};
        function increaseCount(){
            counter += 1;
        }
        function registerContext(id, context){
            contextHash[id] = context;
        }
        return {
            getNewContext: function(){
                var nc = {
                    id: counter,
                    emu: "",
                    lastState: "",
                    availableStates: [],
                    statesCache: {},
                    currentGame: "",
                    currentPerformance: "",
                    hasRecording: false,
                    ui: { //stubbed out here just for autocomplete convenience in IntelliJ
                        root: "",
                        emulationContainer: "",
                        startEmulationButton: "",
                        saveStateButton: "",
                        loadLastStateButton: "",
                        resetEmulationButton: "",
                        toggleAudioButton: "",
                        stateDescription: "",
                        gameInfo: "",
                        stateInfo: "",
                        mostRecentState: "",
                        stateListing: "",
                        performanceInfo: "",
                        startRecordingButton: "",
                        stopRecordingButton: "",
                        fileInformation: "",
                        performanceTitle: "",
                        performanceDescription: ""
                    },
                    stateDataSaveQueue: async.queue(processSaveStateData, 2),
                    performanceDataSaveQueue: async.queue(processPerformanceDataSave, 2)
                };
                registerContext(nc.id, nc);
                increaseCount();
                return nc;
            },
            currentContexts: function(){
                return contextHash;
            }
        }
    })();

    function updateFullContext(context){

        function getAndUpdateState(cb){
            async.waterfall([
                async.apply(asyncGetStateInfo, context, context.lastState),
                rightAsyncPartial(updateState, this, context.lastState.data)
            ], function(){ cb(null) })
        }

        function getAndUpdatePerformance(cb){
            async.waterfall([
                async.apply(asyncGetPerformanceInfo, context, context.currentPerformance),
                updatePerformance
            ], function(){ cb(null) })
        }

        function getAndUpdateGame(cb){
            async.waterfall([
                async.apply(asyncGetGameInfo, context, context.currentGame),
                updateGame
            ], function(){ cb(null) })
        }

        async.series([
            getAndUpdateGame,
            getAndUpdateState,
            getAndUpdatePerformance
        ], function(err, results){
            updateUI(context)
        })

    }

    function updateState(context, info, data){
        if(!context.lastState) context.lastState = {};
        context.lastState.record = info.record;
        context.lastState.data = data;
        context.lastState.fileMapping = info.fileMapping || "";
        context.lastState.fileInformation = info.fileInformation || "";
        context.lastState.fileURL = info.stateFileURL;
        context.availableStates = info.availableStates;

        if(!(info.record.uuid in context.statesCache)){
            context.statesCache[info.record.uuid] = {info: info, data: data};
        }

        updateStateUI(context);
    }

    function updateGame(context, info){
        if(!context.currentGame) context.currentGame = {};
        context.currentGame.record = info.record;
        context.currentGame.isSingleFile = $.isEmptyObject(info.fileMapping);
        context.currentGame.fileURL = info.gameFileURL;
        if(!$.isEmptyObject(info.fileMapping)) context.currentGame.fileMapping = info.fileMapping;
        if(!$.isEmptyObject(info.fileInformation)) context.currentGame.fileInformation = info.fileInformation;
        context.availableStates = info.availableStates;
        updateGameUI(context);
    }

    function updatePerformance(context, info, callback){
        if(!context.currentPerformance) context.currentPerformance = {};
        context.currentPerformance.record = info.record;
        context.currentPerformance.linkedStates = info.linkedStates;
        updatePerformanceUI(context, callback);
    }

    //UCM-----UI CREATION AND MANAGEMENT---------

    //TODO: lots of calls to createElementForContext, should probably just make an object and map function over it
    function createUIForContext(context, rootDivId){
        var $contextRoot, $emulationControls;
        if(rootDivId){
            $contextRoot = $('#' + rootDivId);
        } else {
            $contextRoot = $('<div/>', {id: context.id + "_root"})
        }
        //Set context root div
        context.ui.root = $contextRoot;

        //Emulation Container
        context.ui.emulationContainer = createElementForContext(context, "div", "emulationContainer", "", $contextRoot);
        context.ui.emulationContainer.css({ "height": "400px", width: "640px"});

        //Emulation Controls
        $emulationControls = createElementForContext(context, "div", "emulationControls", "", $contextRoot);
        context.ui.startEmulationButton = createElementForContext(context, "button", "startEmulationButton", "Loading emulation...",
            $emulationControls);
        context.ui.saveStateButton = createElementForContext(context, "button", "saveStateButton", "Save State",
            $emulationControls);
        context.ui.loadLastStateButton = createElementForContext(context, "button", "loadLastStateButton", "Load Last State",
            $emulationControls);
        context.ui.resetEmulationButton = createElementForContext(context, "button", "resetEmulationButton", "Reset Emulation",
            $emulationControls);
        context.ui.toggleAudioButton = createElementForContext(context, "button", "toggleAudioButton", "Audio Off",
            $emulationControls);

        //State Description
        $stateDescriptionDiv = createElementForContext(context, "div", "stateDescriptionDiv", "State Description: ", $contextRoot);
        context.ui.stateDescription = createElementForContext(context, "input", "stateDescriptionInput", "", $stateDescriptionDiv);
        context.ui.stateDescription.attr('type', 'text');

        //Game Information
        context.ui.gameInfo = createElementForContext(context, "div", "gameInfo", "<h3>Game Information</h3>", $contextRoot);

        //State Information
        context.ui.stateInfo = createElementForContext(context, "div", "stateInfo", "<h3>State Information</h3>", $contextRoot);
        context.ui.mostRecentState = createElementForContext(context, "div", "mostRecentState", "", context.ui.stateInfo);
        context.ui.stateListing = createElementForContext(context, "div", "stateListing", "<h4>Saved States</h4>", context.ui.stateInfo);

        //Performance Information
        context.ui.performanceInfo = createElementForContext(context, "div", "performanceInfo", "<h3>Performance Information</h3>", $contextRoot);
        context.ui.performanceTimer = createElementForContext(context, "div", "performanceTimer", "", context.ui.performanceInfo);
        $performanceTitleDiv = createElementForContext(context, "div", "performanceTitleDiv", "Title: ", context.ui.performanceInfo);
        context.ui.performanceTitle = createElementForContext(context, "input", "performanceTitleInput", "", $performanceTitleDiv);
        $performanceDescriptionDiv = createElementForContext(context, "div", "performanceDescriptionDiv", "Description: ", context.ui.performanceInfo);
        context.ui.performanceDescription = createElementForContext(context, "input", "performanceDescriptionInput", "", $performanceDescriptionDiv);

        //Performance Controls
        $performanceControls = createElementForContext(context, "div", "performanceControls", "", $contextRoot);
        context.ui.startRecordingButton = createElementForContext(context, "button", "startRecordingButton", "Loading emulation...", $performanceControls);
        context.ui.stopRecordingButton = createElementForContext(context, "button", "stopRecordingButton", "Stop Recording", $performanceControls);

        //File System Listing
        context.ui.fileInformation = createElementForContext(context, "div", "fileInformation", "<h3>File Information</h3>", $contextRoot);

        //Attach UI to Page
        $('body').append($contextRoot);
    }

    function createElementForContext(context, elementType, elementName, elementHtml, parentNode){
        return $("<"+elementType+"/>", {id: context.id +"_"+elementName, html: elementHtml}).appendTo(parentNode);
    }

    function updateUI(context, cb){
        async.series([
            async.apply(updateGameUI, context),
            updateStateUI,
            updatePerformanceUI
        ], cb)
    }

    function updateGameUI(context){
        if(!$.isEmptyObject(context.currentGame.fileInformation))
            updateFileListing(context);
        if(context.lastState)
            updateCurrentState(context);
        updateSaveStateListing(context);
    }

    function updateStateUI(context){
        updateCurrentState(context);
        updateSaveStateListing(context);
        updateFileListing(context)
    }

    function updatePerformanceUI(context, callback){
        if(callback){
            callback(null, context);
        }
    }

    function updateSaveStateListing(context){
        context.ui.stateListing.empty();
        if(context.availableStates.length > 0){
            context.ui.stateListing.append('<h4>Save States Available</h4>');
            $stateList = $("<ul/>");
            for(var i=0; i < context.availableStates.length; i++){
                var state = context.availableStates[i];
                $('<li/>', {
                    "class": context.id + "_loadableState",
                    text: state['description']
                }).attr('data-state-uuid', state['uuid'])
                    .appendTo($stateList);
            }
            context.ui.stateListing.append($stateList);
            $('.'+context.id+'_loadableState').click(createLoadableClickHandler(context))
        }
    }

    function updateFileListing(context){
        var fi;
        if("fileInformation" in context.currentGame){
            if(context.lastState){
                fi = context.lastState.fileInformation;
            }else{
                fi = context.currentGame.fileInformation;
            }
        }
        context.ui.fileInformation.empty();
        if(fi){
            context.ui.fileInformation.append('<h3>Current Active Files</h3>');
            $fileList = $('<ul/>');
            for(var filePath in fi){
                $fileList.append("<li>"+filePath+"</li>")
            }
            context.ui.fileInformation.append($fileList);
        }
    }

    function updateCurrentState(context){
        context.ui.mostRecentState.empty();
        if(context.lastState){
            context.ui.mostRecentState.append('<h4>Most Recent Save State</h4>');
            $('<div/>', {
                id: context.id + '_mostRecentStateDiv',
                text: context.lastState.record.description
            }).attr('data-state-uuid', context.lastState.record.uuid)
                .appendTo(context.ui.mostRecentState);
            $('#' + context.id + '_mostRecentStateDiv').click(createLoadableClickHandler(context))
        }
    }

    function createLoadableClickHandler(context){
        return function(event){
            var uuid = $(this).data('state-uuid');
            initLoadState(context, {record:{uuid: uuid}}, updateState);
        }
    }

    function enableStartEmulation(context){
        context.ui.startEmulationButton.html("Start Emulation");
        context.ui.startEmulationButton.click(function(e){
            asyncStartEmulation(context, updateUI)
        })
    }

    function enableAudioToggle(context){
        context.ui.toggleAudioButton.click(function(e){
            context.emu.setMuted(!context.emu.isMuted());
            context.ui.toggleAudioButton.html(context.emu.isMuted() ? "Audio Off" : "Audio On");
        });
    }

    function enableLoadLastState(context){
        context.ui.loadLastStateButton.click(function(e){
            initLoadState(context, context.lastState, updateState);
        });
    }

    function enableSaveState(context){
        context.ui.saveStateButton.click(function(){
            initSaveState(context, updateState);
        })
    }


    //SSF-----------SAVE STATE FUNCTIONS----------------

    function initSaveState(context, callback){
        context.emu.saveState(function(stateData){
            var record = {
                description: context.ui.stateDescription.val(),
                emulator: context.emu.emulator
            };

            if(!record.description)
                record.description = "State for " + context.currentGame.record.title + " at " + new Date(Date.now()).toUTCString();
            if(!context.currentGame.isSingleFile){
                record.emt_stack_pointer = stateData.emtStack;
                record.stack_pointer = stateData.stack;
                record.time = stateData.time;
            }
            //Ick... Should move this somewhere
            context.ui.stateDescription.val("");

            if(context.currentPerformance){
                record.performance_uuid = context.currentPerformance.record.uuid;
                if(context.emu.recording) record.performance_time_index = Date.now() - context.startedRecordingTime;
                //  Check to see if this is a state save terminal
                if(context.hasFinishedRecording){
                    record.performance_time_index = Date.now() - context.previousStartedRecordingTime;
                    context.hasFinishedRecording = false;
                }

                if(!record.description){
                    record.description += "State for performance: " + record.performance_uuid;
                    if(record.performance_time_index) record.description += " at time: " + record.performance_time_index;
                }
            }

            addStateRecordAJAX(context, {record: record},
                function(err, context, info){
                    if(context.currentGame.isSingleFile){
                        context.stateDataSaveQueue.push(createSaveStateDataTask(context,
                            info,
                            {buffer: stateData, compressed: false},
                            SINGULAR_STATE,
                            CiteState.canvasCaptureScreen(context.emu)
                        ), callback)
                    }else{
                        context.stateDataSaveQueue.push(createSaveStateDataTask(context,
                            info,
                            {
                                buffer: new Uint8Array(stateData.heap),
                                compressed: false,
                                emtStack: stateData.emtStack,
                                stack: stateData.stack,
                                time: stateData.time
                            },
                            DEPENDENT_STATE,
                            CiteState.canvasCaptureScreen(context.emu)
                        ), callback)
                    }
                });
        });
    }

    //State Save Task Factory Functions (just to make sure task object is consistent)
    function createSaveStateDataTask(context, gameInfo, stateData, stateType, screenData){
        //needed for capturing ui description, as the label could change after call
        //might add stateInfo as parameter if more complementary information is needed
        return {context: context, info: gameInfo, data: stateData, type: stateType, screen: screenData}
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
        var tasks;
        //Single save states do not need worker since low overhead
        if(task.type === SINGULAR_STATE){
            asyncSaveStateData(task.info, task.data, function(err, ti, td){
                if(err) console.log("Error with state save of " + task.info.record.uuid);
                asyncSaveStateScreenData(task.info, task.screen, function(err, iWithScreen){
                    asyncGetStateInfo(task.context, task.info, function(e, c, i){
                        callback(c, i, td);
                    });
                })
            });
        }else if(task.type === DEPENDENT_STATE){
            var saveStateWorker = new Worker("/static/js/save-state-worker.js");
            saveStateWorker.onmessage = function(e){
                var data = e.data;
                if(data.type === "stdout"){
                    console.log("[SAVE STATE W]: "+e.data.message);
                }else if(data.type === "error"){
                    console.log("[SAVE STATE W]: Error with "+data.uuid+" "+data.message);
                }else if(data.type === "finished"){
                    saveStateWorker.terminate();
                    if(callback){
                        asyncSaveStateScreenData(task.info, task.screen, function(err, iWithScreen){
                            asyncGetStateInfo(task.context, iWithScreen, function(e, c, i){
                                callback(c, i, data.data);
                            });
                        })
                    }
                }
            };

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

        }
    }

    //LSF------------LOAD STATE FUNCTIONS---------------

    function asyncLoadState(context, info, data, callback){
        // Decompress data if needed, otherwise just pass as is (decompress function will ignore uncompressed data)
        // Do not modify the data object directly, as it will get passed along to the cache
        // and we don't want uncompressed data in the cache since that might blow up the browser
        //TODO: Clean this up if runLength actually works
        function prepLoadState(err, c, i, d){
            var dataToLoad = {};
            if(context.currentGame.isSingleFile){
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

    function initLoadState(context, info, callback){
        //check cache
        if(info.record.uuid in context.statesCache && context.statesCache[info.record.uuid]){
            loadStateFromCache(context, context.statesCache[info.record.uuid], callback);
        } else {
            //init async if not found
            for(var i = 0; i < context.availableStates.length; i++){
                var state = context.availableStates[i];
                if(state.uuid === info.record.uuid){ //rely on var scoping to function
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
            if(!task.context.currentGame.isSingleFile){
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
    function loadStateForPageLoad(context, info, data, callback){

        function prepForStartEmulation(err, c, i, d){
            //Need new dataObject so that cache is correct
            var dataToLoad = {};
            if(!c.currentGame.isSingleFile){
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

    function enableStartRecordPerformance(context){
        context.ui.startRecordingButton.html("Start Recording");
        context.ui.startRecordingButton.click(function(e){
            startTiming('buttonPushInterval');
            var tasks = [];
            if(context.emu){
                //start recording, save new initial state for performance
                tasks.push(async.apply(asyncStartRecording, context));
                tasks.push(async.apply(initSaveState, context));
            }else{
                //start emulation and recording
                tasks.push(async.apply(asyncStartEmulationWithRecording, context));

                if(context.lastState){
                    //save init state as performance initial if present
                    tasks.push(
                        async.apply(asyncAddStateToPerformance, context, context.lastState.record)
                    );
                }
            }

            //Add record and update
            async.waterfall(
                [
                    async.apply(addPerformanceRecordAJAX, context),
                    updatePerformance
                ],
                // Run tasks based on conditionals above
                function (err, context){
                    async.series(tasks, function(err, results){
                        //Update everything after you're finished
                        async.waterfall([
                            async.apply(asyncGetPerformanceInfo, context, context.currentPerformance),
                            updatePerformance
                        ], function(err, context){
                            updateUI(context)
                        });
                    })
                }
            );
        })
    }

    function enableStopRecordPerformance(context){
        context.ui.stopRecordingButton.click(function(e){
            if(context.emu.recording){
                stopTiming('buttonPushInterval');
                var tasks = [
                    async.apply(asyncStopRecording, context),
                    function(context, data, callback){
                        context.performanceDataSaveQueue.push(createPerformanceSaveTask(
                            context,
                            context.currentPerformance,
                            data
                        ),updatePerformance);
                        callback(null, context);
                    }
                ];

                initSaveState(context, updateState);
                async.waterfall(tasks, function(err, context){
                    updateFullContext(context);
                })
            }
        })
    }

    function asyncStartRecording(context, callback){
        if(!context.emu.recording){
            var options = {};
            //Used to reduce transcoding time for DOS at the moment
            if(!context.currentGame.isSingleFile){
                options = {width: context.emu.canvas.width, height: context.emu.canvas.height, br: 300000};
            }
            context.emu.startRecording(function(){
                startTiming('asyncRecording');
                context.startedRecordingTime = Date.now();
                callback(null, context)
            }, options);
        }else{
            callback(new Error("Cannot start recording on context "+context.id+" it is already recording"), context)
        }
    }

    function asyncStopRecording(context, callback){
        if(context.emu.recording){
            context.emu.finishRecording(function(videoData){
                stopTiming('asyncRecording');
                context.previousStartedRecordingTime = context.startedRecordingTime;
                //  Needed to signal to saveState that it should look for the previous started time
                context.hasFinishedRecording = true;
                context.startedRecordingTime = 0;
                callback(null, context, {buffer: videoData, compressed: false})
            });
        }else{
            callback(new Error("Cannot stop recording on context "+context.id+" because it hasn't started"), context, {})
        }
    }

    function createPerformanceSaveTask(context, perfInfo, perfData){
        perfInfo.title = context.ui.performanceTitle.val();
        return {context: context, info: perfInfo, data: perfData, uuid: perfInfo.record.uuid}
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

                if(callback){
                    asyncGetPerformanceInfo(task.context, task.info, function(err, c, i){
                        callback(c, i)
                    });
                }
                saveWorker.terminate();
            }else if(data.type === "stdout"){
                console.log(data.data);
            }
        };

        saveWorker.postMessage({
            perfUUID: task.uuid,
            data: task.data
        });
    }

    function asyncAddStateToPerformance(context, stateInfo, callback){

    }

    //EMF---------EMULATION MANAGEMENT FUNCTIONS--------------

    function asyncStartEmulation(context, callback){
        CiteState.cite.apply(this, prepArgsForCiteState(context, callback, {mute:true, recorder: {}}))
    }

    function asyncStartEmulationWithRecording(context, callback){
        var options = {mute: false, recorder:{autoStart: true}};
        //TODO: change from isSingleFile to requiresSDL2, since there may be SDL2 applications that are single file
        if(!context.currentGame.isSingleFile){
            //Add callback to start recording once SDL context is loaded
            //if necessary
            triggerOnSDL2Available(context, function (context, timestamp){
                asyncStartRecording(context, callback);
            });
            options.recorder = {};
            //Initiate emulator setup without recording
            CiteState.cite.apply(this, prepArgsForCiteState(context, null, options))
        }else{
            startTiming('asyncRecording');
            CiteState.cite.apply(this, prepArgsForCiteState(context, callback, options))
        }
    }

    function prepArgsForCiteState(context, cb, options){
        var args = [
            context.ui.emulationContainer.attr('id'),
            function(emu){
                context.emu = emu;
                enableAudioToggle(context);
                if(cb)
                    cb(context);
            },
            context.currentGame.fileURL,
            null, //blank unless saveStateURL, used for NES / SNES and other systems with small save states
            null, //blank unless compressedSaveStateData, used for DOS and other large save states
            null  //blank unless dependent files
            //options are next argument if needed
        ];
        var single = context.currentGame.isSingleFile;
        if(context.lastState){
            if(single){
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

    function initPageLoad(context){
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
                        loadStateForPageLoad
                    ];
                }
                // after all that, wire up the UI
                async.waterfall(tasks, function(err, c){
                    if(err) console.log("Error preloading state for page.");
                    enableStartEmulation(context);
                    enableStartRecordPerformance(context);
                    enableStopRecordPerformance(context);
                    enableLoadLastState(context);
                    enableSaveState(context);
                })
            });
    }

    return {
        contextFactory: contextFactory,
        initPageLoad: initPageLoad,
        createUIForContext: createUIForContext
    }

}({}));

    //Load initial page information into model
    var stateUUID = $('body').data('state-uuid');
    var gameUUID = $('body').data('game-uuid');
    var context0 = CiteManager.contextFactory.getNewContext();
    CiteState.scriptRoot = '/static/js/cite-game/';

    CiteManager.createUIForContext(context0);
    CiteManager.initPageLoad(context0);
});

