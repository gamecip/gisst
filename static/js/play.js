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
    function addPerformanceRecordURL(gameUUID){ return "/performance/" + gameUUID +'/add'}
    function updatePerformanceRecordURL(perfUUID){ return "/performance/" + perfUUID +'/update'}

    //Simple context factory
    var contextFactory = (function(){
        var counter = 0;
        var contextHash = {};
        function increaseCount(){
            counter += 1;
        }
        function registerContext(id, context){
            contextHash.id = context;
        }
        return {
            getNewContext: function(){
                var nc = {
                    id: counter,
                    emu: "",
                    lastState: {},
                    availableStates: [],
                    statesCache: [],
                    currentGame: {},
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
                        recordingButton: "",
                        fileInformation: ""
                    },
                    stateSaveQueue: async.queue(processStateSave, 2),
                    performanceSaveQueue: async.queue(processPerformanceSave, 2)
                };
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
        context.ui.emulationContainer.css({ "height": "480px", width: "640px"});

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
        context.ui.mostRecentState = createElementForContext(context, "div", "mostRecentState", "<h4>Most Recent State</h4>", context.ui.stateInfo);
        context.ui.stateListing = createElementForContext(context, "div", "stateListing", "<h4>Saved States</h4>", context.ui.stateInfo);

        //Performance Information
        context.ui.performanceInfo = createElementForContext(context, "div", "performanceInfo", "<h3>Performance Information</h3>", $contextRoot);

        //Performance Controls
        $performanceControls = createElementForContext(context, "div", "performanceControls", "", $contextRoot);
        context.ui.recordingButton = createElementForContext(context, "button", "recordingButton", "Start Recording", $performanceControls);

        //File System Listing
        context.ui.fileInformation = createElementForContext(context, "div", "fileInformation", "<h3>File Information</h3>", $contextRoot);

        //Attach UI to Page
        $('body').append($contextRoot);
    }

    function createElementForContext(context, elementType, elementName, elementHtml, parentNode){
        return $("<"+elementType+"/>", {id: context.id +"_"+elementName, html: elementHtml}).appendTo(parentNode);
    }

    function updateGameUI(context){
        if(!$.isEmptyObject(context.currentGame.fileInformation))
            updateFileListing(context);
        if(!$.isEmptyObject(context.lastState))
            updateCurrentState(context);
        updateSaveStateListing(context);
    }

    function updateStateUI(context){
        updateCurrentState(context);
        updateSaveStateListing(context);
        updateFileListing(context)
    }

    function updatePerformanceUI(context){
        updateCurrentPerformanceInfo(context);
    }

    function updateCurrentPerformanceInfo(context){

    }

    function updateSaveStateListing(context){
        context.ui.stateListing.empty();
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

    function createLoadableClickHandler(context){
        return function(event){
            var uuid = $(this).data('state-uuid');
            initLoadState(context, uuid);
        }
    }

    function updateFileListing(context){
        var fi;
        if("fileInformation" in context.currentGame){
            if(!$.isEmptyObject(context.lastState)){
                fi = context.lastState.fileInformation;
            }else{
                fi = context.currentGame.fileInformation;
            }
        }else{
            fi = {};
        }
        context.ui.fileInformation.empty();
        if(!$.isEmptyObject(fi)){
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
        context.ui.mostRecentState.append('<h3>Most Recent Save State</h3>');
        $('<div/>', {
            id: context.id + '_mostRecentStateDiv',
            text: context.lastState.record.description
        }).attr('data-state-uuid', context.lastState.record.uuid)
            .appendTo(context.ui.mostRecentState);
        $('#' + context.id + '_mostRecentStateDiv').click(createLoadableClickHandler(context))
    }


    //002 Async Function Management


    function preLoadStateFromServer(context, task, callback){
        async.waterfall([
            async.apply(asyncGetStateInfo, context, task.info, task.data),
            asyncLoadStateArray,
            decompressStateByteArray
        ], callback);
    }

    function loadStateFromServer(task, callback){
        preLoadStateFromServer(task.context, task, function(err, context, info, data){
            var dataObj = {};
            if("emt_stack_pointer" in info.record && info.record['emt_stack_pointer']){
                dataObj.emtStack = info.record.emt_stack_pointer;
                dataObj.stack = info.record.stack_pointer;
                dataObj.heap = data.buffer;
                dataObj.time = info.record.system_time;
            } else {
                dataObj = data.buffer;
            }
            context.emu.loadState(dataObj, function(stateData){ //unused since redundant data
                callback(err, context, info, data);
            });
        })
    }

    function asyncLoadStateArray(context, info, data, callback){
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
            var args = [
                context.ui.emulationContainer.attr('id'),
                function(emu){
                    context.emu = emu;
                    enableAudioToggle(context);
                },
                context.currentGame.fileURL,
                "", //blank unless saveState
                ""  //blank unless dependent files
            ];
            if(!$.isEmptyObject(context.lastState)){
                args[4] = context.lastState.data.buffer;
                if(!$.isEmptyObject(context.lastState.fileMapping)){
                    args[5] = context.lastState.fileMapping;
                }
            }else if(!$.isEmptyObject(context.currentGame.fileMapping)){
                args[5] = context.currentGame.fileMapping;
            }
            CiteState.cite.apply(this, args);
        })
    }

    function enableAudioToggle(context){
        context.ui.toggleAudioButton.click(function(e){
            context.emu.setMuted(!emu.isMuted());
            context.ui.toggleAudioButton.html(context.emu.isMuted() ? "Audio Off" : "Audio On");
        });
    }

    function enableSaveState(context){
        context.ui.saveStateButton.click(function(e){
            context.emu.saveState(function(stateData){
                if(context.currentGame.isSingleFile){
                    context.stateSaveQueue.push(createStateSaveTask(context,
                        context.currentGame,
                        {buffer: stateData, compressed: false},
                        SINGULAR_STATE,
                        context.ui.stateDescription.val()
                    ), updateState)
                }else{
                    context.stateSaveQueue.push(createStateSaveTask(context,
                        context.currentGame,
                        {
                            buffer: new Uint8Array(stateData.heap),
                            compressed: false,
                            emtStack: stateData.emtStack,
                            stack: stateData.stack,
                            time: stateData.time
                        },
                        DEPENDENT_STATE,
                        context.ui.stateDescription.val()
                    ), updateState)
                }
            });
        });
    }

    function enableLoadLastState(context){
        context.ui.loadLastStateButton.click(function(e){
            initLoadState(context, context.lastState.record.uuid);
        });
    }

    function initLoadState(context, stateUUID){
        //check cache
        for(var i = 0; i < context.statesCache; i++){
            if(statesCache[i].info.record.uuid === stateUUID){
                loadStateFromCache(context, statesCache[i]);
                return;
            }
        }
        //init async if not found
        for(var i = 0; i < context.availableStates.length; i++){
            var state = context.availableStates[i];
            if(state.uuid === stateUUID){ //rely on var scoping to function
                break;
            }
        }

        loadStateFromServer(createStateLoadTask(context, {record: state}), function(err, context, info, data){
            updateState(context, info, data);
        });
    }

    function loadStateFromCache(context, cache){
        var dataObj = {};
        //TODO: change this check to use context.currentGame.isSingleFile flag
        if("emt_stack_pointer" in cache.info.record && cache.info.record['emt_stack_pointer']){
            dataObj.emtStack = cache.info.record.emt_stack_pointer;
            dataObj.stack = cache.info.record.stack_pointer;
            dataObj.heap = cache.data.buffer;
            dataObj.time = cache.info.record.system_time;
        } else {
            dataObj = cache.data.buffer;
        }

        if(cache.data.compressed){
            decompressStateByteArray(context, cache.info, cache.data, function(err, context, info, data){
                if("emtStack" in dataObj) {
                    dataObj.heap = data.buffer;
                } else {
                    dataObj = data.buffer
                }
                context.emu.loadState(dataObj, function(d){ updateState(context, cache.info, cache.data); });
            })
        }else{
            context.emu.loadState(dataObj, function(d){ updateState(context, cache.info, cache.data)});
        }
    }

    //State Save Task Factory Functions (just to make sure task object is consistent)
    function createStateSaveTask(context, gameInfo, stateData, stateType, stateDescription){
        //needed for capturing ui description, might add stateInfo as parameter if more complementary information is needed
        gameInfo.stateDescription = stateDescription;
        return {context: context, info: gameInfo, data: stateData, type: stateType}
    }

    //State Load Task, Identical to above for now
    function createStateLoadTask(context, stateInfo, stateData, stateType){
        return {context: context, info: stateInfo, data: stateData, type: stateType}
    }

    //Manage the compression and uploading of save state data
    function processStateSave(task, callback){
        var tasks;
        if(task.type === SINGULAR_STATE){
            tasks = [
                async.apply(addStateRecordAJAX, task.context, task.info, task.data),
                asyncGetStateInfo
            ];
        }else if(task.type === DEPENDENT_STATE){
            tasks = [
                async.apply(compressStateByteArray, task.context, task.info, task.data),
                addStateRecordAJAX,
                asyncSaveExtraFiles,
                asyncFileSaveTasks,
                asyncGetStateInfo
            ];
        }
        async.waterfall(tasks,
            function(err, context, info, data){
                if(err) console.log("Error with state save of " + task.info.uuid);
                callback(context, info, data);
            })
    }

    function processPerformanceSave(task, callback){}


    //Wraps saveExtraFiles to capture async err, and pass arguments forward in the chain
    function asyncSaveExtraFiles(context, info, data, callback){
        context.emu.saveExtraFiles(context.emu.listExtraFiles(),
            function(fm) {
                info.fileMapping = fm;
                callback(null, context, info, data)})
    }

    function asyncFileSaveTasks(context, info, data, callback){
        var tasks = [];
        var fileInformation = !$.isEmptyObject(context.lastState) ? context.lastState.fileInformation : context.currentGame.fileInformation;
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
                console.log('Compressing state data from '+ info.record.title + " " + percent + "% complete");
            }
        )
    }

    function decompressStateByteArray(context, info, data, callback){
        var lzma = new LZMA(LZMA_WORKER_PATH);
        if(data.compressed){
            lzma.decompress(data.buffer,
            function on_finish(result, err){
                if (err) console.log("Error with decompression of state data for " + info.uuid);
                data.buffer = result;
                data.data_length = result.length;
                data.compressed = false;
                lzma.worker().terminate(); //needed since lzma.js does not check for existing worker, and it is not garbage collected
                callback(err, context, info, data)
            },
            function on_progress(percent){
                //TODO: progress update for state load
            })
        }else{
            callback(null, context, info, data)
        }
    }

    function addStateRecordAJAX(context, gameInfo, data, callback){
        var dataObject = {
            save_state_data: StringView.bytesToBase64(data.buffer),
            description: gameInfo.stateDescription,
            emulator: context.emu.emulator,
            data_length: data.buffer.length,
            compressed: data.compressed
        };
        //Check for additional info for DOSBox States
        if("emtStack" in data) dataObject.emt_stack_pointer = data.emtStack;
        if("stack" in data) dataObject.stack_pointer = data.stack;
        if("time" in data) dataObject.system_time = data.time;
        //Need to wrap callback function to pass null for err and ignore all but returned JSON data
        $.post(addStateRecordURL(gameInfo.record.uuid),
            dataObject,
            function(sInfo){ callback(null, context, sInfo, data)});
    }

    function asyncGetStateInfo(context, stateInfo, stateData, callback){
        $.get(jsonStateInfoURL(stateInfo.record.uuid), "", function(info){ callback(null, context, info, stateData)})
    }

    function asyncGetGameInfo(context, gameInfo, callback){
        $.get(jsonGameInfoURL(gameInfo.record.uuid), "", function(info){ callback(null, context, info)} )
    }

    function updateState(context, info, data){
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
        context.currentGame.record = info.record;
        context.currentGame.isSingleFile = $.isEmptyObject(info.fileMapping);
        context.currentGame.fileURL = info.gameFileURL;
        if(!$.isEmptyObject(info.fileMapping)) context.currentGame.fileMapping = info.fileMapping;
        if(!$.isEmptyObject(info.fileInformation)) context.currentGame.fileInformation = info.fileInformation;
        context.availableStates = info.availableStates;
        updateGameUI(context);
    }

    function updatePerformance(context, info){
        context.performance.record = info.record;
        context.performance.linkedStates = info.linkedStates;
        updatePerformanceUI(context);
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
            enableAudioToggle(context);
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