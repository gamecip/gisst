/**
 * Created by erickaltman on 2/29/16.
 */



$(function() {
    //API Call URLs

    //JSON Information
    function jsonGameInfoURL(uuid){ return "/json/game_info/" + uuid; }
    function jsonStateInfoURL(uuid){ return "/json/state_info/" + uuid; }

    //Record Creation
    function addStateRecordURL(gameUUID){ return "/state/" + gameUUID + '/add' }
    function addStateDataURL(stateUUID){ return "/state/" + stateUUID + '/add_data' }
    function addExtraFileRecordURL(stateUUID){ return "/extra_file/" + stateUUID + '/add'}
    function addPerformanceRecordURL(gameUUID){ return "/performance/" + gameUUID +'/add'}
    function updatePerformanceRecordURL(perfUUID){ return "/performance/" + perfUUID +'/update'}


    //Setup simple page model
    var PlayContext = {
        gameLoaded: false,
        emu: "",
        currentStateData: "",
        currentStateDescription: "",
        currentFileMapping: "",
        currentFileInformation: "",
        currentStates: "",
        gameFilePath: "",
        stateFilePath: "",
        game:"",
        state:"",
        performance:""
    };

    function updateGame(gameUpdateObj){
        PlayContext.game = gameUpdateObj['gameRecord'];
        PlayContext.gameFilePath = gameUpdateObj['gameFile'];
        PlayContext.currentStates = gameUpdateObj['saveStates'];
        if(gameUpdateObj['extraFiles'] &&
            (!PlayContext.currentFileMapping || !PlayContext.currentFileInformation)){
            PlayContext.currentFileMapping = gameUpdateObj['extraFiles'];
            PlayContext.currentFileInformation = gameUpdateObj['extraFileInfo'];
        }
        //Needed on initialization
        if(!PlayContext.gameLoaded) PlayContext.gameLoaded = true;
        updateGameUI();
    }

    function updateState(stateUpdateObj){
        PlayContext.state = stateUpdateObj['stateRecord'];
        PlayContext.currentStates = stateUpdateObj['saveStates'];
        PlayContext.stateFilePath = '/cite_data/'+ PlayContext.state['save_state_source_data'] + '/' + PlayContext.state['uuid'];
        PlayContext.currentFileMapping = stateUpdateObj['extraFiles'];
        PlayContext.currentFileInformation = stateUpdateObj['extraFileInfo'];
        updateStateUI();
    }
    function updatePerformance(performanceUpdateObj){
        PlayContext.performance = performanceUpdateObj;
        updatePerformanceUI();
    }

    //Initialize UI objects and containers
    var $saveButton = $('#saveStateButton');
    var $startEmulationButton = $('#startEmulationButton');
    var $loadLastButton = $('#loadLastStateButton');
    var $resetButton = $('#resetButton');
    var $toggleAudioButton = $('#toggleAudioButton');
    var $stateDescription = $('#stateDescriptionTextBox');
    var $saveStateListing = $('#saveStateListingContainer');
    var $fileListing = $('#fileListingContainer');
    var $mostRecentState = $('#mostRecentStateContainer');
    var $performanceInfo = $('#performanceContainer');

    //Load initial page information into model
    var stateUUID = $('body').data('state-uuid');
    var gameUUID = $('body').data('game-uuid');

    $.getJSON(jsonGameInfoURL(gameUUID), '', function(gameInfo){
        updateGame(gameInfo);
    });

    if(stateUUID){
        $.getJSON(jsonStateInfoURL(stateUUID),'', function(stateInfo){
            updateState(stateInfo);
        })
    }

    //Initialize current performance
    $.getJSON(addPerformanceRecordURL(gameUUID),'',function(performanceInfo){
        updatePerformance(performanceInfo)
    });

    //Wire up UI

    $saveButton.click(function(e){
        if(PlayContext.currentFileMapping){
            PlayContext.emu.saveState(manageSaveWithExtraFiles);
        }else{
            PlayContext.emu.saveState(manageSingleSave);
        }
    });

    $loadLastButton.click(function(e){
        PlayContext.emu.loadState(PlayContext.currentStateData, manageLoadState);
    });

    $resetButton.click(function(e){

    });

    $toggleAudioButton.click(function(e){
        PlayContext.emu.setMuted(!PlayContext.emu.isMuted());
        $toggleAudioButton.html(PlayContext.emu.isMuted() ? "Audio Off" : "Audio On")
    });

    $stateDescription.change(function(e){
        PlayContext.currentStateDescription = $stateDescription.val();
    });

    $startEmulationButton.click(function(e){
        if(PlayContext.gameLoaded){
            loadEmulation();
        }
    });


    //UI management
    function updateGameUI(){
        if(PlayContext.currentFileInformation)
            updateFileListing(PlayContext.currentFileInformation);
        updateCurrentState(PlayContext.state);
        updateSaveStateListing(PlayContext.currentStates);
    }

    function updateStateUI(){
        updateCurrentState(PlayContext.state);
        updateSaveStateListing(PlayContext.currentStates);
        updateGameUI();
    }

    function updatePerformanceUI(){
        updateCurrentPerformanceInfo(PlayContext.performance);
    }

    function updateCurrentPerformanceInfo(perf_info){

    }

    function updateSaveStateListing(saveStates){
        $saveStateListing.empty();
        $saveStateListing.append('<h3>Save States Available</h3>')
        $stateList = $("<ul/>");
        for(var i=0; i < saveStates.length; i++){
            var state = saveStates[i];
            $('<li/>', {
                "class": "loadableState",
                text: state['description']
            }).attr('data-state-uuid', state['uuid'])
                .attr('data-state-source', state['save_state_source_data'])
                .appendTo($stateList);
        }
        $saveStateListing.append($stateList);
        $('.loadableState').click(loadableStateClick)
    }

    function loadableStateClick(e){
        var uuid = $(this).data('state-uuid');
        var source = $(this).data('state-source');
        initLoadState(source, uuid);
    }

    function updateFileListing(fileInformation){
        $fileListing.empty();
        $fileListing.append('<h3>Current Active Files</h3>');
        $fileList = $('<ul/>');
        for(var filePath in fileInformation){
            $fileList.append("<li>"+filePath+"</li>")
        }
        $fileListing.append($fileList);
    }

    function updateCurrentState(stateInfo){
        $mostRecentState.empty();
        $mostRecentState.append('<h3>Most Recent Save State</h3>')
        $('<div/>', {
            id: 'mostRecentStateDiv',
            "class": 'loadableState',
            text: stateInfo['description']
        }).attr('data-state-uuid', stateInfo['uuid'])
            .attr('data-state-source', stateInfo['save_state_source_data'])
            .appendTo($mostRecentState);
        $('#mostRecentStateDiv').click(loadableStateClick)
    }


    //Emulation management
    function citeLoadCallback(emu) {
        PlayContext.emu = emu;
    }

    function initLoadState(sourceData, stateUUID){
        var xhr = new XMLHttpRequest();
        var path = '/cite_data/' + sourceData + '/' + stateUUID;
        xhr.open('GET', path, true);
        xhr.responseType = 'arraybuffer';
        xhr.onload = function (e) {
            var responseData = new Uint8Array(this.response);
            PlayContext.currentStateData = responseData;
            $.getJSON(jsonStateInfoURL(stateUUID),"", completeLoadState)
        };
        xhr.send();
    }

    function completeLoadState(stateInfo){
        updateState(stateInfo);
        var stateRecord = stateInfo['stateRecord'];
        if (stateRecord['emt_stack_pointer']){
            var stateLoadObject = {
                emtStack: stateRecord['emt_stack_pointer'],
                stack: stateRecord['stack_pointer'],
                heap: PlayContext.currentStateData.buffer,
                time: stateRecord['system_time']
            };
            PlayContext.emu.loadState(stateLoadObject, manageLoadState);
        }else{
            PlayContext.emu.loadState(PlayContext.currentStateData, manageLoadState);
        }

    }

    function manageLoadState(stateData){
        //Nothing here yet, but needs callback
    }


    function loadEmulation() {
        var gameFile = PlayContext.gameFilePath;
        var freezeFile = PlayContext.stateFilePath;
        var extraFiles = PlayContext.currentFileMapping;

        var args = ["emulator", citeLoadCallback, gameFile, "", ""];

        if (freezeFile) args[3] = freezeFile;
        if (extraFiles) args[4] = extraFiles;

        CiteState.cite.apply(this, args);
    }

    // Nested callback here, should use promises or some such thing I guess
    function manageSaveWithExtraFiles(stateData){
        var stateUpdate = {};
        stateUpdate.extraFileInfo = {};
        var dataObject = {
            description: PlayContext.currentStateDescription,
            emulator: PlayContext.emu.emulator,
            emt_stack_pointer: stateData.emtStack,
            stack_pointer: stateData.stack,
            system_time: stateData.time
        };

        //Add State Record to Database
        $.post(addStateRecordURL(PlayContext.game.uuid),
            dataObject,
            function(stateRecordData){
                // Add State File Data to State Record
                var xhr = new XMLHttpRequest();
                xhr.open("PUT", addStateDataURL(stateRecordData['uuid']), true);
                xhr.onload = function(e){
                    //After that add all files to the State Record
                    PlayContext.emu.saveExtraFiles(PlayContext.emu.listExtraFiles(), function(fileMapping){
                        var fileCount = Object.keys(fileMapping).length;
                        PlayContext.currentStates.push(stateRecordData);
                        stateUpdate.extraFiles = fileMapping;

                        function filePathPost(filePath, fileObject){
                            return function(){
                                $.post(addExtraFileRecordURL(stateRecordData['uuid']),
                                    fileObject,
                                    function(data){
                                        stateUpdate.extraFileInfo[filePath] = data;
                                        fileCount--;
                                        if(fileCount === 0){
                                            $.getJSON(jsonStateInfoURL(stateRecordData['uuid']), "", updateState)
                                        }
                                    }
                                )
                            }
                        }

                        for(var file in fileMapping){
                            var cleanFilePath;
                            if(file.match(/^\//)){ //if there is a leading slash remove it
                                cleanFilePath = file.slice(1)
                            }
                            var fileObj = {
                                extra_file_data: StringView.bytesToBase64(fileMapping[file]),
                                sha1_hash: SHA1Generator.calcSHA1FromByte(fileMapping[file]),
                                data_length: fileMapping[file].length,
                                rel_file_path: cleanFilePath,
                                is_executable: PlayContext.currentFileInformation[cleanFilePath].isExecutable,
                                main_executable: PlayContext.currentFileInformation[cleanFilePath].mainExecutable
                            };
                            filePathPost(cleanFilePath, fileObj)();
                        }
                    });
                };
                xhr.send(stateData.heap);
            },
            'json'
        );
    }

    function manageSingleSave(stateData){
        var b64String = StringView.bytesToBase64(stateData);
        var dataObject = {
            save_state_data: b64String,
            description: PlayContext.currentStateDescription,
            emulator: PlayContext.emu.emulator,
            data_length: stateData.length
        };

        $.post(addStateRecordURL(PlayContext.game.uuid),
            dataObject,
            function(data){
                PlayContext.currentStateData = stateData;
                $.getJSON(jsonStateInfoURL(data['uuid']), "", updateState)
            },
            'json'
        )
    }

    function manageSaveExtraFiles(fileMapping) {
        for (var file_path in fileMapping) {
            $.post('/save_extra_file/' + PlayContext.state['uuid'] + '/add')
        }
    }

    function resetEmulation(event) {

    }

    function listFilePaths(emu) {
        var paths = [];
        for (var fileName in emu.extraFiles) {
            paths.push(fileName);
        }
        return paths;
    }

});