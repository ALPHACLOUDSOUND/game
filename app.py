import os
import random
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # Automatically generated secret key
socketio = SocketIO(app)

# Game state
games = {}
players = {}
team_captains = {}

def create_game():
    return {
        'team_a': [],
        'team_b': [],
        'score_a': 0,
        'score_b': 0,
        'current_batting': 'A',
        'current_bowler': None,
        'current_batsman': None,
        'overs': 0,
        'balls': 0,
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create():
    game_id = request.form.get('game_id')
    player_name = request.form.get('player_name')
    session['player_name'] = player_name
    session['game_id'] = game_id
    if game_id not in games:
        games[game_id] = create_game()
        players[game_id] = []
    players[game_id].append(player_name)
    return redirect(url_for('game'))

@app.route('/game')
def game():
    if 'player_name' not in session or 'game_id' not in session:
        return redirect(url_for('index'))
    return render_template('game.html', player_name=session['player_name'], game_id=session['game_id'])

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_game')
def join_game(data):
    game_id = data['game_id']
    player_name = data['player_name']
    join_room(game_id)
    emit('player_joined', {'player_name': player_name, 'game_id': game_id}, room=game_id)
    if len(players[game_id]) >= 2 and game_id not in team_captains:
        team_captains[game_id] = random.sample(players[game_id], 2)
        emit('captains_selected', {'team_captains': team_captains[game_id]}, room=game_id)

@socketio.on('start_game')
def start_game(data):
    game_id = data['game_id']
    if game_id in team_captains and data['player_name'] in team_captains[game_id]:
        emit('game_started', {'game_id': game_id}, room=game_id)

@socketio.on('play_ball')
def play_ball(data):
    game_id = data['game_id']
    player_name = data['player_name']
    game = games[game_id]
    outcome = random.choice(['0', '1', '2', '3', '4', '6', 'W'])  # Simplified outcomes
    if outcome == 'W':
        game['current_batsman'] = random.choice(game['team_a'] if game['current_batting'] == 'A' else game['team_b'])
        emit('wicket', {'player_name': player_name, 'game_id': game_id}, room=game_id)
    else:
        if game['current_batting'] == 'A':
            game['score_a'] += int(outcome)
        else:
            game['score_b'] += int(outcome)
        emit('ball_played', {'player_name': player_name, 'runs': outcome, 'game_id': game_id}, room=game_id)
    
    game['balls'] += 1
    if game['balls'] == 6:
        game['balls'] = 0
        game['overs'] += 1
        emit('over', {'game_id': game_id, 'overs': game['overs']}, room=game_id)
    
    if game['overs'] == 20:  # End game after 20 overs for simplicity
        emit('game_over', {'score_a': game['score_a'], 'score_b': game['score_b']}, room=game_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)
