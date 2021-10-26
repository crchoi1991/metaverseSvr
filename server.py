import socket   # Network connection을 위한 디스크립터
import select   # Network event 선택자
import time     # 시간 관련된 내용
import math     # math module
import os.path  # file 또는 directory 검사용

class Server:
    TimeTick = 5.0      # 하나의 틱 길이 (초단위)
    
    # Constructor
    def __init__(self, port):
        self.port = port
        self.running = False

        # 사용자 프로파일
        self.users = dict()

    # Start server
    def start(self, worldData):
        # Save world data and load world
        self.worldData = worldData
        self.loadWorld()
        
        # Create a socket for listen
        self.listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind address to listen socket
        self.listenSock.bind(('', self.port))

        # Listen socket
        self.listenSock.listen(5)

        # Connected client sockets
        self.reads = [self.listenSock]

        # time tick 설정을 위해서 현재 시간을 제거합니다.
        self.timeOffset = -time.time()
        self.curTick = 0
        
        # Infinite loop
        self.running = True
        while self.running:
            self.select()

        print("Shutdown")
        self.listenSock.close()

    # Load world
    def loadWorld(self):
        for k in self.worldData:
            if os.path.isfile(f"{k}.py"):
                wd = self.worldData[k]
                pyMod = __import__(k)
                wd[3] = getattr(pyMod, k)()
                
    def getTick(self):
        return int((time.time() + self.timeOffset)/Server.TimeTick)

    # on connect
    def onConnect(self, sock):
        # 요청이 온 클라이언트에 대하여 접속 수락
        client, addr = sock.accept()
        print(f"Connected from {addr}")
        self.reads.append(client)

    # on close
    def onClose(self, sock):
        self.reads.remove(sock)
        del self.users[sock]

    # on packet
    def onPacket(self, sock, sdata):
        ss = sdata.split()
        if ss[0] == "join":
            # ss[1] 은 이름
            # 이미 접속해있는 다른 유저의 이동 정보를 받아야한다.
            for k in self.users:
                u = self.users[k]
                mesg = f"move {u['name']} {u['pos']} {u['dir']} {u['speed']}"
                self.send(sock, mesg.encode())
            self.users[sock] = {
                "name" : ss[1],
                "pos" : (0, 0),
                "dir" : 0,
                "speed" : 0,
                "aspeed" : 0
            }
            u = self.users[sock]
            mesg = f"move {u['name']} {u['pos']} {u['dir']} {u['speed']}"
            self.broadcast(mesg.encode())
            # 월드 데이터를 보낸다.
            for k in self.worldData:
                wd = self.worldData[k]
                mesg = f"worlddata {k} {wd[0]} {wd[1]} {wd[2]}"
                self.send(sock, mesg.encode())
            return
        if sock not in self.users:
            print("Error : Unknown user message")
            return
        user = self.users[sock]
        if ss[0] == "shutdown":
            self.running = False
        elif ss[0] == "move":
            user['pos'] = (float(ss[2]), float(ss[3]))
            user['direction'] = float(ss[4])
            user['speed'] = float(ss[5])
            user['aspeed'] = float(ss[6])
        elif ss[0] == "turn":
            user['aspeed'] = int(ss[1])
        elif ss[0] == "world":
            mesg = f"world {len(self.worldData)}"
            self.send(sock, mesg.encode())
        elif ss[0] == "worlddata":
            idx = int(ss[1])
            key = list(self.worldData.keys())[idx]
            wd = self.worldData[key]
            mesg = f"worlddata {key} {wd[0]} {wd[1]} {wd[2]}"
            self.send(sock, mesg.encode())
        elif ss[0] == "action":
            if ss[1] not in self.worldData:
                mesg = f"error {ss[1]} is not world object"
                self.send(sock, mesg.encode())
                return
            obj = self.worldData[ss[1]][3]
            if len(ss) == 2:
                ret = obj.runCommand(f"join {user['name']}")
                print(ret)
            elif len(ss) == 3:
                ret = obj.runCommand(f"put {user['name']} {ss[2]}")
                print(ret)
            self.send(sock, ret.encode())
        elif ss[0] == "avatar":
            user['avatar'] = int(ss[2])
        elif ss[0] == "look":
            user['look'] = tuple(map(int, ss[2:]))
        self.broadcast(sdata.encode())

    # on recv
    def onRecv(self, sock):
        # 클라이언트로부터 온 데이터를 수신한다.
        try:
            data = sock.recv(4)
            if data == None or len(data) <= 0:
                print("closed by peer")
                self.onClose(sock)
                return
        except socket.error:
            print("socket error")
            self.onClose(sock)
            return
        needed = int(data.decode())
        try:
            data = sock.recv(needed)
            if data == None or len(data) <= 0:
                print("closed by peer")
                self.onClose(sock)
                return
        except socket.error:
            print("socket error")
            self.onClose(sock)
            return
        sdata = data.decode()
        print(sdata)
        self.onPacket(sock, sdata)
        return

        
    def onIdle(self):
        #print(f"onIdle({self.curTick})")
        # 유저들 위치 이동
        for k in self.users:
            u = self.users[k]
            # 유저의 속도와 각속도가 모두 0이면 무시
            if u['speed'] == 0 and u['aspeed'] == 0: continue
            u['dir'] = u['dir'] + u['aspeed'] * Server.TimeTick
            # 각도를 라디안으로 변경
            theta = u['dir'] * math.pi / 180
            x = u['pos'][0] + u['speed'] * math.cos(theta) * Server.TimeTick
            y = u['pos'][1] + u['speed'] * math.sin(theta) * Server.TimeTick
            u['pos'] = (x, y)
            mesg = f"/move {self.curTick} {u['name']} {u['pos']} {u['dir']} {u['speed']}"
            self.broadcast(mesg.encode())
        for k in self.worldData:
            wd = self.worldData[k]
            if wd[3] == None: continue
            ret = wd[3].runCommand("board")
            mesg = f"{k} {ret}"
            #print(mesg)
            self.broadcast(mesg.encode())

    # Select
    def select(self):
        reads, _, _ = select.select(self.reads, [], [], Server.TimeTick/2)

        # for every socket events
        for s in reads:
            # if s is listen socket
            if s == self.listenSock: self.onConnect(s)
            # if s is not listen socket
            else: self.onRecv(s)

        # time tick이 현재 있는지 검사
        ctick = self.getTick()
        if self.curTick < ctick:
            self.onIdle()
            self.curTick += 1

    # Send
    def send(self, sock, data):
        packet = ("%04d"%len(data)).encode()+data
        sock.send(packet)
                
    # Broadcast
    def broadcast(self, data):
        for s in self.users:
            self.send(s, data)

server = Server(8888)
worldData = dict()
with open("world.txt") as f:
    while True:
        line = f.readline()
        if line == None: break
        ss = line.split()
        if len(ss) < 4: break
        worldData[ss[0]] = [ float(ss[1]), float(ss[2]), float(ss[3]), None ]
for k in worldData:
    print(k, worldData[k])
server.start(worldData)


                