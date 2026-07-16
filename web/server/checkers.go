package main

import (
	"crypto/rand"
	"errors"
	"sort"
	"strings"
	"sync"
	"time"
)

const (
	redMan   = "r"
	redKing  = "R"
	blueMan  = "b"
	blueKing = "B"
)

var (
	errRoomNotFound = errors.New("комната не найдена")
	errRoomFull     = errors.New("в комнате уже два игрока")
	errNotPlayer    = errors.New("вы не участвуете в этой партии")
	errNotYourTurn  = errors.New("сейчас ход другого игрока")
	errInvalidMove  = errors.New("этот ход недоступен")
)

type position struct {
	Row int `json:"row"`
	Col int `json:"col"`
}

type checkerMove struct {
	From position `json:"from"`
	To   position `json:"to"`
}

type player struct {
	ID   int64  `json:"-"`
	Name string `json:"name"`
}

type room struct {
	Code       string
	Board      [8][8]string
	Red        player
	Blue       *player
	Bot        bool
	Public     bool
	Turn       string
	Status     string
	Winner     string
	ForcedFrom *position
	LastMoves  []checkerMove
	Version    int64
	UpdatedAt  time.Time
}

type roomView struct {
	Code       string        `json:"code"`
	Board      [8][8]string  `json:"board"`
	Red        player        `json:"red"`
	Blue       *player       `json:"blue,omitempty"`
	Turn       string        `json:"turn"`
	Status     string        `json:"status"`
	Winner     string        `json:"winner,omitempty"`
	You        string        `json:"you"`
	ForcedFrom *position     `json:"forced_from,omitempty"`
	Moves      []checkerMove `json:"moves"`
	LastMoves  []checkerMove `json:"last_moves,omitempty"`
	Version    int64         `json:"version"`
	Bot        bool          `json:"bot"`
	Public     bool          `json:"public"`
}

type roomManager struct {
	mu    sync.Mutex
	rooms map[string]*room
}

func newRoomManager() *roomManager {
	return &roomManager{rooms: make(map[string]*room)}
}

func initialBoard() [8][8]string {
	var board [8][8]string
	for row := 0; row < 8; row++ {
		for col := 0; col < 8; col++ {
			if (row+col)%2 == 0 {
				continue
			}
			if row < 3 {
				board[row][col] = blueMan
			} else if row > 4 {
				board[row][col] = redMan
			}
		}
	}
	return board
}

func (m *roomManager) create(user telegramUser) (roomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cleanupLocked()

	code, err := m.uniqueCodeLocked()
	if err != nil {
		return roomView{}, err
	}
	r := &room{
		Code: code, Board: initialBoard(), Red: player{ID: user.ID, Name: user.displayName()},
		Turn: "red", Status: "waiting", Version: 1, UpdatedAt: time.Now(),
	}
	m.rooms[code] = r
	return viewFor(r, user.ID), nil
}

func (m *roomManager) createBot(user telegramUser) (roomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cleanupLocked()

	code, err := m.uniqueCodeLocked()
	if err != nil {
		return roomView{}, err
	}
	bot := player{Name: "катемис"}
	r := &room{
		Code: code, Board: initialBoard(), Red: player{ID: user.ID, Name: user.displayName()},
		Blue: &bot, Bot: true, Turn: "red", Status: "active", Version: 1, UpdatedAt: time.Now(),
	}
	m.rooms[code] = r
	return viewFor(r, user.ID), nil
}

func (m *roomManager) matchPublic(user telegramUser) (roomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cleanupLocked()

	var waiting *room
	for _, candidate := range m.rooms {
		if !candidate.Public || candidate.Bot || candidate.Status != "waiting" {
			continue
		}
		if candidate.Red.ID == user.ID {
			candidate.UpdatedAt = time.Now()
			return viewFor(candidate, user.ID), nil
		}
		if waiting == nil || candidate.UpdatedAt.Before(waiting.UpdatedAt) {
			waiting = candidate
		}
	}
	if waiting != nil {
		waiting.Blue = &player{ID: user.ID, Name: user.displayName()}
		waiting.Status = "active"
		waiting.Version++
		waiting.UpdatedAt = time.Now()
		return viewFor(waiting, user.ID), nil
	}

	code, err := m.uniqueCodeLocked()
	if err != nil {
		return roomView{}, err
	}
	r := &room{
		Code: code, Board: initialBoard(), Red: player{ID: user.ID, Name: user.displayName()},
		Public: true, Turn: "red", Status: "waiting", Version: 1, UpdatedAt: time.Now(),
	}
	m.rooms[code] = r
	return viewFor(r, user.ID), nil
}

