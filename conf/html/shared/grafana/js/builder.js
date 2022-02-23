/**
 * @author Holger Hees
 * 
 * inspired by https://github.com/wborn/openhab-grafana
 */

"use strict";

var domainParts = document.location.hostname.split('.')
var subDomain = domainParts.shift();
var auth_type = subDomain.substring(0,3);
if( auth_type != 'fa-' && auth_type != 'ba-' ) auth_type = "";
var domain = domainParts.join(".");

var SUBSCRIPTION_URL = "/rest/events?topics=openhab/items/*/statechanged";
var REST_URL = "/rest/items/";

var SMARTHOME_GRAFANA_DEFAULTS = {
    // library
    debug: "false",
    render: "false",
    refresh: "0",
    // ESH sitemap
    sitemap: "default",
    // Grafana URL
    urlPrefix: "//" + auth_type + "grafana." + domain,
    panelPath: "/d-solo/",
    renderPanelPath: "/render/d-solo/",
    // Grafana panel parameters
    from: "now-1d",
    to: "now",
    theme: "dark",
    // Grafana render panel parameters
    width: "auto",
    height: "auto"
};

function resolveParam(params, name)
{
    return params !== undefined && params[name] !== undefined ? params[name] : SMARTHOME_GRAFANA_DEFAULTS[name];
}

function SmartHomeSubscriber(params) 
{
    let p = params;
    let initialized = false;
    let initializedListeners = [];
    let items = {};
    let subscription = {
        id: "",
        page: resolveParam(params, "w"),
        sitemap: resolveParam(params, "sitemap")
    };
    
    function ajax(url,callback) 
    {
        let request = new XMLHttpRequest();

        request.open("GET", url, true);

        request.onload = function() 
        {
            if( request.status < 200 || request.status > 400 )
            {
                return;
            }
            callback(request);
        };
        request.send();

        return request;
    }

    function uninitializedItemNames()
    {
        let result = [];
        for( let itemName in items )
        {
            if( items[itemName].value === undefined )
            {
                result.push(itemName);
            }
        }
        return result;
    }

    function updateInitialized() 
    {
        if( !initialized && uninitializedItemNames().length === 0 )
        {
            initialized = true;
            for( let i = 0; i < initializedListeners.length; i++ )
            {
                initializedListeners[i]();
            }
        }
    }

    function updateItem(itemName, value) 
    {
        if( items[itemName].value === value ) return;

        items[itemName].value = value;

        let itemListeners = items[itemName].listeners;
        for( let i = 0; i < itemListeners.length; i++ )
        {
            let listener = itemListeners[i];
            listener(itemName, value);
        }

        updateInitialized();
    }

    function ChangeListener() 
    {
        let source = new EventSource(SUBSCRIPTION_URL);
        source.addEventListener("message", function(payload) 
        {
            let data = JSON.parse(payload.data);
            
            let itemName = data.topic.substr(14);

            itemName = itemName.substr(0,itemName.indexOf("/"));

            let data_payload = JSON.parse(data.payload);

            if( items[itemName] === undefined ) return;
            
            updateItem(itemName, data_payload.value);
        });
    }

    function ValuesInitializer() 
    {
        function valueHandler(response) 
        {
            let responseJSON;

            try 
            {
                responseJSON = JSON.parse(response.responseText);
            }
            catch( e )
            {
                return;
            }

            updateItem(responseJSON.name, responseJSON.state);
        };

        let itemNames = uninitializedItemNames();
        for( let i = 0; i < itemNames.length; i++ )
        {
            ajax(REST_URL + itemNames[i], valueHandler );
        }

        updateInitialized();
    }

    function initialize() 
    {
        if( subscription.page === undefined ) subscription.page = subscription.sitemap;

        document.addEventListener("DOMContentLoaded", function() {
            subscription.valuesInitializer = new ValuesInitializer();
            subscription.changeListener = new ChangeListener();
        });
    }

    initialize();

    return {
        addItemListener: function(itemName, listener)
        {
            if( items[itemName] !== undefined )
            {
                if( !items[itemName].listeners.includes(listener) )
                {
                    items[itemName].listeners.push(listener);
                }
            }
            else
            {
                items[itemName] = {listeners: [listener], value: undefined};
            }
        },
        addInitializedListener: function(listener) 
        {
            initializedListeners.push(listener);
        },
        isInitialized: function()
        {
            return initialized;
        }
    };
}

