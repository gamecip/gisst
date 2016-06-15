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
    



    /*
    * All the style code needed to render layouts
    * */

    var emulationAnalyzerStyle = {
        display: 'flex',
        flexFlow: 'column',
        border: 'solid 1px red',
        width: '100%',
        height: '100%'

    };

    var emulationComponentStyle = {
        width: '50%',
        border: 'solid 1px lightgreen'
    };

    var tabComponentStyle = {
        width: '50%',
        border: 'solid 1px lightblue'
    };

    //Emulation container will change size based on specific emulator
    var emulationContainerStyle = {
        width: "640px",
        height: "480px",
        border: "solid 1px yellow"
    };

    var emulationControlsStyle = {

    };

    var stateListingStyle = {
        width: "100%"
    };

    var stateItemStyle = {
        border: "solid 1px lightgray",
        borderRadius: "5px"
    };

    var stateScreenStyle = {
        width: "160px",
        height: "100px"
    };

    var performanceListingStyle = {
        width: "50%"
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
     * Analyzer UI Code
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
     *           PerformanceReview
     *           UpdateForm
     *
     *  UI components, nesting listed above here
     * */

    var EmulationAnalyzer = React.createClass({
        getInitialState: function (){
            var alerts = [];
            var ctx = CiteManager.getContextById(this.props.contextId);
            if(ctx.lastState){
                alerts.push({statusType: GENERAL_STATUS_ALERT_EVENT, message: "Preloaded: " + ctx.lastState.record.description})
            }
            return {update: false, statusAlerts: alerts, statusCounter: 0}
        },
        componentDidMount: function(){
            var me = this;

            var node = ReactDOM.findDOMNode(this);
            node.addEventListener('contextUpdate', function(){
                me.setState({update: !me.state.update}); //basically just trigger a refresh
            });

            node.addEventListener(PERF_SELECT_CLICK_EVENT, function(e){
                me.setState({selectedPerformance: e.detail});
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
                        React.DOM.h1({style: {width: "25%"}}, "Analyzer"),
                        React.createElement(StatusBar, {alerts: this.state.statusAlerts})
                    ),
                    React.createElement('div', {style: {display: 'flex', flexFlow: 'row'}},
                        React.createElement(EmulationComponent, {contextId: this.props.contextId}),
                        React.createElement(TabComponent, {contextId: this.props.contextId, selectedPerformance: this.state.selectedPerformance })
                    )
                )
            )
        }
    });

    var StatusBar = React.createClass({
        render: function(){
            return (
                React.DOM.div({style:{width:"75%", border:'solid 1px blue', display:'flex', flexFlow:'row'}},
                    this.props.alerts.map(function(s, i, sa){
                        return React.createElement(StatusItem, {id: s.id, message: s.message });
                    })
                )
            )
        }
    });

    var StatusItem = React.createClass({
        render: function(){
            return (
                React.DOM.div({style:statusItemStyle, key: "status_"+this.props.id, id: this.props.id, className:'statusItem'}, this.props.message)
            )
        }
    });

    var EmulationComponent = React.createClass({
        getInitialState: function(){
            var state = {
                startedEmulation: false,
                startedRecording: false,
                muted: false
            };
            var ctx = CiteManager.getContextById(this.props.contextId);
            state.availableStates = ctx.availableStates;
            state.availablePerformances = ctx.availablePerformances;

            return state;
        },
        dispatchStatusEvent: function(node, message, statusType){
            node.dispatchEvent(new CustomEvent(ADD_STATUS_ALERT_EVENT, {detail: {message: message, statusType: statusType}, 'bubbles':true}))
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
                CiteManager.loadPreviousState(me.props.contextId, function(){
                })
            });

            node.addEventListener(START_RECORDING_CLICK_EVENT, function(){
                CiteManager.startRecording(me.props.contextId, function(c){
                    me.dispatchStatusEvent(node, "Started recording performance: " + c.currentPerformance.record.uuid, START_RECORDING_STATUS_EVENT);
                    me.setState({availableStates: c.availableStates});
                })
            });

            //Two events here, one to signal stop recording started, and on to signal actual completion of recording
            //Both are necessary since there is sometimes significant lag due to backup in the video / audio buffer
            //processing
            node.addEventListener(STOP_RECORDING_CLICK_EVENT, function (){
                var perf = CiteManager.getContextById(me.props.contextId).currentPerformance.record;
                me.dispatchStatusEvent(node, "Stop recording performance (called): " + perf['uuid'] + " called.", STOP_RECORDING_CALLED_STATUS_EVENT);
                CiteManager.stopRecording(me.props.contextId, function(c){
                    me.dispatchStatusEvent(node, "Stop recording performance (complete): " + c.currentPerformance.record.uuid, STOP_RECORDING_COMPLETE_STATUS_EVENT);
                    me.setState({availableStates: c.availableStates, availablePerformances: c.availablePerformances});
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
                    ReactDOM.findDOMNode(me).dispatchEvent(new Event('contextUpdate', {'bubbles':true, 'cancelable': true}))
                })
            });

            node.addEventListener(STATE_SELECT_START_CLICK_EVENT, function(e){
                CiteManager.startEmulationWithState(me.props.contextId, e.detail, function(context){
                    ReactDOM.findDOMNode(me).dispatchEvent(new Event('contextUpdate', {'bubbles': true, 'cancelable': true}))
                })
            });
        },
        componentWillReceiveProps: function(nextProps){
            var ctx = CiteManager.getContextById(this.props.contextId);
            this.setState({availableStates: ctx.availableStates, availablePerformances: ctx.availablePerformances});
        },
        render: function (){
            return (
                React.createElement('div', {style: emulationComponentStyle},
                    React.createElement(EmulationContainer, {id: this.props.contextId + "_emulationContainer"}),
                    React.createElement(EmulationControls, {
                        started: this.state.startedEmulation,
                        recording: this.state.startedRecording,
                        muted: this.state.muted
                    }),
                    React.createElement('div', {style:{width:"100%"}},
                        React.createElement(Tabs, {},
                            React.createElement(TabList, {},
                                React.createElement(Tab, {}, "Available States"),
                                React.createElement(Tab, {}, "Available Performances")
                            ),
                            React.createElement(TabPanel, {},
                                React.createElement(StateListing, {started: this.state.startedEmulation, availableStates: this.state.availableStates})
                            ),
                            React.createElement(TabPanel, {},
                                React.createElement(PerformanceListing, {availablePerformances: this.state.availablePerformances})
                            )
                        )
                    )
                )
            )
        }
    });

    var EmulationContainer = React.createClass({
        shouldComponentUpdate: function(){
            return false; //this needs to be false, we can't have React destroy the running emulation instance
        },
        render: function (){
            return (
                React.DOM.div({id: this.props.id, style:emulationContainerStyle}, "EmulationContainer")
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
            var me = this;
            return (
                React.DOM.div({style:stateListingStyle},
                    this.props.availableStates.map(function(s){
                        return React.createElement(StateItem, {key:'StateItem_' + s.uuid,record: s, started: me.props.started})
                    })
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
                React.DOM.div({style:stateItemStyle, onClick: this.stateSelectClick},
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
                React.DOM.div({}, this.props.record.description, this.props.record.uuid)
            )
        }
    });
    
    var PerformanceListing = React.createClass({
        displayName: "PerformanceListing",
        render: function (){
            return (
                React.DOM.div({style:performanceListingStyle},
                    this.props.availablePerformances.map(function(s){
                        return React.createElement(PerformanceItem, {key:'PerformanceItem_' + s.uuid, record: s})
                    })
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
                React.DOM.div({onClick: this.perfSelectClick}, this.props.record.title, this.props.record.uuid)
            )
        }
    });

    var Tabs = ReactTabs.Tabs;
    var Tab = ReactTabs.Tab;
    var TabList = ReactTabs.TabList;
    var TabPanel = ReactTabs.TabPanel;

    var TabComponent = React.createClass({
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
            this.setState({currentGameRecord: ctx.currentGame.record,
                currentGameFiles: ctx.currentGame.fileInformation,
                lastSelectedStateRecord: ctx.lastState.record,
                lastSelectedPerfRecord: this.getSelectedPerformance(nextProps.selectedPerformance, ctx.availablePerformances)
            });
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
        render: function(){
            var perfURL = "";
            if(this.state.lastSelectedPerfRecord){
                perfURL = "/cite_data/" + this.state.lastSelectedPerfRecord.replay_source_file_ref + "/" + this.state.lastSelectedPerfRecord.replay_source_file_name;
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
                            React.createElement(InfoTable, {id: this.state.currentGameRecord.uuid, items: this.itemize(this.state.currentGameRecord)}),
                            React.createElement(GameFileListing, {fileInformation: this.state.currentGameFiles})
                        ),
                        React.createElement(TabPanel, {},
                            React.createElement(InfoTable, {id: this.state.lastStateId, items: this.itemize(this.state.lastSelectedStateRecord)})
                        ),
                        React.createElement(TabPanel, {},
                            React.createElement(InfoTable, {id: this.state.lastSelectPerformanceId, items: this.itemize(this.state.lastSelectedPerfRecord)}),
                            React.createElement(PerformanceReview, {performanceVideoURL: perfURL}),
                            React.createElement(UpdateForm, {})
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
        render: function (){
            return (
                React.DOM.video({style:performanceReviewVideoStyle, src: this.props.performanceVideoURL, type:"video/mp4", controls:true})
            );
        }
    });

    var InfoTable = React.createClass({
        render: function (){
            var me = this;
            return (
                React.DOM.ul({}, this.props.items.map(function(i){
                    return React.DOM.li({key: me.props.id + "_" + i[0]}, i[0] + " : " + i[1]);
                }))
            )
        }
    });

    var UpdateForm = React.createClass({
        render: function (){
            return (
                React.DOM.h1({}, "UpdateForm")
            );
        }
    });
    
    var GameFileListing = React.createClass({
        render: function (){
            var fi = this.props.fileInformation;
            var fi_keys;
            try{
                fi_keys = Object.keys(fi);
            }catch(e){
                fi_keys = [];
            }
            return (
                React.DOM.ul({}, fi_keys.map(function(fi_key){
                    var key = fi_key + "_" + fi[fi_key].game_uuid;
                    return React.DOM.li({key:key}, fi_key)
                }))
            );
        }
    });

    return {
        createUI: function(rootDiv, contextId){
            ReactDOM.render(React.createElement(EmulationAnalyzer, {contextId: contextId}), rootDiv)
        }
    }

}());
