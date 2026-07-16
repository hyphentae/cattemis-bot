package main

import (
	"crypto/rand"
	"errors"
	"sync"
	"time"
)

type webChessMove struct {
	From int `json:"from"`
	To   int `json:"to"`

	Capture    string `json:"capture,omitempty"`
	Promotion  bool   `json:"promotion,omitempty"`
	DoublePawn bool   `json:"double_pawn,omitempty"`
	EnPassant  bool   `json:"en_passant,omitempty"`
	Castle     string `json:"castle,omitempty"`
}

type chessCastling struct{ K, Q, k, q bool }

type chessPosition struct {
	Board     [64]string
	Turn      string
	Castling  chessCastling
	EnPassant int
	Halfmove  int
}

type chessRoom struct {
	Code      string
	Position  chessPosition
	White     player
	Black     *player
	Status    string
	Public    bool
	Winner    string
	LastMove  *webChessMove
	Version   int64
	UpdatedAt time.Time
}

type chessRoomView struct {
	Code     string         `json:"code"`
	Board    [64]string     `json:"board"`
	White    player         `json:"white"`
	Black    *player        `json:"black,omitempty"`
	Turn     string         `json:"turn"`
	Status   string         `json:"status"`
	Winner   string         `json:"winner,omitempty"`
	You      string         `json:"you"`
	Moves    []webChessMove `json:"moves"`
	LastMove *webChessMove  `json:"last_move,omitempty"`
	Version  int64          `json:"version"`
	Public   bool           `json:"public"`
}

type chessRoomManager struct {
	mu    sync.Mutex
	rooms map[string]*chessRoom
}

func newChessRoomManager() *chessRoomManager {
	return &chessRoomManager{rooms: make(map[string]*chessRoom)}
}

func initialChessPosition() chessPosition {
	position := chessPosition{
		Turn: "w", Castling: chessCastling{K: true, Q: true, k: true, q: true}, EnPassant: -1,
	}
	backBlack := []string{"r", "n", "b", "q", "k", "b", "n", "r"}
	backWhite := []string{"R", "N", "B", "Q", "K", "B", "N", "R"}
	for col := 0; col < 8; col++ {
		position.Board[col] = backBlack[col]
		position.Board[8+col] = "p"
		position.Board[48+col] = "P"
		position.Board[56+col] = backWhite[col]
	}
	return position
}

func (m *chessRoomManager) create(user telegramUser) (chessRoomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cleanupLocked()
	code, err := m.uniqueCodeLocked()
	if err != nil {
		return chessRoomView{}, err
	}
	r := &chessRoom{
		Code: code, Position: initialChessPosition(), White: player{ID: user.ID, Name: user.displayName()},
		Status: "waiting", Version: 1, UpdatedAt: time.Now(),
	}
	m.rooms[code] = r
	return chessViewFor(r, user.ID), nil
}

func (m *chessRoomManager) matchPublic(user telegramUser) (chessRoomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cleanupLocked()

	var waiting *chessRoom
	for _, candidate := range m.rooms {
		if !candidate.Public || candidate.Status != "waiting" {
			continue
		}
		if candidate.White.ID == user.ID {
			candidate.UpdatedAt = time.Now()
			return chessViewFor(candidate, user.ID), nil
		}
		if waiting == nil || candidate.UpdatedAt.Before(waiting.UpdatedAt) {
			waiting = candidate
		}
	}
	if waiting != nil {
		waiting.Black = &player{ID: user.ID, Name: user.displayName()}
		waiting.Status = "active"
		waiting.Version++
		waiting.UpdatedAt = time.Now()
		return chessViewFor(waiting, user.ID), nil
	}

	code, err := m.uniqueCodeLocked()
	if err != nil {
		return chessRoomView{}, err
	}
	r := &chessRoom{
		Code: code, Position: initialChessPosition(), White: player{ID: user.ID, Name: user.displayName()},
		Public: true, Status: "waiting", Version: 1, UpdatedAt: time.Now(),
	}
	m.rooms[code] = r
	return chessViewFor(r, user.ID), nil
}

func (m *chessRoomManager) join(code string, user telegramUser) (chessRoomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return chessRoomView{}, errRoomNotFound
	}
	if r.White.ID == user.ID {
		return chessViewFor(r, user.ID), nil
	}
	if r.Black != nil && r.Black.ID != user.ID {
		return chessRoomView{}, errRoomFull
	}
	if r.Black == nil {
		r.Black = &player{ID: user.ID, Name: user.displayName()}
		r.Status = "active"
		r.Version++
	}
	r.UpdatedAt = time.Now()
	return chessViewFor(r, user.ID), nil
}

