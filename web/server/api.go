package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"strconv"
	"time"
)

type server struct {
	botToken string
	rooms    *roomManager
	chess    *chessRoomManager
	canvas   *canvasManager
	ttt      *ticTacToeManager
	leaders  *leaderboardManager
}

func newServer(botToken string) *server {
	canvasPath := os.Getenv("CANVAS_PATH")
	if canvasPath == "" {
		canvasPath = "/data/canvas.json"
	}
	leaderboardPath := os.Getenv("LEADERBOARD_PATH")
	if leaderboardPath == "" {
		leaderboardPath = "/data/leaderboard.json"
	}
	return &server{
		botToken: botToken, rooms: newRoomManager(), chess: newChessRoomManager(),
		canvas: newCanvasManager(canvasPath),
		ttt:    newTicTacToeManager(),
		leaders: newLeaderboardManager(leaderboardPath),
	}
}

func (s *server) leaderboard(w http.ResponseWriter, r *http.Request) {
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	if r.Method == http.MethodGet {
		view, err := s.leaders.view(r.URL.Query().Get("game"), r.URL.Query().Get("difficulty"))
		if err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, view)
		return
	}
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	var request struct {
		Game       string `json:"game"`
		Difficulty string `json:"difficulty"`
		Seconds    int    `json:"seconds"`
		Mistakes   int    `json:"mistakes"`
	}
	if !decodeJSON(w, r, &request) {
		return
	}
	view, err := s.leaders.submit(user, request.Game, request.Difficulty, request.Seconds, request.Mistakes)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, view)
}

func (s *server) createTTTRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, 405, "метод не поддерживается")
		return
	}
	u, ok := s.authorize(w, r)
	if !ok {
		return
	}
	v, e := s.ttt.create(u)
	writeTTTResult(w, v, e)
}
func (s *server) publicTTTRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, 405, "метод не поддерживается")
		return
	}
	u, ok := s.authorize(w, r)
	if !ok {
		return
	}
	v, e := s.ttt.public(u)
	writeTTTResult(w, v, e)
}
func (s *server) joinTTTRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, 405, "метод не поддерживается")
		return
	}
	u, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var q struct {
		Code string `json:"code"`
	}
	if !decodeJSON(w, r, &q) {
		return
	}
	v, e := s.ttt.join(q.Code, u)
	writeTTTResult(w, v, e)
}
func (s *server) tttState(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, 405, "метод не поддерживается")
		return
	}
	u, ok := s.authorize(w, r)
	if !ok {
		return
	}
	v, e := s.ttt.state(r.URL.Query().Get("code"), u.ID)
	writeTTTResult(w, v, e)
}
func (s *server) tttMove(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, 405, "метод не поддерживается")
		return
	}
	u, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var q struct {
		Code  string `json:"code"`
		Index int    `json:"index"`
	}
	if !decodeJSON(w, r, &q) {
		return
	}
	v, e := s.ttt.move(q.Code, u.ID, q.Index)
	writeTTTResult(w, v, e)
}
func writeTTTResult(w http.ResponseWriter, v ticTacToeView, e error) {
	if e == nil {
		writeJSON(w, 200, v)
		return
	}
	status := 400
	if errors.Is(e, errRoomNotFound) {
		status = 404
	}
	if errors.Is(e, errNotPlayer) {
		status = 403
	}
	if errors.Is(e, errNotYourTurn) || errors.Is(e, errRoomFull) {
		status = 409
	}
	writeError(w, status, e.Error())
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) canvasState(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	since, _ := strconv.ParseInt(r.URL.Query().Get("since"), 10, 64)
	writeJSON(w, http.StatusOK, s.canvas.view(user.ID, since))
}

func (s *server) placeCanvasPixel(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var request struct {
		X     int `json:"x"`
		Y     int `json:"y"`
		Color int `json:"color"`
	}
	if !decodeJSON(w, r, &request) {
		return
	}
	view, err := s.canvas.place(user.ID, request.X, request.Y, request.Color)
	if err == nil {
		writeJSON(w, http.StatusOK, view)
		return
	}
	var cooldown canvasCooldownError
	if errors.As(err, &cooldown) {
		writeJSON(w, http.StatusTooManyRequests, map[string]any{
			"error": err.Error(), "retry_after_ms": cooldown.RetryAfter.Milliseconds(),
		})
		return
	}
	writeError(w, http.StatusBadRequest, err.Error())
}

