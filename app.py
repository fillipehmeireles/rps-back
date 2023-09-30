from aiohttp import web
import socketio
from enum import Enum
from dataclasses import dataclass
import json

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)


class Result(Enum):
    Draw = 0
    Win = 1


class Play(Enum):
    ROCK = 0
    PAPER = 1
    SCISSORS = 2


@dataclass
class Player:
    id: str
    play: Play | None
    score: int = 0


@dataclass
class Room:
    id: str
    player_1: Player | None
    player_2: Player | None


rooms: list[Room] = []


def main():

    @sio.event
    def connect(sid, environ):
        print('connect', sid)

    @sio.event
    async def create_room(sid, _):
        new_room = Room(sid,
                        player_1=Player(sid, None), player_2=None)
        sio.enter_room(sid, new_room.id)
        rooms.append(new_room)
        print(f"new_room created by {sid}: {new_room}")

    @sio.event
    async def join_room(sid, game_room):
        room: Room = list(
            map(lambda r: r if r.id == game_room['room_id'] else None, rooms))
        if len(room) == 0:
            await sio.emit('room-not-found', {'msg': 'room not found'}, to=sid)
            return
        room = room[0]
        rooms[rooms.index(room)].player_2 = Player(sid, None)
        sio.enter_room(sid, room.id)
        await sio.emit('player_joined', {'msg': f'user {sid} joined'}, room=room.id)
        print(f'user {sid} joined room {room.id}')

    @sio.event
    def disconnect(sid):
        room: Room = filter(lambda r: r.id == sio.rooms(sid)[0], rooms)[0]
        rooms.remove(room)
        print('disconnect ', sid)

    @sio.event
    async def play(sid, play):
        if not play:
            await sio.emit('player_invalid_play', {'msg': f'please set a valid play'}, to=sid)
            return

        room_id = sio.rooms(sid)[0]
        room: Room = list(
            map(lambda r: r if r.id == room_id else None, rooms))[0]

        (rooms[rooms.index(room)].player_1 if sid == rooms[rooms.index(
            room)].player_1.id else rooms[rooms.index(room)].player_2).play = play['play']
        print(f'player {sid} made its play: {play["play"]}')

        await sio.emit('player_played', {'player_1': json.dumps(rooms[rooms.index(
            room)].player_1.__dict__), 'player_2': json.dumps(rooms[rooms.index(room)].player_2.__dict__)}, room=room.id)

    @sio.event
    async def update_scoreboard(sid, scoreboard):
        room_id = sio.rooms(sid)[0]
        room: Room = list(
            map(lambda r: r if r.id == room_id else None, rooms))[0]
        if Result(scoreboard['result']) == Result.Draw:
            rooms[rooms.index(room)].player_1.score += 1
            rooms[rooms.index(room)].player_2.score += 1
        else:
            (rooms[rooms.index(room)].player_1 if scoreboard['winner_id'] == rooms[rooms.index(
                room)].player_1.id else rooms[rooms.index(room)].player_2).score += 3
        await sio.emit('new_scoreboard', {'player_1_score': json.dumps(rooms[rooms.index(room)].player_1.score), 'player_2_score': json.dumps(rooms[rooms.index(room)].player_1.score)}, room=room.id)


if __name__ == '__main__':
    main()
    web.run_app(app)
