from flask import Flask, render_template_string, session
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
socketio = SocketIO(app, manage_session=False)

# Predefined items
PREDEFINED_ITEMS = [
    "Something shiny",
    "Something soft",
    "Something eco-friendly",
    "Something edible",
    "Something for facial care",
    "Something red",
    "Something green",
    "Something long",
    "Something useful in the kitchen",
    "Something you can drink",
    "Something for pain relief",
    "Something for foot care"
]

# HTML page with shuffle animation + sound
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Random Picker Live</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.1/socket.io.min.js"></script>
    <style>
        body { font-family: Arial; max-width:700px; margin:50px auto; text-align:center; }
        input { width:100%; padding:10px; margin-bottom:15px; }
        button { padding:10px 20px; color:white; border:none; cursor:pointer; margin:5px; }
        .pick-btn { background-color:#4CAF50; }
        .pick-btn:hover { background-color:#45a049; }
        .reset-btn { background-color:#d9534f; }
        .reset-btn:hover { background-color:#c9302c; }
        #shuffleDisplay { font-size:22px; height:30px; margin-top:20px; color:#333; }
        .assignments { text-align:left; margin-top:25px; }
    </style>
</head>
<body>

<h1>Random Picker (Live)</h1>

<input id="username" placeholder="Enter your name">
<button class="pick-btn" onclick="startShuffle()">Pick & Assign</button>
<button class="reset-btn" onclick="resetAll()">Reset All</button>

<div id="shuffleDisplay"></div>

<h3>Assignments:</h3>
<ul id="assignments"></ul>
<h4>Remaining Items: <span id="remaining"></span></h4>

<script>
// Base64 small tick sound
const tickSound = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=");
var socket = io();

// Shuffle animation + sound + pick
function startShuffle(){
    let username = document.getElementById('username').value.trim();
    if(!username){ alert('Enter a name'); return; }

    socket.emit('get_items', {}, function(items){
        if(items.length===0){ alert('No items remaining!'); return; }

        let display = document.getElementById('shuffleDisplay');
        let index=0;
        let shuffleInterval = setInterval(()=>{
            display.innerHTML = items[index % items.length];
            index++;
            tickSound.currentTime=0; tickSound.play();
        }, 100);

        setTimeout(()=>{
            clearInterval(shuffleInterval);
            display.innerHTML="";
            socket.emit('pick', {username: username});
        }, 3000);
    });
}

function resetAll(){
    socket.emit('reset');
}

// Update assignments live
socket.on('update', function(data){
    let list = document.getElementById('assignments');
    list.innerHTML='';
    for(let user in data.assignments){
        let li = document.createElement('li');
        li.innerText = user + ': ' + data.assignments[user];
        list.appendChild(li);
    }
    document.getElementById('remaining').innerText = data.items.length;
});

// Alert pick messages
socket.on('message', function(msg){ alert(msg); });

// Request current state on connect
socket.on('connect', function(){ socket.emit('connect_request'); });
</script>

</body>
</html>
"""

# Global live state
live_items = PREDEFINED_ITEMS.copy()
live_assignments = {}

# Flask route
@app.route("/")
def index():
    return HTML_PAGE

# SocketIO events
@socketio.on('connect_request')
def handle_connect():
    emit('update', {'assignments': live_assignments, 'items': live_items})

@socketio.on('get_items')
def handle_get_items(data):
    emit('get_items_response', live_items, callback=request.sid)
    return live_items

@socketio.on('pick')
def handle_pick(data):
    global live_items, live_assignments
    username = data.get('username','').strip()
    lower_map = {name.lower(): name for name in live_assignments}

    if not username:
        emit('message', "You must enter a name.", to=request.sid)
        return

    if username.lower() in lower_map:
        orig = lower_map[username.lower()]
        emit('message', f"{orig} already has: {live_assignments[orig]}", to=request.sid)
        return

    if not live_items:
        emit('message', "No items remaining!", to=request.sid)
        return

    selected = random.choice(live_items)
    live_items.remove(selected)
    live_assignments[username] = selected

    # Broadcast to all clients
    socketio.emit('update', {'assignments': live_assignments, 'items': live_items})

@socketio.on('reset')
def handle_reset():
    global live_items, live_assignments
    live_items = PREDEFINED_ITEMS.copy()
    live_assignments = {}
    socketio.emit('update', {'assignments': live_assignments, 'items': live_items})

if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=5000)