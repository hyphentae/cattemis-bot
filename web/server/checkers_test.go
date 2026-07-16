package main

import "testing"

func TestLegalMovesRequireCapture(t *testing.T) {
	var board [8][8]string
	board[5][0] = redMan
	board[5][4] = redMan
	board[4][1] = blueMan

	moves := legalMoves(board, "red", nil)
	if len(moves) != 1 {
		t.Fatalf("expected one mandatory capture, got %d", len(moves))
	}
	want := checkerMove{From: position{5, 0}, To: position{3, 2}}
	if moves[0] != want {
		t.Fatalf("unexpected move: %#v", moves[0])
	}
}

func TestCaptureChainKeepsTurn(t *testing.T) {
	manager := newRoomManager()
	var board [8][8]string
	board[5][0] = redMan
	board[4][1] = blueMan
	board[2][3] = blueMan
	board[0][7] = blueMan
	manager.rooms["ABC123"] = &room{
		Code: "ABC123", Board: board, Red: player{ID: 1, Name: "Red"},
		Blue: &player{ID: 2, Name: "Blue"}, Turn: "red", Status: "active",
	}

	view, err := manager.move("ABC123", 1, checkerMove{From: position{5, 0}, To: position{3, 2}})
	if err != nil {
		t.Fatal(err)
	}
	if view.Turn != "red" || view.ForcedFrom == nil || *view.ForcedFrom != (position{3, 2}) {
		t.Fatalf("capture chain was not preserved: %#v", view)
	}
}

func TestPromotion(t *testing.T) {
	manager := newRoomManager()
	var board [8][8]string
	board[1][2] = redMan
	board[7][0] = blueMan
	manager.rooms["ABC123"] = &room{
		Code: "ABC123", Board: board, Red: player{ID: 1, Name: "Red"},
		Blue: &player{ID: 2, Name: "Blue"}, Turn: "red", Status: "active",
	}

	view, err := manager.move("ABC123", 1, checkerMove{From: position{1, 2}, To: position{0, 1}})
	if err != nil {
		t.Fatal(err)
	}
	if view.Board[0][1] != redKing {
		t.Fatalf("expected red king, got %q", view.Board[0][1])
	}
}

func TestBotRepliesAfterPlayerMove(t *testing.T) {
	manager := newRoomManager()
	user := telegramUser{ID: 1, FirstName: "Player"}
	created, err := manager.createBot(user)
	if err != nil {
		t.Fatal(err)
	}
	if !created.Bot || created.Status != "active" || created.Blue == nil {
		t.Fatalf("unexpected bot room: %#v", created)
	}

	view, err := manager.move(created.Code, user.ID, checkerMove{
		From: position{Row: 5, Col: 0},
		To:   position{Row: 4, Col: 1},
	})
	if err != nil {
		t.Fatal(err)
	}
	if view.Status != "active" || view.Turn != "red" || len(view.Moves) == 0 {
		t.Fatalf("bot did not return the turn: %#v", view)
	}
	if len(view.LastMoves) < 2 {
		t.Fatalf("expected player and bot moves for animation, got %#v", view.LastMoves)
	}
	if view.Board[0] == initialBoard()[0] && view.Board[1] == initialBoard()[1] && view.Board[2] == initialBoard()[2] {
		t.Fatal("bot did not move a blue piece")
	}
}

func TestPublicCheckersMatchmaking(t *testing.T) {
	manager := newRoomManager()
	first := telegramUser{ID: 1, FirstName: "First"}
	second := telegramUser{ID: 2, FirstName: "Second"}

	waiting, err := manager.matchPublic(first)
	if err != nil {
		t.Fatal(err)
	}
	if !waiting.Public || waiting.Status != "waiting" || waiting.You != "red" {
		t.Fatalf("unexpected public lobby: %#v", waiting)
	}
	joined, err := manager.matchPublic(second)
	if err != nil {
		t.Fatal(err)
	}
	if joined.Code != waiting.Code || joined.Status != "active" || joined.You != "blue" {
		t.Fatalf("players were not matched: %#v", joined)
	}
	firstView, err := manager.state(waiting.Code, first.ID)
	if err != nil || firstView.Blue == nil || firstView.Blue.Name != "Second" {
		t.Fatalf("first player did not see opponent: view=%#v err=%v", firstView, err)
	}
}

func TestEnginePrefersCapturingKing(t *testing.T) {
	var board [8][8]string
	board[2][1] = blueMan
	board[3][2] = redKing
	board[2][5] = blueMan
	board[3][6] = redMan

	moves := legalMoves(board, "blue", nil)
	if len(moves) != 2 {
		t.Fatalf("expected two captures, got %#v", moves)
	}
	move := chooseBotMove(board, moves)
	want := checkerMove{From: position{Row: 2, Col: 1}, To: position{Row: 4, Col: 3}}
	if move != want {
		t.Fatalf("engine chose %#v instead of the king capture %#v", move, want)
	}
}