var smartHomeSubscriber = new SmartHomeSubscriber();

function GrafanaPanel(params) 
{
    let initialized = false;
    let refreshTimerId = null;
    let resizeTimerId = null;
    let frame = resolveParam(params, "frame");
    let urlPrefix = resolveParam(params, "urlPrefix");
    let panelPath = resolveParam(params, "panelPath");
    let renderPanelPath = resolveParam(params, "renderPanelPath");
    let libVars = {
        debug: {
            value: resolveParam(params, "debug")
        },
        render: {
            value: resolveParam(params, "render")
        },
        refresh: {
            value: resolveParam(params, "refresh")
        }
    };
    let urlVars = {
        dashboard: {
            value: resolveParam(params, "dashboard")
        },
        from: {
            key: "from",
            value: resolveParam(params, "from")
        },
        to: {
            key: "to",
            value: resolveParam(params, "to")
        },
        panel: {
            key: "panelId",
            value: resolveParam(params, "panel")
        },
        theme: {
            key: "theme",
            value: resolveParam(params, "theme")
        },
        width: {
            key: "width",
            value: resolveParam(params, "width")
        },
        height: {
            key: "height",
            value: resolveParam(params, "height")
        }
    };

    function updateFrameSourceURL() 
    {
        var debug = libVars.debug.value;
        var render = libVars.render.value;
        var refresh = libVars.refresh.value;

        var iframe = document.getElementById(frame);
        var idocument = iframe.contentWindow.document;

        var url = urlPrefix;
        url += render === "true" ? renderPanelPath : panelPath;
        url += urlVars.dashboard.value;

        var firstParameter = true;
        for( var uvKey in urlVars ) 
        {
            var key = urlVars[uvKey].key;
            var value = urlVars[uvKey].value;

            if( key === "width" ) 
            {
                value = render === "false" ? undefined : (value === "auto" ? idocument.body.clientWidth : value);
            }
            else if( key === "height" ) 
            {
                value = render === "false" ? undefined : (value === "auto" ? idocument.body.clientHeight : value);
            }

            if( key !== undefined && value !== undefined ) 
            {
                url += (firstParameter ? "?" : "&") + key + "=" + value;
                firstParameter = false;
            }
        }
        
        if( render === "true" ) 
        {
            // append cache busting parameter
            url += "&cacheBuster=" + Date.now();
        }
        // update frame content
        if( debug === "true" )
        {
            idocument.open();
            idocument.write("<a href=\"" + url + "\">" + url + "</a>");
            idocument.close();
        }
        else if( render === "true" )
        {
            var htmlUrl = url.replace(renderPanelPath, panelPath);
            idocument.open();
            idocument.write("<style>body{margin:0px}p{margin:0px}</style>");
            idocument.write("<p style=\"text-align:center;\"><a href=\"" + htmlUrl + "\"><img src=\"" + url + "\"></a></p>");
            idocument.close();
        }
        else if( document.getElementById(frame).src !== url )
        {
            // replace the URL so changes are not added to the browser history
            iframe.contentWindow.location.replace(url);
        }

        if( render === "true" && refresh > 0 ) 
        {
            refreshTimerId = setTimeout(updateFrameSourceURL, refresh);
        }
    }

    function updateFrameOnResize() 
    {
        clearTimeout(resizeTimerId);
        if( libVars.render.value === "true" && ( urlVars.width.value === "auto" || urlVars.height.value === "auto" ) ) 
        {
            resizeTimerId = setTimeout(updateFrameSourceURL, 500);
        } 
    }
    
    function updateVars(vars)
    {
        for( let [key, value] of Object.entries(vars) )
        {
            urlVars[key].value = value;
        }
    }

    return {
        show: function(params)
        {
            if( params ) updateVars(params);
            updateFrameSourceURL();
            if( !initialized && libVars.render.value === "true" && ( urlVars.width.value === "auto" || urlVars.height.value === "auto" ) )
            {
                initialized = true;
                window.addEventListener("resize", updateFrameOnResize);
            }
        },
    }
}

