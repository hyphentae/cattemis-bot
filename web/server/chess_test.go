package main

import "testing"

func requireChessMove(t *testing.T, position chessPosition, from, to int) webChessMove {
	t.Helper()
	for _, move := range legalWebChessMoves(position) {
		if move.From == from && move.To == to {
			return move
		}
	}
	t.Fatalf("missing legal chess move %d-%d", from, to)
	return webChessMove{}
}

func TestInitialChessPositionHasTwentyMoves(t *testing.T) {
	position := initialChessPosition()
	if moves := legalWebChessMoves(position); len(moves) != 20 {
		t.Fatalf("expected 20 initial moves, got %d", len(moves))
	}
}

func TestChessSpecialMoves(t *testing.T) {
	position := initialChessPosition()
	position = applyWebChessMove(position, requireChessMove(t, position, 52, 36))
	position = applyWebChessMove(position, requireChessMove(t, position, 8, 16))
	position = applyWebChessMove(position, requireChessMove(t, position, 36, 28))
	position = applyWebChessMove(position, requireChessMove(t, position, 11, 27))
	enPassant := requireChessMove(t, position, 28, 19)
	if !enPassant.EnPassant {
		t.Fatal("expected en passant move")
	}
	position = applyWebChessMove(position, enPassant)
	if position.Board[27] != "" || position.Board[19] != "P" {
		t.Fatal("en passant was applied incorrectly")
	}

	castle := initialChessPosition()
	castle.Board = [64]string{}
	castle.Board[60], castle.Board[56], castle.Board[63], castle.Board[4] = "K", "R", "R", "k"
	kingSide := requireChessMove(t, castle, 60, 62)
	if kingSide.Castle != "king" {
		t.Fatal("expected king-side castling")
	}
	castle = applyWebChessMove(castle, kingSide)
	if castle.Board[62] != "K" || castle.Board[61] != "R" || castle.Board[63] != "" {
		t.Fatal("castling was applied incorrectly")
	}
}

func TestChessFoolsMate(t *testing.T) {
	position := initialChessPosition()
	for _, move := range [][2]int{{53, 45}, {12, 28}, {54, 38}, {3, 39}} {
		position = applyWebChessMove(position, requireChessMove(t, position, move[0], move[1]))
	}
	if len(legalWebChessMoves(position)) != 0 || !webChessInCheck(position, "w") {
		t.Fatal("fool's mate was not detected")
	}
}

func TestChessRoomFlow(t *testing.T) {
	manager := newChessRoomManager()
	white := telegramUser{ID: 1, FirstName: "White"}
	black := telegramUser{ID: 2, FirstName: "Black"}
	created, err := manager.create(white)
	if err != nil {
		t.Fatal(err)
	}
	if created.Status != "waiting" || created.You != "w" || len(created.Moves) != 0 {
		t.Fatalf("unexpected created chess room: %#v", created)
	}
	joined, err := manager.join(created.Code, black)
	if err != nil {
		t.Fatal(err)
	}
	if joined.Status != "active" || joined.You != "b" || len(joined.Moves) != 0 {
		t.Fatalf("unexpected joined chess room: %#v", joined)
	}
	moved, err := manager.move(created.Code, white.ID, webChessMove{From: 52, To: 36})
	if err != nil {
		t.Fatal(err)
	}
	if moved.Turn != "b" || len(moved.Moves) != 0 {
		t.Fatalf("turn was not passed to black: %#v", moved)
	}
	if moved.LastMove == nil || moved.LastMove.From != 52 || moved.LastMove.To != 36 {
		t.Fatalf("last chess move was not exposed: %#v", moved.LastMove)
	}
	blackView, err := manager.state(created.Code, black.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(blackView.Moves) != 20 {
		t.Fatalf("expected black replies, got %d", len(blackView.Moves))
	}
}

func TestPublicChessMatchmaking(t *testing.T) {
	manager := newChessRoomManager()
	first := telegramUser{ID: 1, FirstName: "First"}
	second := telegramUser{ID: 2, FirstName: "Second"}

	waiting, err := manager.matchPublic(first)
	if err != nil {
		t.Fatal(err)
	}
	if !waiting.Public || waiting.Status != "waiting" || waiting.You != "w" {
		t.Fatalf("unexpected public lobby: %#v", waiting)
	}
	joined, err := manager.matchPublic(second)
	if err != nil {
		t.Fatal(err)
	}
	if joined.Code != waiting.Code || joined.Status != "active" || joined.You != "b" {
		t.Fatalf("players were not matched: %#v", joined)
	}
	firstView, err := manager.state(waiting.Code, first.ID)
	if err != nil || firstView.Black == nil || firstView.Black.Name != "Second" {
		t.Fatalf("first player did not see opponent: view=%#v err=%v", firstView, err)
	}
}
