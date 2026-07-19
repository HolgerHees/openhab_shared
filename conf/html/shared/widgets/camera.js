var mvCamera = (function( ret ) {
    let isFullscreen = false;
    let states = {};

    function refreshCameraImage(key)
    {
        states[key]['image'].src = states[key]['imageUrl'] + '&time=' + new Date().getTime();
        window.setTimeout(function(){
          if( !states[key]['active'] ) return;
          refreshCameraImage(key)
        }, 3000);
    }

    function togglePopup(key)
    {
        if( isFullscreen )
        {
          isFullscreen = false;

          for (let key of Object.keys(states)) {
            states[key]["active"] = true;
            refreshCameraImage(key);
          }

          let containerElement = states[key]['container'];

          states[key]['image'].style.display="";
          states[key]['handler'].cleanup();
          containerElement.removeChild(states[key]['video']);

          containerElement.style.inset = containerElement.dataset.inset;
          containerElement.style.backgroundColor = "";
          window.setTimeout(function(){
              containerElement.style.inset = "";
              containerElement.classList.remove("cameraPopup");
          },500);
        }
        else {
          isFullscreen = true;

          for (let key of Object.keys(states)) {
            states[key]["active"] = false;
          }

          let imageElement = states[key]['image'];
          let containerElement = states[key]['container'];

          var rect = containerElement.getBoundingClientRect()
          var right = window.innerWidth - rect["left"] - rect["width"];
          var bottom = window.innerHeight - rect["top"] - rect["height"];

          containerElement.classList.add("cameraPopup");

          containerElement.dataset.inset = rect["top"] + "px " + right + "px " + bottom + "px " + rect["left"] + "px";

          containerElement.classList.add("cameraPopup");
          containerElement.style.inset = containerElement.dataset.inset;

          window.setTimeout(function(){
              containerElement.style.inset = "0 0 0 0";
              containerElement.style.backgroundColor = "rgba(0,0,0,0.9)";
          },50);

          videoElement = states[key]['video'] = document.createElement("video");
          videoElement.setAttribute("style", "display:none;max-height:100%;max-width:100%;width:100%;height:100%;object-fit:contain;");
          containerElement.appendChild(videoElement);
          window.setTimeout(function(){
              if( !isFullscreen ) return;
              videoElement.addEventListener("loadeddata", function() {
                  if( !isFullscreen ) return;
                  videoElement.style.display="";
                  imageElement.style.display="none";
              });
              states[key]['handler'] = mvVideo.build(videoElement, states[key]['streamUrl']);
          },0);

          //videoElement.addEventListener("click",function(){togglePopup(key);});
        }
    }

    ret.build = function(event, imageUrl, streamUrl)
    {
        let key = imageUrl;
        states[key] = {'image':  event.target, 'container': event.target.parentNode, 'video': null, 'handler': null, 'imageUrl': imageUrl, 'streamUrl': streamUrl, 'active': true}
        states[key]['image'].onload = null;
        refreshCameraImage(key)

        states[key]['container'].addEventListener("click",function(){togglePopup(key);});
    }
    return ret;
})({});