func (m *chessRoomManager) state(code string, userID int64) (chessRoomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return chessRoomView{}, errRoomNotFound
	}
	if chessColorFor(r, userID) == "" {
		return chessRoomView{}, errNotPlayer
	}
	if r.Public && r.Status == "waiting" {
		r.UpdatedAt = time.Now()
	}
	return chessViewFor(r, userID), nil
}

func (m *chessRoomManager) move(code string, userID int64, requested webChessMove) (chessRoomView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[normalizeCode(code)]
	if r == nil {
		return chessRoomView{}, errRoomNotFound
	}
	color := chessColorFor(r, userID)
	if color == "" {
		return chessRoomView{}, errNotPlayer
	}
	if r.Status != "active" || r.Position.Turn != color {
		return chessRoomView{}, errNotYourTurn
	}

	var selected *webChessMove
	for _, move := range legalWebChessMoves(r.Position) {
		if move.From == requested.From && move.To == requested.To {
			copy := move
			selected = &copy
			break
		}
	}
	if selected == nil {
		return chessRoomView{}, errInvalidMove
	}
	r.LastMove = selected
	r.Position = applyWebChessMove(r.Position, *selected)
	nextMoves := legalWebChessMoves(r.Position)
	if len(nextMoves) == 0 {
		r.Status = "finished"
		if webChessInCheck(r.Position, r.Position.Turn) {
			r.Winner = oppositeChessColor(r.Position.Turn)
		} else {
			r.Winner = "draw"
		}
	} else if insufficientChessMaterial(r.Position.Board) || r.Position.Halfmove >= 100 {
		r.Status, r.Winner = "finished", "draw"
	}
	r.Version++
	r.UpdatedAt = time.Now()
	return chessViewFor(r, userID), nil
}

func chessViewFor(r *chessRoom, userID int64) chessRoomView {
	you := chessColorFor(r, userID)
	moves := []webChessMove{}
	if r.Status == "active" && r.Position.Turn == you {
		moves = legalWebChessMoves(r.Position)
	}
	return chessRoomView{
		Code: r.Code, Board: r.Position.Board, White: r.White, Black: r.Black,
		Turn: r.Position.Turn, Status: r.Status, Winner: r.Winner, You: you,
		Moves: moves, LastMove: r.LastMove, Version: r.Version, Public: r.Public,
	}
}

func chessColorFor(r *chessRoom, userID int64) string {
	if r.White.ID == userID {
		return "w"
	}
	if r.Black != nil && r.Black.ID == userID {
		return "b"
	}
	return ""
}

func legalWebChessMoves(position chessPosition) []webChessMove {
	color := position.Turn
	pseudo := pseudoWebChessMoves(position, color)
	legal := make([]webChessMove, 0, len(pseudo))
	for _, move := range pseudo {
		if !webChessInCheck(applyWebChessMove(position, move), color) {
			legal = append(legal, move)
		}
	}
	return legal
}

func pseudoWebChessMoves(position chessPosition, color string) []webChessMove {
	moves := make([]webChessMove, 0, 48)
	for from, piece := range position.Board {
		if webChessPieceColor(piece) != color {
			continue
		}
		row, col := from/8, from%8
		switch lowerChessPiece(piece) {
		case "p":
			direction, startRow, promotionRow := 1, 1, 7
			if color == "w" {
				direction, startRow, promotionRow = -1, 6, 0
			}
			nextRow := row + direction
			if webChessInside(nextRow, col) && position.Board[nextRow*8+col] == "" {
				to := nextRow*8 + col
				moves = append(moves, webChessMove{From: from, To: to, Promotion: nextRow == promotionRow})
				if row == startRow && position.Board[(row+2*direction)*8+col] == "" {
					moves = append(moves, webChessMove{From: from, To: (row+2*direction)*8 + col, DoublePawn: true})
				}
			}
			for _, colStep := range []int{-1, 1} {
				nextCol := col + colStep
				if !webChessInside(nextRow, nextCol) {
					continue
				}
				to, target := nextRow*8+nextCol, position.Board[nextRow*8+nextCol]
				if target != "" && webChessPieceColor(target) != color {
					moves = append(moves, webChessMove{From: from, To: to, Capture: target, Promotion: nextRow == promotionRow})
				} else if to == position.EnPassant {
					moves = append(moves, webChessMove{From: from, To: to, EnPassant: true, Capture: map[bool]string{true: "p", false: "P"}[color == "w"]})
				}
			}
		case "n":
			addWebChessSteps(position, from, color, [][2]int{{-2, -1}, {-2, 1}, {-1, -2}, {-1, 2}, {1, -2}, {1, 2}, {2, -1}, {2, 1}}, &moves)
		case "b":
			addWebChessSlides(position, from, color, [][2]int{{-1, -1}, {-1, 1}, {1, -1}, {1, 1}}, &moves)
		case "r":
			addWebChessSlides(position, from, color, [][2]int{{-1, 0}, {1, 0}, {0, -1}, {0, 1}}, &moves)
		case "q":
			addWebChessSlides(position, from, color, [][2]int{{-1, -1}, {-1, 1}, {1, -1}, {1, 1}, {-1, 0}, {1, 0}, {0, -1}, {0, 1}}, &moves)
		case "k":
			addWebChessSteps(position, from, color, [][2]int{{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}}, &moves)
			addWebChessCastling(position, color, &moves)
		}
	}
	return moves
}

