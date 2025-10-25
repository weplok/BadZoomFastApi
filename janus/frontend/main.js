/*
 Minimal Janus VideoRoom client (PoC)
 - Connects to Janus via WebSocket at ws://localhost:8188 (adjust if necessary)
 - Joins room 1234. Creates room if not exists.
 - Publishes local stream and subscribes to remote feeds.
 - Very lightweight; intended for quick PoC/night work.
 Note: This code is adapted/simplified from Janus demo examples.
*/

let janus = null;
let sfutest = null;
let opaqueId = "janus-poc-" + Janus.randomString(12);

const server = (location.protocol === 'https:' ? "wss" : "ws") + "://" + window.location.hostname + ":8188/"; // adjust if needed
console.log("Janus server:", server);

const joinBtn = document.getElementById("joinBtn");
const toggleVideo = document.getElementById("toggleVideo");
const toggleAudio = document.getElementById("toggleAudio");
const statusSpan = document.getElementById("status");
const videos = document.getElementById("videos");

let myStream = null;
let myId = null;
let myRoom = 1234;
let publishing = false;
let videoEnabled = false;
let audioEnabled = false;
let feeds = {}; // remote feeds by feed id

function addVideoElement(id, display, isLocal=false) {
  let container = document.createElement("div");
  container.id = "feed-"+id;
  if (isLocal) {
    let v = document.createElement("video");
    v.autoplay = true; v.muted = true; v.playsInline = true;
    v.id = "localvideo";
    container.appendChild(v);
  } else {
    let v = document.createElement("video");
    v.autoplay = true; v.id = "remote-"+id; v.playsInline = true;
    container.appendChild(v);
  }
  videos.appendChild(container);
  return container;
}

function removeVideoElement(id) {
  let el = document.getElementById("feed-"+id);
  if (el) el.remove();
}

function updateStatus(s) { statusSpan.textContent = s; }

function initJanus() {
  Janus.init({
    debug: "all",
    callback: function() {
      janus = new Janus({
        server: server,
        success: function() {
          janus.attach({
            plugin: "janus.plugin.videoroom",
            opaqueId: opaqueId,
            success: function(pluginHandle) {
              sfutest = pluginHandle;
              console.log("Plugin attached! (" + sfutest.getPlugin() + ", id=" + sfutest.getId() + ")");
              updateStatus("Ready (not in room)");
            },
            error: function(error) {
              console.error("  -- Error attaching plugin...", error);
              updateStatus("Error attaching plugin");
            },
            consentDialog: function(on) {
              console.log("consentDialog", on);
            },
            onmessage: function(msg, jsep) {
              Janus.debug(" ::: Got a message :::");
              Janus.debug(msg);
              let event = msg["videoroom"];
              if (event) {
                if (event === "joined") {
                  myId = msg["id"];
                  updateStatus("Joined room " + msg["room"] + " as publisher (id=" + myId + ")");
                  // Publish our stream
                  publishOwnFeed();
                  // If there are publishers, subscribe to them
                  if (msg["publishers"]) {
                    let list = msg["publishers"];
                    for (let f of list) {
                      newRemoteFeed(f["id"], f["display"]);
                    }
                  }
                } else if (event === "event") {
                  if (msg["publishers"]) {
                    let list = msg["publishers"];
                    for (let f of list) {
                      newRemoteFeed(f["id"], f["display"]);
                    }
                  } else if (msg["leaving"]) {
                    let leaving = msg["leaving"];
                    updateStatus("Participant left: " + leaving);
                    removeVideoElement(leaving);
                    delete feeds[leaving];
                  } else if (msg["unpublished"]) {
                    let unpublished = msg["unpublished"];
                    if (unpublished === 'ok') {
                      // That's us
                      sfutest.hangup();
                      return;
                    }
                    updateStatus("Remote feed unpublished: " + unpublished);
                    removeVideoElement(unpublished);
                    delete feeds[unpublished];
                  }
                }
              }
              if (jsep) {
                Janus.debug("Handling SDP as well...");
                Janus.debug(jsep);
                sfutest.handleRemoteJsep({ jsep: jsep });
              }
            },
            onlocalstream: function(stream) {
              Janus.debug(" ::: Got a local stream :::");
              myStream = stream;
              // attach to <video>
              let el = document.getElementById("localvideo");
              if (!el) addVideoElement(myId || "local", "Me", true);
              el = document.getElementById("localvideo");
              Janus.attachMediaStream(el, stream);
            },
            onremotestream: function(stream) {
              // The plugin will not use this for subscribers; remote streams are attached in subscriber handle
            },
            oncleanup: function() {
              Janus.log(" ::: Got a cleanup notification :::");
            }
          });
        },
        error: function(error) {
          Janus.error(error);
          updateStatus("Janus error: " + error);
        },
        destroyed: function() {
          window.location.reload();
        }
      });
    }
  });
}

