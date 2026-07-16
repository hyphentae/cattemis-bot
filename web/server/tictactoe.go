package main

import (
	"crypto/rand"
	"errors"
	"sync"
	"time"
)

type ticTacToeRoom struct {
	Code                 string
	Board                [9]string
	X                    player
	O                    *player
	Public               bool
	Turn, Status, Winner string
	Version              int64
	UpdatedAt            time.Time
}
type ticTacToeView struct {
	Code    string    `json:"code"`
	Board   [9]string `json:"board"`
	X       player    `json:"x"`
	O       *player   `json:"o,omitempty"`
	Public  bool      `json:"public"`
	Turn    string    `json:"turn"`
	Status  string    `json:"status"`
	Winner  string    `json:"winner,omitempty"`
	You     string    `json:"you"`
	Version int64     `json:"version"`
}
type ticTacToeManager struct {
	mu    sync.Mutex
	rooms map[string]*ticTacToeRoom
}

func newTicTacToeManager() *ticTacToeManager {
	return &ticTacToeManager{rooms: make(map[string]*ticTacToeRoom)}
}

func (m *ticTacToeManager) create(user telegramUser) (ticTacToeView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	code, err := m.code()
	if err != nil {
		return ticTacToeView{}, err
	}
	r := &ticTacToeRoom{Code: code, X: player{ID: user.ID, Name: user.displayName()}, Turn: "x", Status: "waiting", Version: 1, UpdatedAt: time.Now()}
	m.rooms[code] = r
	return tttView(r, user.ID), nil
}
func (m *ticTacToeManager) public(user telegramUser) (ticTacToeView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, r := range m.rooms {
		if r.Public && r.Status == "waiting" {
			if r.X.ID == user.ID {
				return tttView(r, user.ID), nil
			}
			r.O = &player{ID: user.ID, Name: user.displayName()}
			r.Status = "active"
			r.Version++
			return tttView(r, user.ID), nil
		}
	}
	code, err := m.code()
	if err != nil {
		return ticTacToeView{}, err
	}
	r := &ticTacToeRoom{Code: code, X: player{ID: user.ID, Name: user.displayName()}, Public: true, Turn: "x", Status: "waiting", Version: 1, UpdatedAt: time.Now()}
	m.rooms[code] = r
	return tttView(r, user.ID), nil
}
func (m *ticTacToeManager) join(code string, user telegramUser) (ticTacToeView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return ticTacToeView{}, errRoomNotFound
	}
	if r.X.ID == user.ID {
		return tttView(r, user.ID), nil
	}
	if r.O != nil && r.O.ID != user.ID {
		return ticTacToeView{}, errRoomFull
	}
	if r.O == nil {
		r.O = &player{ID: user.ID, Name: user.displayName()}
		r.Status = "active"
		r.Version++
	}
	return tttView(r, user.ID), nil
}
func (m *ticTacToeManager) state(code string, id int64) (ticTacToeView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return ticTacToeView{}, errRoomNotFound
	}
	if tttSide(r, id) == "" {
		return ticTacToeView{}, errNotPlayer
	}
	return tttView(r, id), nil
}
func (m *ticTacToeManager) move(code string, id int64, index int) (ticTacToeView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return ticTacToeView{}, errRoomNotFound
	}
	side := tttSide(r, id)
	if side == "" {
		return ticTacToeView{}, errNotPlayer
	}
	if r.Status != "active" || r.Turn != side {
		return ticTacToeView{}, errNotYourTurn
	}
	if index < 0 || index > 8 || r.Board[index] != "" {
		return ticTacToeView{}, errInvalidMove
	}
	r.Board[index] = side
	r.Version++
	if winner := tttWinner(r.Board); winner != "" {
		r.Status = "finished"
		r.Winner = winner
	} else if side == "x" {
		r.Turn = "o"
	} else {
		r.Turn = "x"
	}
	return tttView(r, id), nil
}
func tttWinner(b [9]string) string {
	for _, l := range [][3]int{{0, 1, 2}, {3, 4, 5}, {6, 7, 8}, {0, 3, 6}, {1, 4, 7}, {2, 5, 8}, {0, 4, 8}, {2, 4, 6}} {
		if b[l[0]] != "" && b[l[0]] == b[l[1]] && b[l[1]] == b[l[2]] {
			return b[l[0]]
		}
	}
	for _, v := range b {
		if v == "" {
			return ""
		}
	}
	return "draw"
}
func tttSide(r *ticTacToeRoom, id int64) string {
	if r.X.ID == id {
		return "x"
	}
	if r.O != nil && r.O.ID == id {
		return "o"
	}
	return ""
}
func tttView(r *ticTacToeRoom, id int64) ticTacToeView {
	return ticTacToeView{Code: r.Code, Board: r.Board, X: r.X, O: r.O, Public: r.Public, Turn: r.Turn, Status: r.Status, Winner: r.Winner, You: tttSide(r, id), Version: r.Version}
}
func (m *ticTacToeManager) code() (string, error) {
	const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	for n := 0; n < 20; n++ {
		b := make([]byte, 6)
		if _, err := rand.Read(b); err != nil {
			return "", err
		}
		for i := range b {
			b[i] = chars[int(b[i])%len(chars)]
		}
		if m.rooms[string(b)] == nil {
			return string(b), nil
		}
	}
	return "", errors.New("не удалось создать комнату")
}
