/**
 * This is a collection of UI elements, and UI modules (collections of elements)
 * that allow for different levels of analysis and presentation of the games and
 * their underlying activity
 * Created by erickaltman on 6/6/16.
 */

var UI = (function(){


    /*
    Basic consts for events (since I keep forgetting them), naming is getting pretty bad, oh well
     */

    const STATE_SELECT_CLICK_EVENT = "stateSelectClickEvent";
    const STATE_SELECT_START_CLICK_EVENT = "stateSelectStartClickEvent";
    const PERF_SELECT_CLICK_EVENT = "perfSelectClickEvent";
    const START_RECORDING_CLICK_EVENT = "startRecordingClickEvent";
    const STOP_RECORDING_CLICK_EVENT = "stopRecordingClickEvent";
    const START_RECORDING_STATUS_EVENT = "startRecordingStatusEvent";
    const STOP_RECORDING_CALLED_STATUS_EVENT = "stopRecordingCalledStatusEvent";
    const STOP_RECORDING_COMPLETE_STATUS_EVENT = "stopRecordingCompleteStatusEvent"; //needed since recording lags on longer videos
    const SAVE_STATE_CLICK_EVENT = "saveStateClickEvent";
    const SAVE_STATE_START_STATUS_EVENT = "saveStateStartStatusEvent";
    const SAVE_STATE_FINISH_STATUS_EVENT = "saveStateFinishStatusEvent";
    const ADD_STATUS_ALERT_EVENT = "addStatusAlertEvent";
    const REMOVE_STATUS_ALERT_EVENT = "removeStatusAlertEvent";
    const GENERAL_STATUS_ALERT_EVENT = "generalStatusAlertEvent";
    const CONTEXT_UPDATE_EVENT = "contextUpdateEvent";

    const MULTI_START_CLICK_EVENT = "multiStartClickEvent";
    const MULTI_STOP_CLICK_EVENT = "multiStopClickEvent";
    const MULTI_START_RECORD_CLICK_EVENT = "multiStartRecordClickEvent";
    const MULTI_STOP_RECORD_CLICK_EVENT = "multiStopRecordClickEvent";
    const MULTI_INPUT_ON_CLICK_EVENT = "multiInputOnClickEvent";
    const MULTI_INPUT_OFF_CLICK_EVENT = "multiInputOffClickEvent";
    const MULTI_AUDIO_OFF_CLICK_EVENT = "multiAudioOffClickEvent";
    const MULTI_AUDIO_ON_CLICK_EVENT = "multiAudioOnClickEvent";
    const MULTI_SAVE_STATE_CLICK_EVENT = "multiSaveStateClickEvent";

    /*
    Page Canonical DOM Element Ids, right now only for emulation target
     */


    /*
    Form header information, mainly for display and update form exclusions
     */
    var UPDATE_EXCLUDED_GAME_FIELDS = ['uuid', 'data_image_checksum_type', 'data_image_checksum', 'data_image_source', 'source_url', 'source_data', 'schema_version'];
    var UPDATE_EXCLUDED_PERF_FIELDS = ['uuid', 'game_uuid', 'replay_source_purl', 'replay_source_file_ref', 'replay_source_file_name', 'emulator_system_dependent_images', 'emulator_system_configuration', 'previous_performance_uuid', 'schema_version'];
    var UPDATE_EXCLUDED_STATE_FIELDS = ['id', 'uuid', 'game_uuid', 'save_state_source_data', 'compressed', 'rl_starts_data', 'rl_lengths_data', 'rl_total_length', 'save_state_type', 'emt_stack_pointer', 'stack_pointer', 'time', 'has_screen', 'created_on', 'created'];
    var UPDATE_EXCLUDED_FIELDS = UPDATE_EXCLUDED_GAME_FIELDS.concat(UPDATE_EXCLUDED_PERF_FIELDS).concat(UPDATE_EXCLUDED_STATE_FIELDS);

    var DISPLAY_GAME_FIELDS = ['copyright_year', 'date_published', 'developer', 'distributor', 'localization_region', 'notes', 'platform', 'publisher', 'title', 'version'];
    var DISPLAY_PERF_FIELDS = ['additional_info', 'description', 'emulator_name', 'emulator_version', 'location', 'notes', 'performer', 'recording_agent', 'start_datetime', 'title'];
    var DISPLAY_STATE_FIELDS = ['description', 'emulator_name', 'emulator_version'];
    var DISPLAY_FIELDS = DISPLAY_GAME_FIELDS.concat(DISPLAY_PERF_FIELDS).concat(DISPLAY_STATE_FIELDS);

    /*
    Static util functions (no where else to put them right now)
     */
    function snakeToTitle(snakeCaseText){
        function capitalize(s){ return s.charAt(0).toUpperCase() + s.slice(1); }
        return new Array(snakeCaseText.split("_").map(function(cv, i, a){ return i !== a.length - 1 ? capitalize(cv) + " " : capitalize(cv)})).join().replace(/,/g, "");
    }

    /*
    * STYLES
    * All the style code needed to render layouts
    * */

    //Single Emulation Styles

    var emulationAnalyzerStyle = {
        //border: 'solid 1px red',
        width: '1300px',
        height: '800px'
    };

    var emulationComponentStyle = {
        width: '50%',
        border: 'solid 1px lightgreen'
    };

    var emulationContainerStyle = {
        width: "640px",
        height: "480px",
        //border: "solid 1px yellow",
        display: "flex",
        flexWrap: "wrap",
        flexDirection: "row"
    };

    var emulationControlsStyle = {

    };

    var tabComponentStyle = {
        width: '50%',
        border: 'solid 1px lightblue'
    };

    var stateListingSingleStyle = {
        width: "100%",
        height: "180px",
        overflow: "scroll"
    };

    var stateItemStyle = {
        border: "solid 1px lightgray",
        borderRadius: "5px",
        height: "55px"
    };

    var selectedStateItemStyle = {
        border: "solid 1px lightgray",
        borderRadius: "5px",
        height: "55px",
        color: "white",
        backgroundColor: "lightgray"
    };

    var stateScreenStyle = {
        width: "80px",
        height: "50px",
        border: "1px solid lightgray"
    };

    var stateItemInfoStyle = {
        fontFamily: "Georgia, serif",
        fontSize: "14px",
        marginLeft: "85px",
        marginTop: "-50px"
    };

    //Multi Emulation Styles

    var multiEmulationAnalyzerStyle = {
        border: 'solid 1px red',
        width: '1300px',
        height: '800px'
    };

    var multiEmulationComponentStyle = {
        width:"50%",
        height:"100%"
    };

    var multiEmulatorContainerStyle = {
        width:"100%",
        height:"598px",
        border: "solid pink 1px",
        overflowY: "scroll"
    };

    var multiEmulationControlsContainerStyle = {
        height:"100px",
        width:"100%",
        border:"solid 1px black",
        marginTop: "10px",
        display: "flex",
        flexDirection: "row"
    };

    var startMultiControlContainerStyle = {
        display: "flex",
        flexDirection:"row"
    };

    var recordMultiControlContainerStyle = {
        display: "flex",
        flexDirection:"row",
        marginLeft: "15px"
    };

    var inputMultiControlContainerStyle = {
        display: "flex",
        flexDirection:"row",
        marginLeft: "15px"
    };

    var audioMultiControlContainerStyle = {
        display: "flex",
        flexDirection:"row",
        marginLeft: "15px"
    };

    var stateMultiControlContainerStyle = {
        display: "flex",
        flexDirection:"row",
        marginLeft: "15px"
    };

    var controlContextSelectContainerStyle = {
        listStyle: "none",
        paddingLeft:"0px"
    };

    var controlOptionActive = {
        color: "white",
        backgroundColor: "blue"
    };

    var controlOptionInactive = {
        color: "grey",
        backgroundColor: "yellow"
    };

    var contextListingStyle = {
        width:"50%",
        height:"760px",
        overflowY:"scroll"
    };

    var contextComponentStyle = {
        height: "260px",
        width: "610px",
        display: "flex",
        flexDirection: "row"
    };

    var contextStatusStyle = {
        height: "100%",
        width: "20px",
        paddingLeft: "5px"
    };

    var stateListingMultiStyle = {
        width: "100%",
        height: "180px",
        overflow: "scroll"
    };

    var searchBarContainerStyle = {
        height:"30px",
        width:"100%"
    };

    var searchBarInputStyle = {
        height:"100%",
        width:"95%"
    };

    var performanceListingStyle = {
        width: "100%",
        height: "180px",
        overflow: "scroll"
    };

    var performanceItemStyle = {
        fontFamily: "Georgia, serif",
        fontSize: "14px",
        height: "30px",
        border: "solid 1px lightgray"
    };

    var selectedPerformanceItemStyle = {
        fontFamily: "Georgia, serif",
        fontSize: "14px",
        height: "30px",
        border: "solid 1px lightgray",
        color: "white",
        backgroundColor: "lightgray"
    };

    var gameFileListingStyle = {
        overflowY: "scroll",
        height: "100%"
    };

    var gamePanelMultiStyle = {
        display: "flex",
        flexFlow: "row"
    };

    var performanceReviewStyle = {

    };

    var performanceReviewVideoStyle = {
        //width: "320px",
        //height: "200px"
    };

    var updateFormStyle = {

    };

    var statusItemStyle = {
    };

    /*
     * Single Analyzer UI Code
     * Structure:
     * Emulation Analyzer
     *   Title
     *   StatusBar
     *   AnalyzerComponent
     *       EmulationComponent
     *           EmulationContainer
     *           Emulation Controls
     *           StateListing
     *           PerformanceListing
     *       TabComponent
     *          Game
     *              InfoTable
     *          State
     *              InfoTable
     *          Performance
     *              PerformanceReview
     *              InfoTable
     *
     *  UI components, nesting listed above here
     * */

    var EmulationAnalyzer = React.createClass({
        getInitialState: function (){
            var alerts = [];
            var state = {
                update: false,
                statusAlerts: alerts,
                statusCounter: 0
            };
            var ctx = CiteManager.getContextById(this.props.contextId);
            if(ctx.lastState){
                alerts.push({statusType: GENERAL_STATUS_ALERT_EVENT, message: "Preloaded: " + ctx.lastState.record.description});
                state.selectedState = ctx.lastState.record.uuid;
            }
            return state;
        },
        componentDidMount: function(){
            var me = this;

            var node = ReactDOM.findDOMNode(this);
            node.addEventListener(CONTEXT_UPDATE_EVENT, function(){
                me.setState({update: !me.state.update}); //basically just trigger a refresh
            });

            node.addEventListener(PERF_SELECT_CLICK_EVENT, function(e){
                me.setState({selectedPerformance: e.detail});
            });

            node.addEventListener(STATE_SELECT_CLICK_EVENT, function(e){
                me.setState({selectedState: e.detail});
            });

            node.addEventListener(ADD_STATUS_ALERT_EVENT, function(e){
                var statuses = me.state.statusAlerts.concat([]);
                var removeStatus;
                e.detail.id = me.state.statusCounter;
                // Remove previous "started" updates if needed
                switch(e.detail.statusType){
                    case(SAVE_STATE_FINISH_STATUS_EVENT):
                        removeStatus = SAVE_STATE_START_STATUS_EVENT;
                        break;
                    case(STOP_RECORDING_CALLED_STATUS_EVENT):
                        removeStatus = START_RECORDING_STATUS_EVENT;
                        break;
                    case(STOP_RECORDING_COMPLETE_STATUS_EVENT):
                        removeStatus = STOP_RECORDING_CALLED_STATUS_EVENT;
                        break;
                    default:
                        break;
                }

                if(removeStatus){
                    for(var i = 0; i < statuses.length; i++){
                        if(statuses[i].statusType === removeStatus){
                            statuses.splice(i, 1);
                            break;
                        }
                    }
                }

                statuses.push(e.detail);
                me.setState({statusAlerts: statuses, statusCounter: me.state.statusCounter++ });
            });

            node.addEventListener(REMOVE_STATUS_ALERT_EVENT, function(e){
                var statuses = me.state.statusAlerts.concat([]);
                for(var i = 0; i < statuses.length; i++){
                    if(statuses[i].id === e.detail){
                        statuses.splice(i, 1);
                    }
                }
                me.setState({statusAlerts: statuses});
            });
        },
        render: function (){
            return (
                React.createElement('div', {style: emulationAnalyzerStyle},
                    React.createElement('div', {style: {display: 'flex', flexFlow: 'row'}},
                        React.DOM.h3({style: {width: "25%"}}, React.DOM.a({href:'/citations'}, "Analyzer")),
                        React.createElement(StatusBar, {alerts: this.state.statusAlerts})
                    ),
                    React.createElement('div', {style: {display: 'flex', flexFlow: 'row'}},
                        React.createElement(EmulationComponent, {contextId: this.props.contextId, selectedState: this.state.selectedState, selectedPerformance: this.state.selectedPerformance, uiType: CiteManager.SINGLE}),
                        React.createElement(TabComponent, {contextId: this.props.contextId, selectedPerformance: this.state.selectedPerformance, uiType: CiteManager.SINGLE})
                    )
                )
            )
        }
    });

    /*
     * Multi Analyzer UI Code
     * Structure:
     * Multi Emulation Analyzer
     *   Title
     *   StatusBar
     *   AnalyzerComponent
     *       MultiEmulationComponent
     *           Add Game Search Bar
     *           Emulation Controls
     *           EmulationContainer
     *       ContextListing
     *          ContextComponent
     *              TabComponent
     *                  Game
     *                      InfoTable
     *                  State
     *                      InfoTable
     *                      StateListing
     *                  Performance
     *                      InfoTable
     *                      PerformanceReview
     *
     *  UI components, nesting listed above here
     * */

    var MultiEmulationAnalyzer = React.createClass({
        dispatchStatusEvent: function(node, message, statusType){
            node.dispatchEvent(new CustomEvent(ADD_STATUS_ALERT_EVENT, {detail: {message: message, statusType: statusType}, 'bubbles': true, 'cancelable': true}))
        },
        getInitialState: function (){
            var alerts = [];
            var state = {
                update: false,
                statusAlerts: alerts,
                statusCounter: 0
            };
            return state;
        },
        update: function(){
            this.setState({update: !this.state.update});
        },
        componentDidMount: function(){
            var node = ReactDOM.findDOMNode(this);
            var me = this;
            node.addEventListener(MULTI_AUDIO_OFF_CLICK_EVENT, function(e){
                e.detail.forEach(function(id){
                    var ctx = CiteManager.getContextById(id);
                    if(ctx.emu) ctx.emu.setMuted(true);
                    me.update();
                })
            }, this);

            node.addEventListener(MULTI_AUDIO_ON_CLICK_EVENT, function(e){
                e.detail.forEach(function(id){
                    var ctx = CiteManager.getContextById(id);
                    if(ctx.emu) ctx.emu.setMuted(false);
                    me.update();
                })
            }, this);

            node.addEventListener(MULTI_INPUT_OFF_CLICK_EVENT, function(e){
                e.detail.forEach(function(id){
                    var ctx = CiteManager.getContextById(id);
                    if(ctx.emu) ctx.emu.turnOffInput();
                    me.update();
                })
            }, this);

            node.addEventListener(MULTI_INPUT_ON_CLICK_EVENT, function(e){
                e.detail.forEach(function(id){
                    var ctx = CiteManager.getContextById(id);
                    if(ctx.emu) ctx.emu.turnOnInput();
                    me.update();
                })
            }, this);

            node.addEventListener(MULTI_START_RECORD_CLICK_EVENT, function(e){
                var contextIds = e.detail;

                for(var i = 0; i < contextIds.length; i++){
                    var ctx = CiteManager.getContextById(contextIds[i]);
                    if(!ctx.recording){
                        CiteManager.startRecording(contextIds[i], function(c){
                            me.dispatchStatusEvent(node, "Started recording performance: " + c.currentPerformance.record.uuid, START_RECORDING_STATUS_EVENT);
                            me.update();
                        }.bind(this), function(err, c){}.bind(this))
                    }
                }
            }, this);

            node.addEventListener(MULTI_STOP_RECORD_CLICK_EVENT, function(e){
                var contextIds = e.detail;

                for(var i = 0; i < contextIds.length; i++){
                    var ctx = CiteManager.getContextById(contextIds[i]);
                    if(!ctx.recording){
                        me.dispatchStatusEvent(node, "Stopped recording (called) for context " + contextIds[i], STOP_RECORDING_CALLED_STATUS_EVENT);
                        CiteManager.stopRecording(contextIds[i], function(c){
                            me.dispatchStatusEvent(node, "Stopped recording (complete) for context " + contextIds[i], STOP_RECORDING_COMPLETE_STATUS_EVENT);
                            me.update();
                        }.bind(this), function(err, c){}.bind(this))
                    }
                }
            }, this);

            node.addEventListener(MULTI_START_CLICK_EVENT, function(e){
                //Check if there are already running emulations
                //if so, add them to the total including incoming emulation start ups
                //This code will not be able to resize running emulations, so if you cross
                //a threshold of 1->2, or 4->5, you are better off just starting with that many
                //and not trying to add more
                var totalTargetContexts = e.detail.length;
                for(var x = 0; x < CiteManager.activeContexts().length; x++){
                    if(e.detail.indexOf(CiteManager.activeContexts()[x]) == -1){
                        totalTargetContexts++;
                    }
                }

                for(var i=0; i < e.detail.length; i++){
                    var ctx = CiteManager.getContextById(e.detail[i]);
                    if(!ctx.emu || !ctx.emu.canvas || !document.getElementById(ctx.emu.canvas.id) || !ctx.emu.recording){
                        var options = {};
                        // Bargain basement view management here and below, basically if there are multiple
                        // active contexts, put 2 next to each other, 3-4 in a 2x2 grid, 5-9 in 3x3 grid
                        // hopefully we don't have a reason for more than 9 instances (also browser probably can't
                        // take it, so we'll test and limit based on emulation
                        if(totalTargetContexts > 1){
                            options.width = 320;
                            options.height = 240;
                        }else if(totalTargetContexts > 4){
                            options.width = 212;
                            options.height = 160;
                        }
                        if(ctx.lastState){
                            CiteManager.startEmulationWithState(ctx.id, ctx.lastState.record.uuid, function(){
                                me.update();
                            }.bind(this), options)
                        }else{
                            CiteManager.startEmulation(ctx.id, function(){
                                me.update();
                            }.bind(this), options)
                        }
                    }
                }
            }, this);

            node.addEventListener(MULTI_STOP_CLICK_EVENT, function(e){
                e.detail.forEach(function(id){
                    var ctx = CiteManager.getContextById(id);
                    if(ctx.emu) ctx.emu.quit();
                    me.update();
                });
            }, this);

            node.addEventListener(MULTI_SAVE_STATE_CLICK_EVENT, function(e){
                e.detail.forEach(function(id){
                    var ctx = CiteManager.getContextById(id);
                    if(ctx.emu){
                        me.dispatchStatusEvent(node, "Saving state for instance " + ctx.emu.instanceID, SAVE_STATE_START_STATUS_EVENT);
                        console.log("Saving for ctx: " + ctx.id);
                        CiteManager.saveState(id, function(c){
                            console.log("Saved for ctx: " + ctx.id);
                            me.update();
                            me.dispatchStatusEvent(node, "State saved for instance " + ctx.emu.instanceID, SAVE_STATE_FINISH_STATUS_EVENT);
                        }.bind(this))
                    }
                }, this);
            }, this);
        },
        render: function (){
            return (
                React.createElement('div', {style: multiEmulationAnalyzerStyle},
                    React.createElement('div', {style: {display: 'flex', flexFlow: 'row'}},
                        React.DOM.h3({style: {width: "25%"}}, React.DOM.a({href:'/citations'}, "Analyzer")),
                        React.createElement(StatusBar, {alerts: this.state.statusAlerts})
                    ),
                    React.createElement('div', {style: {display: 'flex', flexFlow: 'row'}},
                        React.createElement(MultiEmulationComponent, {contextIds: this.props.contextIds}),
                        React.createElement(ContextListing, {contextIds: this.props.contextIds})
                    )

                )
            )
        }
    });

    var MultiEmulationComponent = React.createClass({
        render: function (){
            return (
                React.createElement('div', {style:multiEmulationComponentStyle},
                    React.createElement(AddSearchBar, {}),
                    React.createElement(MultiEmulationControls, {contextIds: this.props.contextIds}),
                    React.DOM.div({id: "emulationContainer", style:multiEmulatorContainerStyle})
                )
            )
        }
    });

    var AddSearchBar = React.createClass({
        getInitialState:function(){ return {val: ""}},
        onSearchChange: function(e){
            var val = e.currentTarget.value;
            this.setState({val:val});
        },
        render: function(){
            var me = this;
            return (
                React.DOM.div({id:'addSearchBarHolder', style:searchBarContainerStyle},
                    React.DOM.input({type: 'text', name: 'searchBar', val: me.state.val, onChange: me.onSearchChange, style:searchBarInputStyle})
                )
            )
        }
    });

    var MultiEmulationControls = React.createClass({
        grabCheckBoxes: function(className){
            var affectedContexts = [];
            var cboxes = document.getElementsByClassName(className);
            for(var i=0; i < cboxes.length; i++){
                if(cboxes[i].checked){
                    affectedContexts.push(cboxes[i].id.split("_")[1])
                }
            }
            return affectedContexts;
        },
        dispatchControlEvent: function(eventName, affectedContexts){
            var node = ReactDOM.findDOMNode(this);
            node.dispatchEvent(new CustomEvent(eventName, {detail: affectedContexts, 'bubbles': true, 'cancelable': true}));
        },
        onStartClick: function(){
            this.dispatchControlEvent(MULTI_START_CLICK_EVENT, this.grabCheckBoxes('start-control-checkbox'));
        },
        onStopClick: function(){
            this.dispatchControlEvent(MULTI_STOP_CLICK_EVENT, this.grabCheckBoxes('start-control-checkbox'));
        },
        onRecordClick: function(){
            this.dispatchControlEvent(MULTI_START_RECORD_CLICK_EVENT, this.grabCheckBoxes('record-control-checkbox'));
        },
        onStopRecordClick: function(){
            this.dispatchControlEvent(MULTI_STOP_RECORD_CLICK_EVENT, this.grabCheckBoxes('record-control-checkbox'));
        },
        onInputOnClick: function(){
            this.dispatchControlEvent(MULTI_INPUT_ON_CLICK_EVENT, this.grabCheckBoxes('input-control-checkbox'));
        },
        onInputOffClick: function(){
            this.dispatchControlEvent(MULTI_INPUT_OFF_CLICK_EVENT, this.grabCheckBoxes('input-control-checkbox'));
        },
        onMuteClick: function(){
            this.dispatchControlEvent(MULTI_AUDIO_OFF_CLICK_EVENT, this.grabCheckBoxes('audio-control-checkbox'));
        },
        onUnMuteClick: function(){
            this.dispatchControlEvent(MULTI_AUDIO_ON_CLICK_EVENT, this.grabCheckBoxes('audio-control-checkbox'));
        },
        onStateSaveClick: function(){
            this.dispatchControlEvent(MULTI_SAVE_STATE_CLICK_EVENT, this.grabCheckBoxes('state-control-checkbox'));
        },
        render: function (){
            var me = this;
            return (
                React.DOM.div({style:multiEmulationControlsContainerStyle},
                    React.DOM.div({style:startMultiControlContainerStyle},
                        React.DOM.div({style:{display:"flex",flexDirection:"column"}},
                            React.DOM.button({style:{height:'50%'}, onClick: me.onStartClick}, "Start"),
                            React.DOM.button({style:{height:'50%'}, onClick: me.onStopClick}, "Stop")
                        ),
                        React.DOM.div({},
                            React.DOM.ul({style:controlContextSelectContainerStyle},
                                this.props.contextIds.map(function(item){
                                    var ctx = CiteManager.getContextById(item);
                                    return React.DOM.li({key:"startControlContextContainer_"+item},
                                        React.DOM.input({className: "start-control-checkbox", id:"startControlContextInput_" + item, type:"checkbox"}),
                                        React.DOM.span({style: ctx.emu && ctx.emu.canvas && document.getElementById(ctx.emu.canvas.id) ? controlOptionActive : controlOptionInactive}, "Game " + item)
                                    )
                                }, this)
                            )
                        )
                    ),
                    React.DOM.div({style:recordMultiControlContainerStyle},
                        React.DOM.div({style:{display:"flex",flexDirection:"column"}},
                            React.DOM.button({style:{height:'50%'}, onClick: me.onRecordClick}, "Record"),
                            React.DOM.button({style:{height:'50%'}, onClick: me.onStopRecordClick}, "Stop")
                        ),
                        React.DOM.div({},
                            React.DOM.ul({style:controlContextSelectContainerStyle},
                                this.props.contextIds.map(function(item){
                                    var ctx = CiteManager.getContextById(item);
                                    return React.DOM.li({key:"recordControlContextContainer_"+item},
                                        React.DOM.input({type:"checkbox", className:"record-control-checkbox", id:"recordControlContextInput_" + item}),
                                        React.DOM.span({style: ctx.emu && ctx.emu.recording ? controlOptionActive : controlOptionInactive}, "Game " + item)
                                    )
                                }, this)
                            )
                        )
                    ),
                    React.DOM.div({style:inputMultiControlContainerStyle},
                        React.DOM.div({style:{display:"flex",flexDirection:"column"}},
                            React.DOM.button({style:{height:'50%'}, onClick: me.onInputOnClick}, "I On"),
                            React.DOM.button({style:{height:'50%'}, onClick: me.onInputOffClick}, "I Off")
                        ),
                        React.DOM.div({},
                            React.DOM.ul({style:controlContextSelectContainerStyle},
                                this.props.contextIds.map(function(item){
                                    var ctx = CiteManager.getContextById(item);
                                    return React.DOM.li({key:"inputControlContextContainer_"+item},
                                        React.DOM.input({className:"input-control-checkbox", id:"inputControlContextInput_"+item, type:"checkbox"}),
                                        React.DOM.span({style: ctx.emu && ctx.emu.canvas && document.getElementById(ctx.emu.canvas.id) && ctx.emu.inputActive ? controlOptionActive : controlOptionInactive}, "Game " + item)
                                    )
                                }, this)
                            )
                        )
                    ),
                    React.DOM.div({style:audioMultiControlContainerStyle},
                        React.DOM.div({style:{display:"flex",flexDirection:"column"}},
                            React.DOM.button({style:{height:'50%'}, onClick: me.onUnMuteClick}, "A On"),
                            React.DOM.button({style:{height:'50%'}, onClick: me.onMuteClick}, "A Off")
                        ),
                        React.DOM.div({},
                            React.DOM.ul({style:controlContextSelectContainerStyle},
                                this.props.contextIds.map(function(item){
                                    var ctx = CiteManager.getContextById(item);
                                    return React.DOM.li({key:"audioControlContextContainer_"+item},
                                        React.DOM.input({className:"audio-control-checkbox", id:"audioControlContextInput_"+item, type:"checkbox"}),
                                        React.DOM.span({style: ctx.emu && !ctx.emu.isMuted() ? controlOptionActive : controlOptionInactive}, "Game " + item)
                                    )
                                }, this)
                            )
                        )
                    ),
                    React.DOM.div({style:stateMultiControlContainerStyle},
                        React.DOM.div({style:{display:"flex",flexDirection:"column"}},
                            React.DOM.button({style:{height:"100%"}, onClick: me.onStateSaveClick}, "Save")
                        ),
                        React.DOM.div({},
                            React.DOM.ul({style:controlContextSelectContainerStyle},
                                this.props.contextIds.map(function(item){
                                    return React.DOM.li({key:"stateControlContextContainer_"+item},
                                        React.DOM.input({className:"state-control-checkbox", id:"stateControlContextInput_"+item, type:"checkbox"}),
                                        React.DOM.span({}, "Game " + item)
                                    )
                                }, this)
                            )
                        )
                    )
                )
            )
        }
    });

    var StatusBar = React.createClass({
        render: function(){
            return (
                React.DOM.div({style:{height: "50px", width:"75%", border:'solid 1px blue', display:'flex', flexFlow:'row'}},
                    this.props.alerts.map(function(s, i, sa){
                        return React.createElement(StatusItem, {key: "status_" + s.id ,id: s.id, message: s.message });
                    })
                )
            )
        }
    });

    var StatusItem = React.createClass({
        render: function(){
            return (
                React.DOM.div({style:statusItemStyle, id: this.props.id, className:'statusItem'}, this.props.message)
            )
        }
    });

    var EmulationComponent = React.createClass({
        getInitialState: function(){
            var state = {
                startedEmulation: false,
                isRecording: false,
                muted: false
            };
            var ctx = CiteManager.getContextById(this.props.contextId);
            state.availableStates = ctx.availableStates;
            state.availablePerformances = ctx.availablePerformances;
            return state;
        },
        dispatchStatusEvent: function(node, message, statusType){
            node.dispatchEvent(new CustomEvent(ADD_STATUS_ALERT_EVENT, {detail: {message: message, statusType: statusType}, 'bubbles': true, 'cancelable': true}))
        },
        componentDidMount: function(){
            var me = this;
            var node = ReactDOM.findDOMNode(this);

            node.addEventListener('start', function(){
                CiteManager.startEmulation(me.props.contextId, function(){
                    var ctx = CiteManager.getContextById(me.props.contextId);
                    me.setState({startedEmulation: true, muted: ctx.emu.isMuted()})
                })
            });

            node.addEventListener('loadPrevious', function(e){
                CiteManager.loadPreviousState(me.props.contextId, function(context){
                    ReactDOM.findDOMNode(me).dispatchEvent(new Event(CONTEXT_UPDATE_EVENT, {'bubbles':true, 'cancelable': true}))
                })
            });

            node.addEventListener(START_RECORDING_CLICK_EVENT, function(){
                CiteManager.startRecording(me.props.contextId, function(c){
                    me.dispatchStatusEvent(node, "Started recording performance: " + c.currentPerformance.record.uuid, START_RECORDING_STATUS_EVENT);
                }, function(err, c){ //err needed due to return callback for initSaveState
                    me.setState({availableStates: c.availableStates, isRecording: c.emu.recording})
                })
            });

            //Two events here, one to signal stop recording started, and on to signal actual completion of recording
            //Both are necessary since there is sometimes significant lag due to backup in the video / audio buffer
            //processing
            node.addEventListener(STOP_RECORDING_CLICK_EVENT, function (){
                var perf = CiteManager.getContextById(me.props.contextId).currentPerformance.record;
                me.dispatchStatusEvent(node, "Stop recording performance (called): " + perf['uuid'] + " called.", STOP_RECORDING_CALLED_STATUS_EVENT);
                CiteManager.stopRecording(me.props.contextId,
                    function(c){
                        me.dispatchStatusEvent(node, "Stop recording performance (complete): " + c.currentPerformance.record.uuid, STOP_RECORDING_COMPLETE_STATUS_EVENT);
                        me.setState({availablePerformances: c.availablePerformances, isRecording: c.emu.recording});
                        ReactDOM.findDOMNode(me).dispatchEvent(new Event(CONTEXT_UPDATE_EVENT, {'bubbles': true, 'cancelable': true}));
                    },
                    function(err, c){//err needed due to return callback for initSaveState
                        me.setState({availableStates: c.availableStates})
                    })
            });

            node.addEventListener('mute', function(e){
                var muted = CiteManager.mute(me.props.contextId);
                me.setState({muted: muted});
            });

            node.addEventListener(SAVE_STATE_CLICK_EVENT, function(e){
                var title = CiteManager.getContextById(me.props.contextId).currentGame.record.title;
                me.dispatchStatusEvent(node, "Saving State for " + title, SAVE_STATE_START_STATUS_EVENT);
                CiteManager.saveState(me.props.contextId, function(context){
                    me.dispatchStatusEvent(node, "Saving State Complete for " + title, SAVE_STATE_FINISH_STATUS_EVENT);
                    me.setState({availableStates: context.availableStates});
                })
            });

            node.addEventListener(STATE_SELECT_CLICK_EVENT, function(e){
                CiteManager.loadState(me.props.contextId, e.detail, function(context){
                    ReactDOM.findDOMNode(me).dispatchEvent(new Event(CONTEXT_UPDATE_EVENT, {'bubbles':true, 'cancelable': true}))
                })
            });

            node.addEventListener(STATE_SELECT_START_CLICK_EVENT, function(e){
                CiteManager.startEmulationWithState(me.props.contextId, e.detail, function(context){
                    me.setState({availableStates: context.availableStates, startedEmulation: true});
                    ReactDOM.findDOMNode(me).dispatchEvent(new Event(CONTEXT_UPDATE_EVENT, {'bubbles': true, 'cancelable': true}))
                })
            });
        },
        componentWillReceiveProps: function(nextProps){
            var ctx = CiteManager.getContextById(nextProps.contextId);
            this.setState({availableStates: ctx.availableStates, availablePerformances: ctx.availablePerformances});
        },
        render: function (){
            return (
                React.createElement('div', {style: emulationComponentStyle},
                    React.createElement('div', {id: this.props.contextId + "_emulationContainer", style:emulationContainerStyle}),
                    React.createElement(EmulationControls, {
                        started: this.state.startedEmulation,
                        recording: this.state.isRecording,
                        muted: this.state.muted
                    }),
                    React.createElement('div', {style:{width:"100%"}},
                        React.createElement(Tabs, {},
                            React.createElement(TabList, {},
                                React.createElement(Tab, {}, "Available States"),
                                React.createElement(Tab, {}, "Available Performances")
                            ),
                            React.createElement(TabPanel, {},
                                React.createElement(StateListing, {started: this.state.startedEmulation, selectedState: this.props.selectedState, availableStates: this.state.availableStates, uiType: this.props.uiType})
                            ),
                            React.createElement(TabPanel, {},
                                React.createElement(PerformanceListing, {availablePerformances: this.state.availablePerformances, selectedPerformance: this.props.selectedPerformance, uiType: this.props.uiType})
                            )
                        )
                    )
                )
            )
        }
    });

    var EmulationControls = React.createClass({
        startEmulationClick: function(e){
            ReactDOM.findDOMNode(this).dispatchEvent(new Event('start', {"bubbles": true, "cancelable": true}))
        },
        loadPreviousStateClick: function(e){
            ReactDOM.findDOMNode(this).dispatchEvent(new Event('loadPrevious', {"bubbles": true, "cancelable": true}))
        },
        startRecordingClick: function(e){
            ReactDOM.findDOMNode(this).dispatchEvent(new Event(START_RECORDING_CLICK_EVENT, {"bubbles": true, "cancelable": true}))
        },
        stopRecordingClick: function(e){
            ReactDOM.findDOMNode(this).dispatchEvent(new Event(STOP_RECORDING_CLICK_EVENT, {"bubbles": true, "cancelable": true}))
        },
        muteClick: function(e){
            ReactDOM.findDOMNode(this).dispatchEvent(new Event('mute', {"bubbles": true, "cancelable": true}))
        },
        saveStateClick: function(e){
            ReactDOM.findDOMNode(this).dispatchEvent(new Event(SAVE_STATE_CLICK_EVENT, {"bubbles": true, "cancelable": true}))
        },
        render: function (){
            return (
                React.DOM.div({style:emulationControlsStyle},
                    React.DOM.button({id:'startEmulation', onClick: this.startEmulationClick }, 'Start Emulation'),
                    React.DOM.button({id:'saveState', onClick: this.saveStateClick }, 'Save State'),
                    React.DOM.button({id:'loadPreviousState', onClick: this.loadPreviousStateClick}, 'Load Previous State'),
                    React.DOM.button({id:'startRecording', onClick: this.startRecordingClick}, 'Start Recording'),
                    React.DOM.button({id:'stopRecording', onClick: this.stopRecordingClick}, 'Stop Recording'),
                    React.DOM.button({id:'mute', onClick: this.muteClick }, this.props.muted ? 'Audio Off' : 'Audio On')
                )
            )
        }
    });
    
    var StateListing = React.createClass({
        displayName: "StateListing",
        render: function (){
            return (
                React.DOM.div({style: this.props.uiType === CiteManager.SINGLE ? stateListingSingleStyle : stateListingMultiStyle},
                    this.props.availableStates.map(function(s){
                        return React.createElement(StateItem, {key:'StateItem_' + s.uuid,record: s, started: this.props.started, selected: this.props.selectedState === s.uuid })
                    }.bind(this))
                )
            )
        }
    });

    var StateItem = React.createClass({
        displayName: "StateItem",
        stateSelectClick: function(e){
            e.stopPropagation();
            var node = ReactDOM.findDOMNode(this);
            if(this.props.started){
                node.dispatchEvent(new CustomEvent(STATE_SELECT_CLICK_EVENT, {"detail": this.props.record.uuid, "bubbles": true, "cancelable": true }))
            }else{
                node.dispatchEvent(new CustomEvent(STATE_SELECT_START_CLICK_EVENT, {"detail": this.props.record.uuid, "bubbles": true, "cancelable": true }));
            }
        },
        render: function (){
            var screenURL = "/cite_data/" + this.props.record.uuid + "/screen_" + this.props.record.uuid + ".png";
            return (
                React.DOM.div({style: this.props.selected ? selectedStateItemStyle : stateItemStyle, onClick: this.stateSelectClick},
                    React.createElement(StateScreenShot, {screenURL: screenURL}),
                    React.createElement(StateItemInfo, {record: this.props.record})
                )
            )
        }
    });

    var StateScreenShot = React.createClass({
        displayName: "StateScreenShot",
        render: function (){
            return (
                React.DOM.img({src: this.props.screenURL, style:stateScreenStyle})
            )
        }
    });

    var StateItemInfo = React.createClass({
        displayName: "StateItemInfo",
        render: function(){
            return (
                React.DOM.div({style: stateItemInfoStyle}, this.props.record.description + " " + this.props.record.uuid)
            )
        }
    });
    
    var PerformanceListing = React.createClass({
        displayName: "PerformanceListing",
        render: function (){
            return (
                React.DOM.div({style:performanceListingStyle},
                    this.props.availablePerformances.map(function(s){
                        return React.createElement(PerformanceItem, {key:'PerformanceItem_' + s.uuid, record: s, selected: this.props.selectedPerformance === s.uuid })
                    }.bind(this))
                )
            )
        }
    });

    var PerformanceItem = React.createClass({
        displayName: "PerformanceItem",
        perfSelectClick: function(){
            ReactDOM.findDOMNode(this).dispatchEvent(new CustomEvent(PERF_SELECT_CLICK_EVENT,
                {detail: this.props.record.uuid, bubbles: "true", cancelable: "true"}))
        },
        render: function(){
            return (
                React.DOM.div({style: this.props.selected ? selectedPerformanceItemStyle : performanceItemStyle, onClick: this.perfSelectClick}, this.props.record.title + " " + this.props.record.uuid)
            )
        }
    });

    var Tabs = ReactTabs.Tabs;
    var Tab = ReactTabs.Tab;
    var TabList = ReactTabs.TabList;
    var TabPanel = ReactTabs.TabPanel;

    var ContextListing = React.createClass({
        displayName: "ContextListing",
        getInitialState: function(){
            return null;
        },
        render: function(){
            return (
                React.DOM.div({style:contextListingStyle},
                    this.props.contextIds.map(function (id){
                        return React.createElement(ContextComponent, {key: "contextComponent_" + id, contextId: id})
                    }, this)
                )
            )
        }
    });

    var ContextComponent = React.createClass({
        displayName: "ContextComponent",
        getInitialState: function(){
            var ctx = CiteManager.getContextById(this.props.contextId);
            var state = {};
            state.currentGameRecord = ctx.currentGame.record;
            state.currentGameFiles = ctx.currentGame.fileInformation;
            if(ctx.lastState){
                state.lastSelectedStateRecord = ctx.lastState.record;
                state.lastStateId = ctx.lastState.record.uuid;
            }
            state.lastSelectedPerfRecord = null;
            state.lastSelectPerformanceId = null;
            state.availableStates = ctx.availableStates;
            state.availablePerformances = ctx.availablePerformances;
            return state;
        },
        componentDidMount: function(){
            var node = ReactDOM.findDOMNode(this);
            var me = this;

            node.addEventListener(STATE_SELECT_CLICK_EVENT, function(e){
                CiteManager.loadState(this.props.contextId, e.detail, function(c){
                    me.setState({
                        lastSelectedStateRecord: c.lastState.record,
                        lastStateId: e.detail
                    })
                })
            }.bind(this));

            node.addEventListener(PERF_SELECT_CLICK_EVENT, function(e){
                var ctx = CiteManager.getContextById(this.props.contextId);
                this.setState({
                    lastSelectedPerfRecord: ctx.availablePerformances.filter(function(item){ return item.uuid === e.detail})[0],
                    lastSelectedPerformanceId: e.detail
                })
            }.bind(this));
        },
        componentWillReceiveProps: function(nextProps){
            var ctx = CiteManager.getContextById(nextProps.contextId);
            this.setState({
                availableStates: ctx.availableStates,
                availablePerformances: ctx.availablePerformances,
                running: ctx.emu && ctx.emu.canvas && document.getElementById(ctx.emu.canvas.id) ? true : false,
                recording: ctx.emu ? ctx.emu.recording : false,
                inputting: ctx.emu ? ctx.emu.inputActive : false,
                muted: ctx.emu ? ctx.emu.isMuted() : false
            })
        },
        render: function(){
            return (
                React.createElement('div', {style: contextComponentStyle},
                    React.createElement('div', {style: contextStatusStyle},
                        React.DOM.p({}, this.props.contextId)
                    ),
                    React.createElement(Tabs, {},
                        React.createElement(TabList, {},
                            React.createElement(Tab, {}, "Game"),
                            React.createElement(Tab, {}, "State"),
                            React.createElement(Tab, {}, "Performance"),
                            React.createElement(Tab, {}, "Real Time Analytics")
                        ),
                        React.createElement(TabPanel, {},
                            React.DOM.div({style:gamePanelMultiStyle},
                                React.createElement(InfoTable, {contextId: this.props.contextId, recordType: 'game', id: this.state.currentGameRecord.uuid, record: this.state.currentGameRecord}),
                                React.createElement(GameFileListing, {fileInformation: this.state.currentGameFiles})
                            )
                        ),
                        React.createElement(TabPanel, {},
                            React.createElement(InfoTable, {contextId: this.props.contextId, recordType: 'state', id: this.state.lastStateId, record: this.state.lastSelectedStateRecord}),
                            React.createElement(StateListing, {started: this.state.running, uiType: this.props.uiType, selectedState: this.state.lastStateId, availableStates:this.state.availableStates})
                        ),
                        React.createElement(TabPanel, {},
                            React.createElement(InfoTable, {contextId: this.props.contextId, recordType: 'performance', id: this.state.lastSelectPerformanceId, record: this.state.lastSelectedPerfRecord}),
                            React.createElement(PerformanceListing, {uiType: this.props.uiType, availablePerformances: this.state.availablePerformances})
                        ),
                        React.createElement(TabPanel, {},
                            React.DOM.h1({}, "Heap Information Here")
                        )
                    )
                )
            )
        }
    });

    var TabComponent = React.createClass({
        displayName: "TabComponent",
        getInitialState: function(){
            var ctx = CiteManager.getContextById(this.props.contextId);
            var state = {};
            state.currentGameRecord = ctx.currentGame.record;
            state.currentGameFiles = ctx.currentGame.fileInformation;
            state.lastSelectedStateRecord = ctx.lastState.record;
            state.lastSelectedPerfRecord = this.getSelectedPerformance(this.props.selectedPerformance, ctx.availablePerformances);
            state.lastStateId = state.lastSelectedStateRecord ? state.lastSelectedStateRecord.uuid : "";
            state.lastSelectPerformanceId = state.lastSelectedPerfRecord ? state.lastSelectedPerfRecord.uuid : "";
            return state;
        },
        getSelectedPerformance: function(uuid, perfList){
            for(var i = 0; i < perfList.length; i++){
                if(uuid == perfList[i].uuid){
                    return perfList[i];
                }
            }
        },
        componentWillReceiveProps: function(nextProps){
            var ctx = CiteManager.getContextById(this.props.contextId);
            var lastSelectedPerfRecord = this.getSelectedPerformance(nextProps.selectedPerformance, ctx.availablePerformances);
            var lastSelectedStateRecord = ctx.lastState ? ctx.lastState.record : {};
            this.setState({currentGameRecord: ctx.currentGame.record,
                currentGameFiles: ctx.currentGame.fileInformation,
                lastSelectedStateRecord: lastSelectedStateRecord,
                lastSelectedPerfRecord: lastSelectedPerfRecord,
                lastSelectPerformanceId: lastSelectedPerfRecord ? lastSelectedPerfRecord.uuid : "",
                lastStateId: lastSelectedStateRecord ? lastSelectedStateRecord.uuid : ""
            });
        },
        render: function(){
            var perfURL = "";
            var screenURL = "";
            if(this.state.lastSelectedPerfRecord){
                perfURL = "/cite_data/" + this.state.lastSelectedPerfRecord.replay_source_file_ref + "/" + this.state.lastSelectedPerfRecord.replay_source_file_name;
            }
            if(this.state.lastSelectedStateRecord){
                screenURL = "/cite_data/" + this.state.lastSelectedStateRecord.uuid + "/screen_" + this.state.lastSelectedStateRecord.uuid + ".png";
            }
            return (
                React.createElement('div', {style:tabComponentStyle},
                    React.createElement(Tabs, {},
                        React.createElement(TabList, {},
                            React.createElement(Tab, {}, "Game"),
                            React.createElement(Tab, {}, "State"),
                            React.createElement(Tab, {}, "Performance"),
                            React.createElement(Tab, {}, "Real Time")
                        ),
                        React.createElement(TabPanel, {},
                            React.createElement(InfoTable, {contextId: this.props.contextId, recordType: 'game', id: this.state.currentGameRecord.uuid, record: this.state.currentGameRecord}),
                            React.createElement(GameFileListing, {fileInformation: this.state.currentGameFiles})
                        ),
                        React.createElement(TabPanel, {},
                            React.DOM.img({src:screenURL}),
                            React.createElement(InfoTable, {contextId: this.props.contextId, recordType: 'state', id: this.state.lastStateId, record: this.state.lastSelectedStateRecord})
                        ),
                        React.createElement(TabPanel, {},
                            React.createElement(InfoTable, {contextId: this.props.contextId, recordType: 'performance', id: this.state.lastSelectPerformanceId, record: this.state.lastSelectedPerfRecord}),
                            React.createElement(PerformanceReview, {performanceVideoURL: perfURL, id: this.state.lastSelectPerformanceId})
                        ),
                        React.createElement(TabPanel, {},
                            React.DOM.h1({}, "Heap Information Here")
                        )
                    )
                )
            )
        }
    });

    var PerformanceReview = React.createClass({
        displayName: "PerformanceReview",
        getInitialState: function(){
            return {linkedStates: []}
        },
        componentDidMount: function(){
            $.get(CiteManager.jsonPerformanceInfoURL(this.props.id), function(result){
                this.setState({linkedStates: result.linkedStates})
            }.bind(this))
        },
        componentWillReceiveProps: function(nextProps){
            $.get(CiteManager.jsonPerformanceInfoURL(nextProps.id), function(result){
                this.setState({linkedStates: result.linkedStates})
            }.bind(this))
        },
        render: function (){
            return (
                React.DOM.div({id: "performanceReview_" + this.props.id },
                    React.DOM.video({style:performanceReviewVideoStyle, src: this.props.performanceVideoURL, type:"video/mp4", controls:true}),
                    this.state.linkedStates.map(function(linkRecord, index){
                        return React.DOM.div({key: "linkedState_" + linkRecord.state_record.uuid }, "time index " + linkRecord.time_index + " state: " + linkRecord.state_record.uuid);
                    }, this)
                )
            );
        }
    });

    var InfoTable = React.createClass({
        displayName: "InfoTable",
        getInitialState: function(){
            return {editable: false, formData: this.props.record}
        },
        editInfoClick: function(){
            var me = this;
            if(this.state.editable){
                var updateObject = {};
                for(var key in this.state.formData){
                    if(this.state.formData.hasOwnProperty(key)){
                        //if the value has been updated
                        if(this.props.record[key] !== this.state.formData[key]){
                            updateObject[key] = this.state.formData[key];
                        }
                    }
                }
                //Make sure you actually have something to update, otherwise just remove inputs
                if(!$.isEmptyObject(updateObject)){
                    CiteManager.updateCiteRecord(this.props.contextId, this.props.recordType, this.props.record.uuid, updateObject, function(record){
                        ReactDOM.findDOMNode(me).dispatchEvent(new Event(CONTEXT_UPDATE_EVENT, {'bubbles': true, 'cancelable': true})); //Causes refresh which should update incoming prop record
                        me.setState({editable: false});
                    });
                }else{
                    this.setState({editable: false})
                }
            }else{
                this.setState({editable: true})
            }
        },
        itemize: function(obj){
            var items = [];
            for(var key in obj){
                if(obj.hasOwnProperty(key)){
                    items.push([key, obj[key]])
                }
            }
            return items;
        },
        infoItemChange: function(e){
            var key = e.currentTarget.name;
            var val = e.currentTarget.value;

            //copy form data
            var no = {};
            for(var k in this.state.formData){
                if(this.state.formData.hasOwnProperty(k)){
                    no[k] = this.state.formData[k];
                }
            }
            //copy over change
            no[key] = val;

            //set new state
            this.setState({formData: no})
        },
        componentWillReceiveProps: function(nextProps){
            this.setState({formData: nextProps.record});
        },
        render: function (){
            var me = this;
            return (
                React.DOM.ul({}, this.itemize(this.state.formData).map(function(i){
                    var key = i[0];
                    var val = i[1] ? i[1] : '';
                    if(DISPLAY_FIELDS.indexOf(key) !== -1){
                        if(me.state.editable && UPDATE_EXCLUDED_FIELDS.indexOf(key) == -1){
                            return React.DOM.li({key:'infoItem_' + me.props.id + "_" + key}, snakeToTitle(key) + " : ", React.DOM.input({type: 'text', name: key, value: val, onChange: me.infoItemChange}));
                        }else{
                            return React.DOM.li({key:'infoItem_' + me.props.id + "_" + key}, snakeToTitle(key) + " : " + val);
                        }
                    }
                }), React.DOM.button({onClick: this.editInfoClick }, this.state.editable ? "Submit" : "Edit Info"))
            )
        }
    });

    var GameFileListing = React.createClass({
        displayName: "GameFileListing",
        render: function (){
            var fi = this.props.fileInformation;
            var fi_keys;
            try{
                fi_keys = Object.keys(fi);
            }catch(e){
                fi_keys = [];
            }
            return (
                React.DOM.ul({style:gameFileListingStyle}, fi_keys.map(function(fi_key){
                    var key = fi_key + "_" + fi[fi_key].game_uuid;
                    return React.DOM.li({key:key}, fi_key)
                }))
            );
        }
    });

    return {
        createSingleUI: function(rootDiv, contextId){
            ReactDOM.render(React.createElement(EmulationAnalyzer, {contextId: contextId}), rootDiv)
        },
        createMultiUI: function(rootDiv, contextIds){
            ReactDOM.render(React.createElement(MultiEmulationAnalyzer, {contextIds: contextIds}), rootDiv)
        }
    }

}());