func addWebChessSteps(position chessPosition, from int, color string, steps [][2]int, moves *[]webChessMove) {
	row, col := from/8, from%8
	for _, step := range steps {
		nextRow, nextCol := row+step[0], col+step[1]
		if !webChessInside(nextRow, nextCol) {
			continue
		}
		to, target := nextRow*8+nextCol, position.Board[nextRow*8+nextCol]
		if target == "" || webChessPieceColor(target) != color {
			*moves = append(*moves, webChessMove{From: from, To: to, Capture: target})
		}
	}
}

func addWebChessSlides(position chessPosition, from int, color string, directions [][2]int, moves *[]webChessMove) {
	row, col := from/8, from%8
	for _, direction := range directions {
		for distance := 1; distance < 8; distance++ {
			nextRow, nextCol := row+direction[0]*distance, col+direction[1]*distance
			if !webChessInside(nextRow, nextCol) {
				break
			}
			to, target := nextRow*8+nextCol, position.Board[nextRow*8+nextCol]
			if target == "" {
				*moves = append(*moves, webChessMove{From: from, To: to})
				continue
			}
			if webChessPieceColor(target) != color {
				*moves = append(*moves, webChessMove{From: from, To: to, Capture: target})
			}
			break
		}
	}
}

func addWebChessCastling(position chessPosition, color string, moves *[]webChessMove) {
	row, kingFrom, enemy := 0, 4, "w"
	kingSide, queenSide := position.Castling.k, position.Castling.q
	if color == "w" {
		row, kingFrom, enemy = 7, 60, "b"
		kingSide, queenSide = position.Castling.K, position.Castling.Q
	}
	if webChessSquareAttacked(position.Board, kingFrom, enemy) {
		return
	}
	if kingSide && lowerChessPiece(position.Board[row*8+7]) == "r" && webChessPieceColor(position.Board[row*8+7]) == color &&
		position.Board[row*8+5] == "" && position.Board[row*8+6] == "" &&
		!webChessSquareAttacked(position.Board, row*8+5, enemy) && !webChessSquareAttacked(position.Board, row*8+6, enemy) {
		*moves = append(*moves, webChessMove{From: kingFrom, To: row*8 + 6, Castle: "king"})
	}
	if queenSide && lowerChessPiece(position.Board[row*8]) == "r" && webChessPieceColor(position.Board[row*8]) == color &&
		position.Board[row*8+1] == "" && position.Board[row*8+2] == "" && position.Board[row*8+3] == "" &&
		!webChessSquareAttacked(position.Board, row*8+3, enemy) && !webChessSquareAttacked(position.Board, row*8+2, enemy) {
		*moves = append(*moves, webChessMove{From: kingFrom, To: row*8 + 2, Castle: "queen"})
	}
}

func applyWebChessMove(position chessPosition, move webChessMove) chessPosition {
	next := position
	next.Board = position.Board
	piece := next.Board[move.From]
	color, pieceType := webChessPieceColor(piece), lowerChessPiece(piece)
	captured := next.Board[move.To]
	next.Board[move.From] = ""
	next.Board[move.To] = piece
	if move.Promotion {
		if color == "w" {
			next.Board[move.To] = "Q"
		} else {
			next.Board[move.To] = "q"
		}
	}
	if move.EnPassant {
		direction := 1
		if color == "w" {
			direction = -1
		}
		next.Board[move.To-direction*8] = ""
	}
	row := 0
	if color == "w" {
		row = 7
	}
	if move.Castle == "king" {
		next.Board[row*8+5], next.Board[row*8+7] = next.Board[row*8+7], ""
	} else if move.Castle == "queen" {
		next.Board[row*8+3], next.Board[row*8] = next.Board[row*8], ""
	}
	if pieceType == "k" {
		if color == "w" {
			next.Castling.K, next.Castling.Q = false, false
		} else {
			next.Castling.k, next.Castling.q = false, false
		}
	}
	if move.From == 63 || move.To == 63 {
		next.Castling.K = false
	}
	if move.From == 56 || move.To == 56 {
		next.Castling.Q = false
	}
	if move.From == 7 || move.To == 7 {
		next.Castling.k = false
	}
	if move.From == 0 || move.To == 0 {
		next.Castling.q = false
	}
	next.EnPassant = -1
	if move.DoublePawn {
		next.EnPassant = (move.From + move.To) / 2
	}
	if pieceType == "p" || captured != "" || move.EnPassant {
		next.Halfmove = 0
	} else {
		next.Halfmove++
	}
	next.Turn = oppositeChessColor(color)
	return next
}