func (m *roomManager) join(code string, user telegramUser) (roomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return roomView{}, errRoomNotFound
	}
	if r.Red.ID == user.ID {
		return viewFor(r, user.ID), nil
	}
	if r.Bot {
		return roomView{}, errRoomFull
	}
	if r.Blue != nil && r.Blue.ID != user.ID {
		return roomView{}, errRoomFull
	}
	if r.Blue == nil {
		r.Blue = &player{ID: user.ID, Name: user.displayName()}
		r.Status = "active"
		r.Version++
	}
	r.UpdatedAt = time.Now()
	return viewFor(r, user.ID), nil
}

func (m *roomManager) state(code string, userID int64) (roomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return roomView{}, errRoomNotFound
	}
	if colorFor(r, userID) == "" {
		return roomView{}, errNotPlayer
	}
	if r.Public && r.Status == "waiting" {
		r.UpdatedAt = time.Now()
	}
	return viewFor(r, userID), nil
}

func (m *roomManager) move(code string, userID int64, requested checkerMove) (roomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return roomView{}, errRoomNotFound
	}
	color := colorFor(r, userID)
	if color == "" {
		return roomView{}, errNotPlayer
	}
	if r.Status != "active" || r.Turn != color {
		return roomView{}, errNotYourTurn
	}

	legal := legalMoves(r.Board, color, r.ForcedFrom)
	valid := false
	for _, candidate := range legal {
		if candidate == requested {
			valid = true
			break
		}
	}
	if !valid {
		return roomView{}, errInvalidMove
	}

	r.LastMoves = []checkerMove{requested}
	applyCheckerMove(r, requested, color)
	for r.Bot && r.Status == "active" && r.Turn == "blue" {
		moves := legalMoves(r.Board, "blue", r.ForcedFrom)
		if len(moves) == 0 {
			r.Status, r.Winner, r.ForcedFrom = "finished", "red", nil
			break
		}
		botMove := chooseBotMove(r.Board, moves)
		r.LastMoves = append(r.LastMoves, botMove)
		applyCheckerMove(r, botMove, "blue")
	}
	r.Version++
	r.UpdatedAt = time.Now()
	return viewFor(r, userID), nil
}

func applyCheckerMove(r *room, requested checkerMove, color string) {
	piece := r.Board[requested.From.Row][requested.From.Col]
	r.Board[requested.From.Row][requested.From.Col] = ""
	r.Board[requested.To.Row][requested.To.Col] = piece
	isCapture := abs(requested.To.Row-requested.From.Row) == 2
	if isCapture {
		r.Board[(requested.From.Row+requested.To.Row)/2][(requested.From.Col+requested.To.Col)/2] = ""
	}
	if piece == redMan && requested.To.Row == 0 {
		r.Board[requested.To.Row][requested.To.Col] = redKing
	} else if piece == blueMan && requested.To.Row == 7 {
		r.Board[requested.To.Row][requested.To.Col] = blueKing
	}

	if winner := boardWinner(r.Board); winner != "" {
		r.Status, r.Winner, r.ForcedFrom = "finished", winner, nil
	} else if isCapture && len(capturesFrom(r.Board, requested.To, color)) > 0 {
		forced := requested.To
		r.ForcedFrom = &forced
	} else {
		r.ForcedFrom = nil
		if color == "red" {
			r.Turn = "blue"
		} else {
			r.Turn = "red"
		}
		if len(legalMoves(r.Board, r.Turn, nil)) == 0 {
			r.Status, r.Winner = "finished", color
		}
	}
}

func chooseBotMove(board [8][8]string, moves []checkerMove) checkerMove {
	const maxDepth = 10
	deadline := time.Now().Add(180 * time.Millisecond)
	best := moves[0]
	position := enginePosition{Board: board, Turn: "blue", Status: "active"}

	for depth := 1; depth <= maxDepth; depth++ {
		table := make(map[engineKey]engineEntry, 2048)
		candidate, complete := searchBestMove(position, moves, depth, deadline, table)
		if !complete {
			break
		}
		best = candidate
	}
	return best
}

const (
	engineInfinity = 1_000_000
	boundExact     = iota
	boundLower
	boundUpper
)

type enginePosition struct {
	Board      [8][8]string
	Turn       string
	Status     string
	Winner     string
	ForcedFrom *position
}

type engineKey struct {
	Board  [8][8]string
	Turn   string
	Forced int
}

type engineEntry struct {
	Depth int
	Score int
	Bound int
}

