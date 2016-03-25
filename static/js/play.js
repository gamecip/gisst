/**
 * Created by erickaltman on 2/29/16.
 */



$(function() {

    //000-----------EMULATION CONTEXT MANAGEMENT---------

    //Consts
    var SINGULAR_STATE = "singleState";
    var DEPENDENT_STATE = "dependentState";
    var LZMA_WORKER_PATH = "/static/js/lzma_worker.js";
    var STATE_CACHE_LIMIT = 10;

    // API Call URLs

    //JSON Information
    function jsonGameInfoURL(uuid){ return "/json/game_info/" + uuid; }
    function jsonStateInfoURL(uuid){ return "/json/state_info/" + uuid; }
    function jsonPerformanceInfoURL(uuid){ return "/json/performance_info" + uuid; }

    //Record Creation
    function addStateRecordURL(gameUUID){ return "/state/" + gameUUID + '/add' }
    function addStateDataURL(stateUUID){ return "/state/" + stateUUID + '/add_data' }
    function addExtraFileRecordURL(stateUUID){ return "/extra_file/" + stateUUID + '/add'}
    function addPerformanceRecordURL(gameUUID){ return "/performance/" + gameUUID + '/add'}
    function updatePerformanceRecordURL(perfUUID){ return "/performance/" + perfUUID + '/update'}
    function addPerformanceVideoURL(perfUUID){ return "/performance" + perfUUID + '/add_video_data'}

    //Simple context factory
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
                    statesCache: [],
                    currentGame: "",
                    currentPerformance: "",
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
                    stateDataSaveQueue: async.queue(processStateDataSave, 2),
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

    //001 UI Creation and Management
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
        context.ui.emulationContainer.css({ "height": "480px", width: "512px"});

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
        context.ui.performanceTitle = createElementForContext(context, "input", "peformanceTitleInput", "", $performanceTitleDiv);
        $performanceDescriptionDiv = createElementForContext(context, "div", "performanceTitleDiv", "Description: ", context.ui.performanceInfo);
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

    function updateUI(err, context, cb){
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
        callback(null, context);
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

    function createLoadableClickHandler(context){
        return function(event){
            var uuid = $(this).data('state-uuid');
            initLoadState(context, {record:{uuid: uuid}}, updateState);
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


    //002 Async Function Management


    function preLoadStateFromServer(task, callback){
        async.waterfall([
            async.apply(asyncGetStateInfo, task.context, task.info),
            asyncLoadStateArray
        ], callback);
    }

    function loadStateFromServer(task, callback){
        preLoadStateFromServer(task, function(err, context, info, data){
            if(!task.context.currentGame.isSingleFile){
                data.emtStack = info.record.emt_stack_pointer;
                data.stack = info.record.stack_pointer;
                data.time = info.record.time;
            }
            asyncLoadState(context, info, data, callback);
        })
    }

    function asyncLoadStateArray(context, info, callback){
        var xhr = new XMLHttpRequest();
        xhr.open('GET', info.stateFileURL, true);
        xhr.responseType = 'arraybuffer';
        xhr.onload = function (e){
            callback(null, context, info, {buffer: new Uint8Array(this.response), compressed: info.record.compressed})
        };
        xhr.send()
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

    function enableSaveState(context){
        context.ui.saveStateButton.click(function(){
            initSaveState(context, updateState);
        })
    }

    function asyncAddStateToPerformance(context, stateInfo, callback){

    }

    function initSaveState(context, callback){
        context.emu.saveState(function(stateData){
            var record = {
                description: context.ui.stateDescription.val(),
                emulator: context.emu.emulator
            };

            if(context.currentPerformance){
                record.performance_uuid = context.currentPerformance.record.uuid;
                if(context.isRecording) record.performance_time_index = Date.now() - context.startedRecordingTime;
                //  Check to see if this is a state save terminal
                if(context.hasFinishedRecording){
                    record.performance_time_index = Date.now() - context.previousStartedRecordingTime;
                    context.hasFinishedRecording = false;
                }
            }
            addStateRecordAJAX(context, {record: record}, {},
                function(err, context, info){
                    if(context.currentGame.isSingleFile){
                        context.stateDataSaveQueue.push(createSaveStateDataTask(context,
                            info,
                            {buffer: stateData, compressed: false},
                            SINGULAR_STATE
                        ), callback)
                    }else{
                        context.stateDataSaveQueue.push(createSaveStateDataTask(context,
                            info,
                            {
                                buffer: new Uint8Array(stateData.heap),
                                compressed: false,
                                emt_stack_pointer: stateData.emtStack,
                                stack_pointer: stateData.stack,
                                time: stateData.time
                            },
                            DEPENDENT_STATE
                        ), callback)
                    }
                });
        });
    }

    function enableLoadLastState(context){
        context.ui.loadLastStateButton.click(function(e){
            initLoadState(context, context.lastState, updateState);
        });
    }

    function enableStartRecordPerformance(context){
        context.ui.startRecordingButton.html("Start Recording");
        context.ui.startRecordingButton.click(function(e){
            var tasks = [
                async.apply(addPerformanceRecordAJAX, context),
                updatePerformance
            ];
            if(context.emu){
                //start recording, save new initial state for performance
                tasks.push(asyncStartRecording);
                tasks.push(initSaveState);
            }else{
                //start emulation and recording
                tasks.push(asyncStartEmulationWithRecording);

                if(context.lastState){
                    //save init state as performance initial if present
                    tasks.push(
                        async.compose(
                            async.apply(asyncAddStateToPerformance, context, context.lastState.record),
                            updatePerformance
                        )
                    )
                }
            }
            async.series(tasks, function(err, results){
                updateUI(context)
            })
        })
    }

    function enableStopRecordPerformance(context){
        context.ui.stopRecordingButton.click(function(e){
            if(context.isRecording){
                var tasks = [
                    async.apply(asyncStopRecording, context),
                    function(err, context, data, callback){
                        context.performanceDataSaveQueue.push(createPerformanceSaveTask(
                            context,
                            context.currentPerformance,
                            data
                        ),updatePerformance);
                        callback(null, context);
                    }
                ];
                async.waterfall(tasks, function(err, context){
                    initSaveState(context, updateState);
                    updateFullContext(context);
                })
            }
        })
    }

    function asyncStartEmulation(context, callback){
        CiteState.cite.apply(this, prepArgsForCiteState(context, callback, {mute:true}))
    }

    function asyncStartEmulationWithRecording(context, callback){
        CiteState.cite.apply(this.prepArgsForCiteState(context, callback, {mute:false, recorder: {autoStart: true}}))
    }

    function prepArgsForCiteState(context, cb, options){
        var args = [
            context.ui.emulationContainer.attr('id'),
            function(emu){
                context.emu = emu;
                enableAudioToggle(context);
                cb(null, context)
            },
            context.currentGame.fileURL,
            null, //blank unless saveState
            null  //blank unless dependent files
            //options are next argument if needed
        ];
        if(context.lastState){
            args[3] = context.lastState.data.buffer;
            if(!$.isEmptyObject(context.lastState.fileMapping)){
                args[4] = context.lastState.fileMapping;
            }
        }else if(!$.isEmptyObject(context.currentGame.fileMapping)){
            args[4] = context.currentGame.fileMapping;
        }
        if(options){
            args.push(options)
        }
        return args;
    }

    function asyncStartRecording(context, callback){
        if(!context.isRecording){
            context.emu.startRecording(function(){
                context.isRecording = true;
                context.startedRecordingTime = Date.now();
                callback(null, context)
            })
        }else{
            callback(new Error("Cannot start recording on context "+context.id+" it is already recording"), context)
        }
    }

    function asyncStopRecording(context, callback){
        if(!context.isRecording){
            context.emu.finishRecording(function(videoData){
                context.isRecording = false;
                context.previousStartedRecordingTime = context.startedRecordingTime;
                //  Needed to signal to saveState that it should look for the previous started time
                context.hasFinishedRecording = true;
                context.startedRecordingTime = 0;
                callback(null, context, {buffer: videoData, compressed: false})
            })
        }else{
            callback(new Error("Cannot stop recording on context "+context.id+" because it hasn't started"), context, {})
        }
    }

    function asyncLoadState(context, info, data, callback){
        // Decompress data if needed, otherwise just pass as is (decompress function will ignore uncompressed data)
        // Do not modify the data object directly, as it will get passed along to the cache
        // and we don't want uncompressed data in the cache since that might blow up the browser
        decompressStateByteArray(context, info, data, function(err, c, i, d){
            var dataToLoad = {};
            if(context.currentGame.isSingleFile){
                dataToLoad = d.buffer;
            } else{
                dataToLoad.heap = d.buffer;
                dataToLoad.time = d.time;
                dataToLoad.emtStack = d.emtStack;
                dataToLoad.stack = d.stack;
            }
            //pass dataToLoad with uncompressed buffer to loadState, but pass original data object down the line
            context.emu.loadState(dataToLoad, function(){
                callback(context, info, data)
            })
        })
    }

    function initLoadState(context, info, callback){
        //check cache
        for(var i = 0; i < context.statesCache.length; i++){
            if(context.statesCache[i].info.record.uuid === info.record.uuid){
                loadStateFromCache(context, context.statesCache[i], callback);
                return;
            }
        }
        //init async if not found
        for(var i = 0; i < context.availableStates.length; i++){
            var state = context.availableStates[i];
            if(state.uuid === info.record.uuid){ //rely on var scoping to function
                break;
            }
        }
        loadStateFromServer(createStateLoadTask(context, {record: state}), callback);
    }

    function loadStateFromCache(context, cache, callback){
            asyncLoadState(context, cache.info, cache.data, callback);
    }

    //State Save Task Factory Functions (just to make sure task object is consistent)
    function createSaveStateDataTask(context, gameInfo, stateData, stateType){
        //needed for capturing ui description, as the label could change after call
        //might add stateInfo as parameter if more complementary information is needed
        return {context: context, info: gameInfo, data: stateData, type: stateType}
    }

    //State Load Task, Identical to above for now
    function createStateLoadTask(context, stateInfo, stateData, stateType){
        return {context: context, info: stateInfo, data: stateData, type: stateType}
    }

    function createPerformanceSaveTask(context, perfInfo, perfData){
        perfInfo.title = context.ui.performanceDescription.val();
        return {context: context, info: perfInfo, data: perfData}
    }

    //Manage the compression and uploading of save state data
    function processStateDataSave(task, callback){
        var tasks;
        if(task.type === SINGULAR_STATE){
            tasks = [
                async.apply(asyncSaveStateData,task.context, task.info, task.data)
            ];
        }else if(task.type === DEPENDENT_STATE){
            tasks = [
                async.apply(compressStateByteArray, task.context, task.info, task.data),
                asyncSaveStateData,
                asyncSaveExtraFiles,
                asyncFileSaveTasks
            ];
        }
        async.waterfall(tasks, function(err, context, info, data){
            if(err) console.log("Error with state save of " + task.info.record.uuid);
            asyncGetStateInfo(context, info, function(e, c, i){
                callback(c, i, data);
            });
        })
    }

    function processPerformanceDataSave(task, callback){
        asyncSaveVideoFile(task.context, task.data, function(err, results){
            asyncGetPerformanceInfo(context, task.info, callback);
        });
    }

    function asyncSaveStateData(context, info, data, callback){
        //Convert ByteArray to Base64 for transfer
        var tempArray = data.buffer;
        data.data_length = data.buffer.length;

        data.buffer = StringView.bytesToBase64(data.buffer);
        $.post(addStateDataURL(info.record.uuid), data, function(i){
            data.buffer = tempArray;
            callback(null, context, i, data)
        })
    }

    function asyncSaveVideoFile(context, data, callback){
        var tasks = [];
        var chunkIndex = 0;
        var blob = new Blob(data.buffer);
        var totalBytesSent = 0;
        var md5 = SHA1Generator.calcSHA1FromByte(data.buffer);
        var perfUUID = context.currentPerformance.record.uuid;
        var targetURL = addPerformanceVideoURL(perfUUID);

        while(totalBytesSent < blob.size){
            var chunkData = blob.slice(chunkIndex * chunkSize, (chunkIndex + 1) * chunkSize);
            tasks.push(createSaveFileChunkTask(targetURL, md5, chunkIndex, chunkData, blob.size));
            chunkIndex++;
        }
        //  Need to get the remaining data, which is less than chunk size
        tasks.push(createSaveFileChunkTask(targetURL, md5, chunkIndex, blob.slice(chunkIndex * chunkSize), blob.size));

        async.parallel(tasks, function(err, results){
            if (err) console.log("Error saving video file for performance: {}".format(perfUUID));
            callback(err, results)
        })
    }

    function createSaveFileChunkTask(targetURL, md5Hash, chunkId, chunkData, totalChunks){
        var data = FormData();
        data.append("total_chunks", totalChunks);
        data.append("chunk_id", chunkId);
        data.append("chunk_data", chunkData);
        data.append("md5_hash", md5Hash);
        return function(cb){
            var request = new XMLHttpRequest();
            request.open("POST", targetURL);
            request.onload(function(result){
                cb(null, result);
            });
            request.send(data);
        }
    }

    //Wraps saveExtraFiles to capture async err, and pass arguments forward in the chain
    function asyncSaveExtraFiles(context, info, data, callback){
        context.emu.saveExtraFiles(context.emu.listExtraFiles(),
            function(fm) {
                info.fileMapping = fm;
                callback(null, context, info, data)})
    }

    function asyncFileSaveTasks(context, info, data, callback){
        var tasks = [];
        var fileInformation = context.lastState ? context.lastState.fileInformation : context.currentGame.fileInformation;
        // Organize individual POSTs for files
        for(var file in info.fileMapping){
            var cleanFilePath;
            if(file.match(/^\//)) cleanFilePath = file.slice(1) //if there is a leading slash remove it
            var fileObj = {
                extra_file_data: StringView.bytesToBase64(info.fileMapping[file]),
                sha1_hash: SHA1Generator.calcSHA1FromByte(info.fileMapping[file]),
                data_length: info.fileMapping[file].length,
                rel_file_path: cleanFilePath,
                is_executable: fileInformation[cleanFilePath].isExecutable,
                main_executable: fileInformation[cleanFilePath].mainExecutable
            };
            tasks.push(createFilePathPostTask(fileObj, info.record.uuid))
        }

        //Run POSTs in parallel and aggregate results
        async.series(tasks, function(err, results){
            if (err) console.log("Error with async file saves for state " + info.record.uuid);
            for(var i = 0; i < results.length; i++){
                info.fileInformation = {};
                info.fileInformation[results[i].file_path] = results[i];
            }
            callback(err, context, info, data)
        });
    }

    function createFilePathPostTask(fileObject, uuid){
        return function(cb){
            $.post(addExtraFileRecordURL(uuid),
                fileObject,
                function(result){ cb(null, result) }
            )
        }
    }

    function compressStateByteArray(context, info, data, callback){
        var lzma = new LZMA(LZMA_WORKER_PATH);
        lzma.compress(data.buffer,
            1, //compression level, 1 is faster but bigger
            function on_finish(result, err){
                if (err) console.log("Error with compression of state data for " + info.uuid);
                data.buffer = result;
                data.data_length = result.length;
                data.compressed = true;
                lzma.worker().terminate(); //needed since lzma.js does not check for existing worker, and it is not garbage collected
                callback(err, context, info, data);
            },
            function on_progress(percent){
                console.log('Compressing state data from '+ info.record.description + " " + percent + "% complete");
            }
        )
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
                lzma.worker().terminate(); //needed since lzma.js does not check for existing worker, and it is not garbage collected
                //Return new data object
                callback(err, context, info, d)
            },
            function on_progress(percent){
                //TODO: progress update for state load
            })
        }else{
            //Nothing to decompress, so just ignore
            callback(null, context, info, data)
        }
    }

    function addStateRecordAJAX(context, stateInfo, data, callback){
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
        var title = context.ui.peformanceTitle.val() || "A peformance of " + context.currentGame.record.title;
        var description = context.ui.performanceDescription.val() || "";
        $.post(addPerformanceRecordURL(context.currentGame.record.uuid),
            {title: title, description: description},
            function(info){ callback(null, context, info)})
    }

    function asyncGetStateInfo(context, info, callback){
        $.get(jsonStateInfoURL(info.record.uuid), "", function(info){ callback(null, context, info)})
    }

    function asyncGetGameInfo(context, info, callback){
        $.get(jsonGameInfoURL(info.record.uuid), "", function(info){ callback(null, context, info)} )
    }

    function asyncGetPerformanceInfo(context, info, callback){
        $.get(jsonPerformanceInfoURL(info.record.uuid), "", function(info){ callback(null, context, info, data)})
    }

    function updateFullContext(context){
        var getAndUpdateState = async.compose(
            async.apply(asyncGetStateInfo, context, context.lastState.record),
            rightAsyncPartial(updateState, this, context.lastState.data)
        );
        var getAndUpdatePerformance = async.compose(
            async.apply(asyncGetPerformanceInfo, context, context.currentPerformance.record),
            updatePerformance
        );
        var getAndUpdateGame = async.compose(
            async.apply(asyncGetGameInfo, context, context.currentGame.record),
            updateGame
        );
        async.series([
            getAndUpdateGame,
            getAndUpdateState,
            getAndUpdatePerformance
        ], updateUI)
    }


    function updateState(context, info, data){
        if(!context.lastState) context.lastState = {};
        context.lastState.record = info.record;
        context.lastState.data = data;
        context.lastState.fileMapping = info.fileMapping || "";
        context.lastState.fileInformation = info.fileInformation || "";
        context.lastState.fileURL = info.stateFileURL;
        context.availableStates = info.availableStates;

        if(context.statesCache.length > STATE_CACHE_LIMIT){
            context.statesCache.pop();
        }
        context.statesCache.unshift({info: info, data: data});
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
        if(!context.performance) context.performance = {};
        context.performance.record = info.record;
        context.performance.linkedStates = info.linkedStates;
        updatePerformanceUI(context, callback);
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

    //003-----------PAGE SPECIFIC------------------------

    function initPageLoad(context){
        var loadTasks = [
            async.apply(asyncGetGameInfo, context, {record: {uuid: gameUUID}})
        ];

        if(stateUUID){
            loadTasks.push(async.apply(preLoadStateFromServer,
                context, createStateLoadTask(context, {record: {uuid: stateUUID}})))
        }

        async.series(loadTasks, function(err, results){
            if(err) console.log("Error loading game " + gameUUID);
            //result[0][0] == context, result[0][1] == gameInfo, result[1] == [context, stateInfo, stateData]
            updateGame(results[0][0], results[0][1]);
            if(stateUUID) updateState(results[1][0], results[1][1], results[1][2]);
            enableStartEmulation(context);
            enableStartRecordPerformance(context);
            enableStopRecordPerformance(context);
            enableLoadLastState(context);
            enableSaveState(context);
        })
    }

    //Load initial page information into model
    var stateUUID = $('body').data('state-uuid');
    var gameUUID = $('body').data('game-uuid');
    var context0 = contextFactory.getNewContext();
    CiteState.scriptRoot = '/static/js/cite-game/';

    createUIForContext(context0);
    initPageLoad(context0);
});