# Reversi.py
"""
1) join playerName
  게임에 참여한다
  ret : a. Black or White, b. Refuse
2) board 
    '0123' 0 : 놓을 수 있는 곳, 1 : white, 2 : black, 3 : 놓을 수 없는 곳
3) put playerName postion
  리버시 position 위치에 돌을 올려놓는다
  ret : success, fail

"""

class Reversi:
    def __init__(self):
        self.board = [0]*64
        self.player = [None]*2

    def runCommand(self, s):
        ss = s.split()
        if ss[0] == "join":
            print(f"{ss[1]}이 게임에 참여합니다.")
            if self.player[0] == None:
                self.player[0] = ss[1]
                ret = "white"
            elif self.player[1] == None:
                self.player[1] = ss[1]
                ret = "black"
            else:
                ret = "refuse"
            return ret
        elif ss[0] == "board":
            ret = "".join(list(map(str, self.board)))
            return ret
        elif ss[0] == "put":
            turn = 0
            if self.player[0] == ss[1]:
                turn = 1
            elif self.player[1] == ss[1]:
                turn = 2
            if turn == 0: return "fail"
            p = int(ss[2])
            self.board[p] = turn
            return "success"
