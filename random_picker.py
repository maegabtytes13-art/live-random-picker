from flask import Flask, render_template_string, request
from flask_socketio import SocketIO
import random
import eventlet

# Patch sockets for eventlet
eventlet.monkey_patch()

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

# Admin username
ADMIN_USER = "admin"

# Other allowed usernames
ALLOWED_USERS = [
    "Jena", "Rogie", "Robert", "Adeth", "Tart", "Jhoren",
    "Pham", "Bjei", "Jha", "Drin", "Patty", "Maria"
]

# Combine admin with allowed users for validation
ALL_USERS = [ADMIN_USER] + ALLOWED_USERS

# HTML template with shuffle animation, sound, left-aligned assignments and headings, admin reset, and mobile responsiveness
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>GP Online Bunutan</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.1/socket.io.min.js"></script>
    <style>
        body { 
            font-family: Arial; 
            max-width:700px; 
            margin:50px auto; 
            text-align:center; 
            padding: 0 10px; 
            box-sizing: border-box;
        }

        input { 
            width: 100%; 
            padding:10px; 
            margin-bottom:15px; 
            font-size: 1em;
            box-sizing: border-box;
        }

        button { 
            padding:10px 20px; 
            color:white; 
            border:none; 
            cursor:pointer; 
            margin:5px; 
            font-size: 1em;
            border-radius:5px;
        }

        .pick-btn { background-color:#4CAF50; }
        .pick-btn:hover { background-color:#45a049; }
        .reset-btn { background-color:#d9534f; }
        .reset-btn:hover { background-color:#c9302c; }

        #shuffleDisplay { 
            font-size:22px; 
            height:30px; 
            margin-top:20px; 
            color:#333; 
            word-wrap: break-word;
        }

        .assignments { 
            list-style-type: none;  
            padding: 0;              
            text-align: left;        
            margin-top: 25px;
            word-wrap: break-word;
        }

        .left-align { text-align: left; }

        /* Mobile responsive */
        @media (max-width: 480px) {
            body { margin: 20px auto; max-width: 100%; }
            h1 { font-size: 1.5em; }
            h3, h4 { font-size: 1.1em; }
            #shuffleDisplay { font-size: 18px; }
            button { width: 100%; padding: 12px 0; font-size: 1em; margin-bottom: 10px; }
        }
    </style>
</head>
<body>

<h1>GP Online Bunutan 2025</h1>

<input id="username" placeholder="Enter your name">
<button class="pick-btn" onclick="startShuffle()">Pick & Assign</button>
<button class="reset-btn" style="display:none;" onclick="resetAll()">Reset All</button>

<div id="shuffleDisplay"></div>

<h3 class="left-align">Assignments:</h3>
<ul id="assignments" class="assignments"></ul>
<h4 class="left-align">Remaining Items: <span id="remaining"></span></h4>

<script>
const tickSound = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=");
var socket = io();

const ADMIN_USER = "admin";  // Must match app.py
const ALLOWED_USERS = ["Jena","Rogie","Robert","Adeth","Tart","Jhoren","Pham","Bjei","Jha","Drin","Patty","Maria"];

function startShuffle(){
    let username = document.getElementById('username').value.trim();
    if(!username){ alert('Enter a name'); return; }

    // Check allowed users (case-insensitive)
    if(username.toLowerCase() !== ADMIN_USER.toLowerCase() && !ALLOWED_USERS.map(u=>u.toLowerCase()).includes(username.toLowerCase())){
        alert(username + " is not allowed to pick.");
        return;
    }

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

// Show reset button only if current user is admin
document.getElementById('username').addEventListener('input', function(){
    let username = this.value.trim();
    let resetBtn = document.querySelector('.reset-btn');
    if(username.toLowerCase() === ADMIN_USER.toLowerCase()){
        resetBtn.style.display = "inline-block";
    } else {
        resetBtn.style.display = "none";
    }
});

function resetAll(){
    socket.emit('reset');
}

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

socket.on('message', function(msg){ alert(msg); });

socket.on('connect', function(){ socket.emit('connect_request'); });
</script>

</body>
</html>
"""

# Live global state
live_items = PREDEFINED_ITEMS.copy()
live_assignments = {}

@app.route("/")
def index():
    return HTML_PAGE

# SocketIO events
@socketio.on('connect_request')
def handle_connect():
    emit_state()

@socketio.on('get_items')
def handle_get_items(data):
    return live_items

@socketio.on('pick')
def handle_pick(data):
    global live_items, live_assignments
    username = data.get('username','').strip()
    if not username:
        socketio.emit('message', "You must enter a name.", to=request.sid)
        return

    # Check if username is allowed (case-insensitive)
    if username.lower() not in [u.lower() for u in ALL_USERS]:
        socketio.emit('message', f"{username} is not allowed to pick.", to=request.sid)
        return

    # Check if user already picked
    lower_map = {name.lower(): name for name in live_assignments}
    if username.lower() in lower_map:
        orig = lower_map[username.lower()]
        socketio.emit('message', f"{orig} already has: {live_assignments[orig]}", to=request.sid)
        return

    if not live_items:
        socketio.emit('message', "No items remaining!", to=request.sid)
        return

    # Pick item
    selected = random.choice(live_items)
    live_items.remove(selected)
    live_assignments[username] = selected
    emit_state()

@socketio.on('reset')
def handle_reset():
    global live_items, live_assignments
    live_items = PREDEFINED_ITEMS.copy()
    live_assignments = {}
    emit_state()

def emit_state():
    socketio.emit('update', {'assignments': live_assignments, 'items': live_items})

if __name__=="__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