func webChessSquareAttacked(board [64]string, target int, byColor string) bool {
	row, col := target/8, target%8
	pawnSourceRow := row - 1
	if byColor == "w" {
		pawnSourceRow = row + 1
	}
	for _, colStep := range []int{-1, 1} {
		sourceCol := col + colStep
		if webChessInside(pawnSourceRow, sourceCol) {
			piece := board[pawnSourceRow*8+sourceCol]
			if webChessPieceColor(piece) == byColor && lowerChessPiece(piece) == "p" {
				return true
			}
		}
	}
	knights := [][2]int{{-2, -1}, {-2, 1}, {-1, -2}, {-1, 2}, {1, -2}, {1, 2}, {2, -1}, {2, 1}}
	for _, step := range knights {
		r, c := row+step[0], col+step[1]
		if webChessInside(r, c) && webChessPieceColor(board[r*8+c]) == byColor && lowerChessPiece(board[r*8+c]) == "n" {
			return true
		}
	}
	kings := [][2]int{{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}}
	for _, step := range kings {
		r, c := row+step[0], col+step[1]
		if webChessInside(r, c) && webChessPieceColor(board[r*8+c]) == byColor && lowerChessPiece(board[r*8+c]) == "k" {
			return true
		}
	}
	if webChessRayAttacked(board, row, col, byColor, [][2]int{{-1, -1}, {-1, 1}, {1, -1}, {1, 1}}, "bq") {
		return true
	}
	return webChessRayAttacked(board, row, col, byColor, [][2]int{{-1, 0}, {1, 0}, {0, -1}, {0, 1}}, "rq")
}

func webChessRayAttacked(board [64]string, row, col int, color string, directions [][2]int, types string) bool {
	for _, direction := range directions {
		for distance := 1; distance < 8; distance++ {
			r, c := row+direction[0]*distance, col+direction[1]*distance
			if !webChessInside(r, c) {
				break
			}
			piece := board[r*8+c]
			if piece == "" {
				continue
			}
			if webChessPieceColor(piece) == color && containsChessType(types, lowerChessPiece(piece)) {
				return true
			}
			break
		}
	}
	return false
}

func webChessInCheck(position chessPosition, color string) bool {
	king := "k"
	if color == "w" {
		king = "K"
	}
	square := -1
	for index, piece := range position.Board {
		if piece == king {
			square = index
			break
		}
	}
	return square == -1 || webChessSquareAttacked(position.Board, square, oppositeChessColor(color))
}

func insufficientChessMaterial(board [64]string) bool {
	pieces := make([]string, 0, 4)
	for _, piece := range board {
		if piece != "" && lowerChessPiece(piece) != "k" {
			pieces = append(pieces, lowerChessPiece(piece))
		}
	}
	return len(pieces) == 0 || (len(pieces) == 1 && (pieces[0] == "b" || pieces[0] == "n"))
}

func webChessPieceColor(piece string) string {
	if piece == "" {
		return ""
	}
	if piece[0] >= 'A' && piece[0] <= 'Z' {
		return "w"
	}
	return "b"
}
func lowerChessPiece(piece string) string {
	if piece == "" {
		return ""
	}
	if piece[0] >= 'A' && piece[0] <= 'Z' {
		return string(piece[0] + ('a' - 'A'))
	}
	return piece
}
func oppositeChessColor(color string) string {
	if color == "w" {
		return "b"
	}
	return "w"
}
func webChessInside(row, col int) bool { return row >= 0 && row < 8 && col >= 0 && col < 8 }
func containsChessType(types, piece string) bool {
	for index := 0; index < len(types); index++ {
		if string(types[index]) == piece {
			return true
		}
	}
	return false
}

func (m *chessRoomManager) uniqueCodeLocked() (string, error) {
	const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	buffer := make([]byte, 6)
	for attempt := 0; attempt < 10; attempt++ {
		if _, err := rand.Read(buffer); err != nil {
			return "", err
		}
		for index := range buffer {
			buffer[index] = alphabet[int(buffer[index])%len(alphabet)]
		}
		code := string(buffer)
		if m.rooms[code] == nil {
			return code, nil
		}
	}
	return "", errors.New("не удалось создать код комнаты")
}

func (m *chessRoomManager) cleanupLocked() {
	now := time.Now()
	cutoff := now.Add(-6 * time.Hour)
	publicCutoff := now.Add(-2 * time.Minute)
	for code, room := range m.rooms {
		if room.UpdatedAt.Before(cutoff) || (room.Public && room.Status == "waiting" && room.UpdatedAt.Before(publicCutoff)) {
			delete(m.rooms, code)
		}
	}
}