function createRoomIfNeeded(callback) {
  // Try to create a room with id myRoom (ignore error if exists)
  let create = { request: "create", room: myRoom, publishers: 50, bitrate: 512000 };
  sfutest.send({ message: create, success: function(result) {
    console.log("Room create result:", result);
    if (callback) callback();
  }, error: function(err) {
    console.warn("Create room error (maybe exists):", err);
    if (callback) callback();
  }});
}

function joinRoom() {
  if (!sfutest) { updateStatus("Janus not ready"); return; }
  createRoomIfNeeded(function() {
    let register = { request: "join", room: myRoom, ptype: "publisher", display: "User-" + Janus.randomString(4) };
    sfutest.send({ message: register });
    updateStatus("Joining room " + myRoom + "...");
  });
}

function publishOwnFeed() {
  // Get user media constraints based on toggles
  let constraints = { audio: audioEnabled, video: videoEnabled ? { width: { ideal: 640 }, height: { ideal: 360 } } : false };
  sfutest.createOffer({
    media: constraints,
    success: function(jsep) {
      Janus.debug("Got publisher SDP!", jsep);
      let publish = { request: "configure", audio: audioEnabled, video: videoEnabled };
      sfutest.send({ message: publish, jsep: jsep });
      publishing = true;
      updateStatus("Publishing (video="+videoEnabled+", audio="+audioEnabled+")");
      // Ensure local video element exists
      let v = document.getElementById("localvideo");
      if (!v) addVideoElement("local", "Me", true);
    },
    error: function(error) {
      Janus.error("WebRTC error:", error);
      updateStatus("WebRTC error: " + error);
      if (Janus.webRTCAdapter.browserDetails.browser === "safari") {
        alert("Error: " + error);
      }
    }
  });
}

function newRemoteFeed(id, display) {
  // Attach to new remote feed
  let remoteFeed = null;
  janus.attach({
    plugin: "janus.plugin.videoroom",
    success: function(pluginHandle) {
      remoteFeed = pluginHandle;
      const subscribe = { request: "join", room: myRoom, ptype: "subscriber", feed: id };
      remoteFeed.send({ message: subscribe });
    },
    error: function(err) {
      Janus.error("Error attaching plugin for remote feed", err);
      return;
    },
    onmessage: function(msg, jsep) {
      let event = msg["videoroom"];
      if (event === "attached") {
        feeds[id] = remoteFeed;
        updateStatus("Attached to feed " + id + " (" + display + ")");
        // create placeholder
        addVideoElement(id, display, false);
      }
      if (jsep) {
        remoteFeed.createAnswer({
          jsep: jsep,
          media: { audio: true, video: true },
          success: function(jsep) {
            let body = { request: "start", room: myRoom };
            remoteFeed.send({ message: body, jsep: jsep });
          },
          error: function(err) {
            Janus.error("WebRTC error (remote):", err);
            updateStatus("WebRTC error (remote): " + err);
          }
        });
      }
    },
    onlocalstream: function(stream) { /* not used for subscribers */ },
    onremotestream: function(stream) {
      Janus.attachMediaStream(document.getElementById("remote-" + id), stream);
    },
    oncleanup: function() {
      removeVideoElement(id);
    }
  });
}

// UI handlers
joinBtn.addEventListener("click", function() {
  if (!janus) initJanus();
  setTimeout(() => joinRoom(), 500); // small delay to ensure plugin attached
});

toggleVideo.addEventListener("click", function() {
  videoEnabled = !videoEnabled;
  toggleVideo.textContent = videoEnabled ? "Video ON" : "Video OFF";
  toggleVideo.classList.toggle("toggled", !videoEnabled);
  if (publishing) {
    // reconfigure
    let update = { request: "configure", audio: audioEnabled, video: videoEnabled };
    sfutest.send({ message: update });
  }
});

toggleAudio.addEventListener("click", function() {
  audioEnabled = !audioEnabled;
  toggleAudio.textContent = audioEnabled ? "Audio ON" : "Audio OFF";
  toggleAudio.classList.toggle("toggled", !audioEnabled);
  if (publishing) {
    let update = { request: "configure", audio: audioEnabled, video: videoEnabled };
    sfutest.send({ message: update });
  }
});