func searchBestMove(
	current enginePosition,
	moves []checkerMove,
	depth int,
	deadline time.Time,
	table map[engineKey]engineEntry,
) (checkerMove, bool) {
	ordered := orderedMoves(current.Board, moves)
	best, bestScore := ordered[0], -engineInfinity
	alpha, beta := -engineInfinity, engineInfinity
	for _, move := range ordered {
		if time.Now().After(deadline) {
			return best, false
		}
		next := engineAfterMove(current, move)
		score, complete := alphaBeta(next, depth-1, alpha, beta, deadline, table)
		if !complete {
			return best, false
		}
		if score > bestScore {
			best, bestScore = move, score
		}
		if score > alpha {
			alpha = score
		}
	}
	return best, true
}

func alphaBeta(
	current enginePosition,
	depth int,
	alpha int,
	beta int,
	deadline time.Time,
	table map[engineKey]engineEntry,
) (int, bool) {
	if time.Now().After(deadline) {
		return 0, false
	}
	if current.Status == "finished" {
		if current.Winner == "blue" {
			return engineInfinity + depth, true
		}
		return -engineInfinity - depth, true
	}
	if depth <= 0 {
		return evaluateBoard(current.Board), true
	}

	key := makeEngineKey(current)
	originalAlpha, originalBeta := alpha, beta
	if cached, ok := table[key]; ok && cached.Depth >= depth {
		switch cached.Bound {
		case boundExact:
			return cached.Score, true
		case boundLower:
			if cached.Score > alpha {
				alpha = cached.Score
			}
		case boundUpper:
			if cached.Score < beta {
				beta = cached.Score
			}
		}
		if alpha >= beta {
			return cached.Score, true
		}
	}

	moves := legalMoves(current.Board, current.Turn, current.ForcedFrom)
	if len(moves) == 0 {
		if current.Turn == "blue" {
			return -engineInfinity - depth, true
		}
		return engineInfinity + depth, true
	}
	moves = orderedMoves(current.Board, moves)

	best := -engineInfinity
	if current.Turn == "red" {
		best = engineInfinity
	}
	for _, move := range moves {
		score, complete := alphaBeta(engineAfterMove(current, move), depth-1, alpha, beta, deadline, table)
		if !complete {
			return 0, false
		}
		if current.Turn == "blue" {
			if score > best {
				best = score
			}
			if best > alpha {
				alpha = best
			}
		} else {
			if score < best {
				best = score
			}
			if best < beta {
				beta = best
			}
		}
		if alpha >= beta {
			break
		}
	}

	bound := boundExact
	if best <= originalAlpha {
		bound = boundUpper
	} else if best >= originalBeta {
		bound = boundLower
	}
	table[key] = engineEntry{Depth: depth, Score: best, Bound: bound}
	return best, true
}

func engineAfterMove(current enginePosition, move checkerMove) enginePosition {
	forced := current.ForcedFrom
	temporary := room{
		Board: current.Board, Turn: current.Turn, Status: "active", ForcedFrom: forced,
	}
	applyCheckerMove(&temporary, move, current.Turn)
	return enginePosition{
		Board: temporary.Board, Turn: temporary.Turn, Status: temporary.Status,
		Winner: temporary.Winner, ForcedFrom: temporary.ForcedFrom,
	}
}

func orderedMoves(board [8][8]string, moves []checkerMove) []checkerMove {
	ordered := append([]checkerMove(nil), moves...)
	sort.SliceStable(ordered, func(i, j int) bool {
		return moveOrderScore(board, ordered[i]) > moveOrderScore(board, ordered[j])
	})
	return ordered
}

func moveOrderScore(board [8][8]string, move checkerMove) int {
	score := 7 - abs(3-move.To.Col)
	piece := board[move.From.Row][move.From.Col]
	if abs(move.To.Row-move.From.Row) == 2 {
		captured := board[(move.From.Row+move.To.Row)/2][(move.From.Col+move.To.Col)/2]
		score += 100
		if captured == redKing || captured == blueKing {
			score += 40
		}
	}
	if (piece == blueMan && move.To.Row == 7) || (piece == redMan && move.To.Row == 0) {
		score += 70
	}
	return score
}

func evaluateBoard(board [8][8]string) int {
	score := 0
	for row := range board {
		for col, piece := range board[row] {
			centre := 7 - abs(3-col)
			switch piece {
			case blueMan:
				score += 100 + row*4 + centre
			case blueKing:
				score += 185 + centre*2
			case redMan:
				score -= 100 + (7-row)*4 + centre
			case redKing:
				score -= 185 + centre*2
			}
		}
	}
	score += (len(legalMoves(board, "blue", nil)) - len(legalMoves(board, "red", nil))) * 3
	return score
}

func makeEngineKey(current enginePosition) engineKey {
	forced := -1
	if current.ForcedFrom != nil {
		forced = current.ForcedFrom.Row*8 + current.ForcedFrom.Col
	}
	return engineKey{Board: current.Board, Turn: current.Turn, Forced: forced}
}