function GrafanaBuilder(panelConfigs) 
{
    var theme = getGrafanaTheme();

    addPreStyle(panelConfigs);
    
    let urlParams = queryParams(window.location);
    let fromItem = "fromItem" in urlParams ? urlParams["fromItem"] : null;
    
    for( var i = 0; i < panelConfigs.length; i++ )
    {
        if( panelConfigs[i].length > 4 )
        {
            let params = { dashboard: panelConfigs[i][1], theme: theme };
            let panel = addGrafanaPanel( panelConfigs[i][0], params );
            smartHomeSubscriber.addItemListener(fromItem,function(item,state)
            {
                //console.log("itemValue");
                
                let fromValue = null;
                let panelId = null;
                switch (state) {
                    case "HOUR": 
                        fromValue = "now-1h";
                        panelId = this[1][0];
                        break;
                    case "DAY":
                        fromValue = "now-1d";
                        panelId = this[1][0];
                        break;
                    case "WEEK":
                        fromValue = "now-1w";
                        panelId = this[1][1];
                        break;
                    case "MONTH":
                        fromValue = "now-1M";
                        panelId = this[1][1];
                        break;
                    case "YEAR":
                        fromValue = "now-1y";
                        panelId = this[1][2];
                        break;
                    case "5YEARS":
                        fromValue = "now-5y";
                        panelId = this[1][2];
                        break;
                }
                
                let params = {};
                params["panel"] = panelId;
                params["from"] = fromValue;
                this[0].show(params);
            }.bind([panel,[ panelConfigs[i][2], panelConfigs[i][3], panelConfigs[i][4] ]]));
            
            /*smartHomeSubscriber.addInitializedListener(function(){
            }.bind([panel,panels]));*/
        }
        else
        {
            let params = { dashboard: panelConfigs[i][1], theme: theme, panel: panelConfigs[i][2] }
            for( let [key, value] of Object.entries(panelConfigs[i][3]) )
            {
                params[key] = value;
            }
            let panel = addGrafanaPanel( panelConfigs[i][0], params );
            panel.show();
        }
    }
    
    function getGrafanaTheme()
    {
        var isPhone = ( navigator.userAgent.indexOf("Android") != -1 && navigator.userAgent.indexOf("Mobile") != -1 );
        return isPhone || parent.document.location.pathname.includes("habpanel") ? 'dark' : 'light';
    }

    function addPreStyle(panelConfigs)
    {
        var cssLink = document.createElement("link");
        cssLink.href = "//" + auth_type + "openhab." + domain + "/static/shared/grafana/css/panel.css"; 
        cssLink.rel = "stylesheet"; 
        cssLink.type = "text/css"; 
        document.head.appendChild(cssLink);
                    
        var style = document.createElement('style');
        style.type = 'text/css';
        style.appendChild(document.createTextNode(".panel-container{ height: " + (100/panelConfigs.length) + "%; }"));
        document.head.appendChild(style);
    }

    function createGuid()
    {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(c) {
            var r = Math.random()*16|0, v = c === "x" ? r : (r&0x3|0x8);
            return v.toString(16);
        });
    }

    function addGrafanaPanel(uniqueId, params) 
    {
        if (uniqueId === undefined) uniqueId = createGuid();

        var div = document.createElement("div");
        div.id = "panel-" + uniqueId + "-container";
        div.className = "panel-container";
        document.body.appendChild(div);

        var frame = document.createElement("iframe");
        frame.id = "panel-" + uniqueId + "-frame";
        frame.className = "panel-frame";
        frame.scrolling = "no";
        frame.onload = function() 
        {
            var cssLink = this.contentWindow.document.createElement("link");
            cssLink.href = "//" + auth_type + "openhab." + domain + "/static/shared/grafana/css/grafana.css"; 
            cssLink.rel = "stylesheet"; 
            cssLink.type = "text/css"; 
            this.contentWindow.document.head.appendChild(cssLink);
        };
        div.appendChild(frame);

        params["frame"] = frame.id;
        return new GrafanaPanel(params);
    }
    
    function queryParams(param) 
    {
        if( !param )  return {};

        let match = null;
        let url = param.toString();
        let queryIndex = url.indexOf("?");
        let query = queryIndex !== -1 ? url.substring(queryIndex + 1) : "";
        let re = /([^&=]+)=?([^&]*)/g;
        let decode = function (s) { return decodeURIComponent(s.replace(/\+/g, " ")); };
        let result = {};

        do 
        {
            match = re.exec(query);
            if( match ) 
            {
                result[decode(match[1])] = decode(match[2]);
            }
        } 
        while( match );

        return result;
    }
}
