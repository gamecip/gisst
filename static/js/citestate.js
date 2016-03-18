(function () {
    window.CiteState = {};

    var NES = "NES";
    var SNES = "SNES";
    var DOS = "DOS";

    var FCEUX = "FCEUX";
    var SNES9X = "SNES9X";
    var DOSBOX = "DOSBOX";

    var EmulatorNames = {};
    EmulatorNames[NES] = FCEUX;
    EmulatorNames[SNES] = SNES9X;
    EmulatorNames[DOS] = DOSBOX;

    var LoadedEmulators = {};

    var EmulatorInstances = {};
    EmulatorInstances[FCEUX] = [];
    EmulatorInstances[SNES9X] = [];
    EmulatorInstances[DOSBOX] = [];

    function determineSystem(gameFile) {
        if (gameFile.match(/\.(smc|sfc)$/i)) {
            return SNES;
        } else if (gameFile.match(/\.(exe|com|bat|dos|iso)$/i)) {
            return DOS;
        } else if (gameFile.match(/\.(nes|fds)$/i)) {
            return NES;
        }
        throw new Error("Unrecognized System");
    }

    function realCite(targetID, onLoad, system, emulator, emulatorRootURL, gameFile, freezeFile, otherFiles) {
        var emuModule = LoadedEmulators[emulator];
        if (!emuModule) {
            throw new Error("Emulator Not Loaded");
        }
        //todo: compile everybody with -s modularize and export name to FCEUX, SNES9X, DOSBOX.
        //todo: and be sure that gameFile, freezeFile, and extraFiles are used appropriately.
        var targetElement = document.getElementById(targetID);
        targetElement.innerHTML = "";
        targetElement.tabIndex = 0;
        targetElement.addEventListener("click", function() {
            targetElement.focus();
        });
        var canvas = (function() {
            var canvas = document.createElement("canvas");
            canvas.width = targetElement.clientWidth;
            canvas.height = targetElement.clientHeight;
            canvas.style.setProperty( "width", "inherit", "important");
            canvas.style.setProperty("height", "inherit", "important");
            targetElement.appendChild(canvas);

            // As a default initial behavior, pop up an alert when webgl context is lost. To make your
            // application robust, you may want to override this behavior before shipping!
            // See http://www.khronos.org/registry/webgl/specs/latest/1.0/#5.15.2
            canvas.addEventListener("webglcontextlost", function(e) {
                alert('WebGL context lost. You will need to destroy and recreate this widget.');
                e.preventDefault();
            }, false);
            return canvas;
        })();
        var instance;
        var moduleObject = {
            locateFile: function(url) {
                return emulatorRootURL + url;
            },
            targetID:targetID,
            keyboardListeningElement:targetElement,
            system:system,
            emulator:emulator,
            gameFile:gameFile,
            freezeFile:freezeFile,
            extraFiles:otherFiles,
            preRun: [],
            postRun: [],
            print: function(m) { console.log(m); },
            printErr: function(e) { console.error(e); },
            canvas: canvas
        };
        instance = emuModule(moduleObject);
        EmulatorInstances[emulator].push(instance);
        if(onLoad) {
            onLoad(instance);
        }
        return instance;
    }

    //the loaded emulator instance will implement saveState(cb), saveExtraFiles(cb), and loadState(s,cb)
    window.CiteState.cite = function (targetID, onLoad, emulatorRootURL, gameFile, freezeFile, otherFiles) {
        var system = determineSystem(gameFile);
        var emulator = EmulatorNames[system];
        if (!(emulator in LoadedEmulators)) {
            var script = emulatorRootURL + emulator + ".js";
            //load the script on the page
            var scriptElement = document.createElement("script");
            scriptElement.src = script;
            scriptElement.onload = function () {
                LoadedEmulators[emulator] = window[emulator];
                realCite(targetID, onLoad, system, emulator, emulatorRootURL, gameFile, freezeFile, otherFiles);
            };
            document.body.appendChild(scriptElement);
        } else {
            realCite(targetID, onLoad, system, emulator, emulatorRootURL, gameFile, freezeFile, otherFiles);
        }
    }
})();