func viewFor(r *room, userID int64) roomView {
	you := colorFor(r, userID)
	moves := []checkerMove{}
	if r.Status == "active" && r.Turn == you {
		moves = legalMoves(r.Board, you, r.ForcedFrom)
	}
	return roomView{
		Code: r.Code, Board: r.Board, Red: r.Red, Blue: r.Blue, Turn: r.Turn,
		Status: r.Status, Winner: r.Winner, You: you, ForcedFrom: r.ForcedFrom,
		Moves: moves, LastMoves: r.LastMoves, Version: r.Version, Bot: r.Bot, Public: r.Public,
	}
}

func colorFor(r *room, userID int64) string {
	if r.Red.ID == userID {
		return "red"
	}
	if r.Blue != nil && r.Blue.ID == userID {
		return "blue"
	}
	return ""
}

func legalMoves(board [8][8]string, color string, forced *position) []checkerMove {
	if forced != nil {
		return capturesFrom(board, *forced, color)
	}
	captures := make([]checkerMove, 0)
	for row := 0; row < 8; row++ {
		for col := 0; col < 8; col++ {
			if pieceColor(board[row][col]) == color {
				captures = append(captures, capturesFrom(board, position{row, col}, color)...)
			}
		}
	}
	if len(captures) > 0 {
		return captures
	}

	moves := make([]checkerMove, 0)
	for row := 0; row < 8; row++ {
		for col := 0; col < 8; col++ {
			from := position{row, col}
			piece := board[row][col]
			if pieceColor(piece) != color {
				continue
			}
			for _, direction := range moveDirections(piece) {
				to := position{row + direction.Row, col + direction.Col}
				if inside(to) && board[to.Row][to.Col] == "" {
					moves = append(moves, checkerMove{From: from, To: to})
				}
			}
		}
	}
	return moves
}

func capturesFrom(board [8][8]string, from position, color string) []checkerMove {
	if !inside(from) || pieceColor(board[from.Row][from.Col]) != color {
		return nil
	}
	moves := make([]checkerMove, 0, 4)
	for _, direction := range []position{{-1, -1}, {-1, 1}, {1, -1}, {1, 1}} {
		middle := position{from.Row + direction.Row, from.Col + direction.Col}
		to := position{from.Row + 2*direction.Row, from.Col + 2*direction.Col}
		if inside(to) && pieceColor(board[middle.Row][middle.Col]) == opposite(color) && board[to.Row][to.Col] == "" {
			moves = append(moves, checkerMove{From: from, To: to})
		}
	}
	return moves
}

func moveDirections(piece string) []position {
	if piece == redKing || piece == blueKing {
		return []position{{-1, -1}, {-1, 1}, {1, -1}, {1, 1}}
	}
	if piece == redMan {
		return []position{{-1, -1}, {-1, 1}}
	}
	return []position{{1, -1}, {1, 1}}
}

func boardWinner(board [8][8]string) string {
	red, blue := false, false
	for row := range board {
		for col := range board[row] {
			red = red || pieceColor(board[row][col]) == "red"
			blue = blue || pieceColor(board[row][col]) == "blue"
		}
	}
	if !red {
		return "blue"
	}
	if !blue {
		return "red"
	}
	return ""
}

func pieceColor(piece string) string {
	if piece == redMan || piece == redKing {
		return "red"
	}
	if piece == blueMan || piece == blueKing {
		return "blue"
	}
	return ""
}

func opposite(color string) string {
	if color == "red" {
		return "blue"
	}
	return "red"
}

func inside(p position) bool { return p.Row >= 0 && p.Row < 8 && p.Col >= 0 && p.Col < 8 }
func abs(value int) int {
	if value < 0 {
		return -value
	}
	return value
}
func normalizeCode(code string) string { return strings.ToUpper(strings.TrimSpace(code)) }

func (m *roomManager) uniqueCodeLocked() (string, error) {
	const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	buffer := make([]byte, 6)
	for attempt := 0; attempt < 10; attempt++ {
		if _, err := rand.Read(buffer); err != nil {
			return "", err
		}
		for i := range buffer {
			buffer[i] = alphabet[int(buffer[i])%len(alphabet)]
		}
		code := string(buffer)
		if m.rooms[code] == nil {
			return code, nil
		}
	}
	return "", errors.New("не удалось создать код комнаты")
}

func (m *roomManager) cleanupLocked() {
	now := time.Now()
	cutoff := now.Add(-6 * time.Hour)
	publicCutoff := now.Add(-2 * time.Minute)
	for code, r := range m.rooms {
		if r.UpdatedAt.Before(cutoff) || (r.Public && r.Status == "waiting" && r.UpdatedAt.Before(publicCutoff)) {
			delete(m.rooms, code)
		}
	}
}