func (s *server) createRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.rooms.create(user)
	writeResult(w, room, err)
}

func (s *server) createBotGame(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.rooms.createBot(user)
	writeResult(w, room, err)
}

func (s *server) matchPublicRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.rooms.matchPublic(user)
	writeResult(w, room, err)
}

func (s *server) joinRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var request struct {
		Code string `json:"code"`
	}
	if !decodeJSON(w, r, &request) {
		return
	}
	room, err := s.rooms.join(request.Code, user)
	writeResult(w, room, err)
}

func (s *server) roomState(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.rooms.state(r.URL.Query().Get("code"), user.ID)
	writeResult(w, room, err)
}

func (s *server) move(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var request struct {
		Code string   `json:"code"`
		From position `json:"from"`
		To   position `json:"to"`
	}
	if !decodeJSON(w, r, &request) {
		return
	}
	room, err := s.rooms.move(request.Code, user.ID, checkerMove{From: request.From, To: request.To})
	writeResult(w, room, err)
}

func (s *server) createChessRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.chess.create(user)
	writeChessResult(w, room, err)
}

func (s *server) matchPublicChessRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.chess.matchPublic(user)
	writeChessResult(w, room, err)
}

func (s *server) joinChessRoom(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var request struct {
		Code string `json:"code"`
	}
	if !decodeJSON(w, r, &request) {
		return
	}
	room, err := s.chess.join(request.Code, user)
	writeChessResult(w, room, err)
}

func (s *server) chessRoomState(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	room, err := s.chess.state(r.URL.Query().Get("code"), user.ID)
	writeChessResult(w, room, err)
}

func (s *server) chessMove(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "метод не поддерживается")
		return
	}
	user, ok := s.authorize(w, r)
	if !ok {
		return
	}
	var request struct {
		Code string `json:"code"`
		From int    `json:"from"`
		To   int    `json:"to"`
	}
	if !decodeJSON(w, r, &request) {
		return
	}
	room, err := s.chess.move(request.Code, user.ID, webChessMove{From: request.From, To: request.To})
	writeChessResult(w, room, err)
}

func (s *server) authorize(w http.ResponseWriter, r *http.Request) (telegramUser, bool) {
	now := time.Now()
	if user, err := validateTelegramInitData(r.Header.Get("X-Telegram-Init-Data"), s.botToken, now); err == nil {
		return user, true
	}
	if user, err := validateGameAuthToken(r.Header.Get("X-Telegram-Game-Auth"), s.botToken, now); err == nil {
		return user, true
	}
	writeError(w, http.StatusUnauthorized, errUnauthorized.Error())
	return telegramUser{}, false
}

func decodeJSON(w http.ResponseWriter, r *http.Request, target any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 4096)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		writeError(w, http.StatusBadRequest, "некорректный запрос")
		return false
	}
	return true
}

func writeResult(w http.ResponseWriter, room roomView, err error) {
	if err == nil {
		writeJSON(w, http.StatusOK, room)
		return
	}
	status := http.StatusBadRequest
	if errors.Is(err, errRoomNotFound) {
		status = http.StatusNotFound
	} else if errors.Is(err, errNotPlayer) {
		status = http.StatusForbidden
	} else if errors.Is(err, errNotYourTurn) || errors.Is(err, errRoomFull) {
		status = http.StatusConflict
	}
	writeError(w, status, err.Error())
}

func writeChessResult(w http.ResponseWriter, room chessRoomView, err error) {
	if err == nil {
		writeJSON(w, http.StatusOK, room)
		return
	}
	status := http.StatusBadRequest
	if errors.Is(err, errRoomNotFound) {
		status = http.StatusNotFound
	} else if errors.Is(err, errNotPlayer) {
		status = http.StatusForbidden
	} else if errors.Is(err, errNotYourTurn) || errors.Is(err, errRoomFull) {
		status = http.StatusConflict
	}
	writeError(w, status, err.Error())
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
