/**
 * Created by erickaltman on 2/29/16.
 */
$(function() {
    var saveButton = $('#saveState');
    var loadLastButton = $('#loadLastState');
    var resetButton = $('#reset');
    var toggleAudioButton = $('#toggleAudio');
    var stateDescription = $('#stateDescription');
    var stateTable = $('#saveStateTable');
    var lastSavedStateData;
    var lastSavedStateUUID;
    var initState = $('body').data('init-state');
    var gameUUID = $('body').data('game-uuid');

    var GAME_EMU_INFO_JSON_URL = "/json/emulation_info/game/";
    var STATE_EMU_INFO_JSON_URL = "/json/emulation_info/state/";

    function manageSaveState(stateData) {
        var b64String = StringView.bytesToBase64(stateData);
        var dataObject = {};
        dataObject['save_state_data'] = b64String;
        dataObject['description'] = stateDescription.val();
        dataObject['emulator'] = $('body').data('emulator');

        $.post('/save_state/' + gameUUID + '/add',
            dataObject,
            updateSaveStateTable
        );
        lastSavedStateData = stateData;
    }

    function updateSaveStateTable(data, textStatus, jqXHR) {
        var saveStatePath = "/cite_data/" + data['save_state_source_data'] +
            "/" + data['game_uuid'] + "_" + data['epoch_time'];

        var newStateRow = $('<tr>');
        stateTable.append(newStateRow);

        var headers = data['headers'];
        var $loadSpan = $('<span>', {class: 'loadableState'});
        $loadSpan.attr('data-path', saveStatePath);
        $loadSpan.html('load');
        $loadSpan.click(requestState);
        var $loadTD = $('<td>').append($loadSpan);
        newStateRow.append($loadTD);
        for (var i = 0; i < headers.length; i++) {
            $('<td>').html(data[headers[i]]).appendTo(newStateRow);
        }
        $('#mostRecentStateTable').empty();
        $('#mostRecentStateTable').append(newStateRow.clone());

        lastSavedStateUUID = data['uuid'];

    }

    function requestState(e) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', $(this).data('path'), true);
        xhr.responseType = 'arraybuffer';
        xhr.onload = function (e) {
            var responseData = new Uint8Array(this.response);
            emu.loadState(responseData, manageLoadState);
            lastSavedStateData = responseData;
        };
        xhr.send();
    }

    function manageLoadState(stateData) {

    }

    function manageSaveExtraFiles(fileMapping) {
        for (var file_path in fileMapping) {
            $.post('/save_extra_file/' + lastSavedStateUUID + '/add')
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

    function citeLoadCallback(emu) {
        window.emu = emu;
        var body = $('body');
        body.data('emulator', emu.emulator);
        saveButton.click(function (event) {
            emu.saveState(manageSaveState)
        });
        loadLastButton.click(function (event) {
            emu.loadState(lastSavedStateData, manageLoadState);
        });
        resetButton.click(resetEmulation);
        toggleAudioButton.click(function (event) {
            emu.setMuted(!emu.isMuted());
            toggleAudioButton.html(emu.isMuted() ? "Audio Off" : "Audio On")
        });
        $('.loadableState').click(requestState);
    }

    function initLoadEmulation(initState) {
        if (initState) {
            $.getJSON(STATE_EMU_INFO_JSON_URL + initState, completeLoadEmulation)
        }
        else {
            $.getJSON(GAME_EMU_INFO_JSON_URL + gameUUID, completeLoadEmulation)

        }
    }

    function completeLoadEmulation(emu_info) {
        var gameFile = emu_info['gameFile'];
        var extraFiles = emu_info['extraFiles'];
        var freezeFile = emu_info['freezeFile'];
        var args = ["emulator", citeLoadCallback, gameFile];

        if (extraFiles) args.push(extraFiles);
        if (freezeFile) args.push(freezeFile);

        CiteState.cite.apply(this, args);
    }

    initLoadEmulation(initState);
});