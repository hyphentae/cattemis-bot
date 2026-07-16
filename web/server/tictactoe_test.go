package main

import "testing"

func TestOnlineTicTacToeFlow(t *testing.T) {
	m := newTicTacToeManager()
	first := telegramUser{ID: 1, FirstName: "X"}
	second := telegramUser{ID: 2, FirstName: "O"}
	waiting, err := m.create(first)
	if err != nil { t.Fatal(err) }
	joined, err := m.join(waiting.Code, second)
	if err != nil || joined.Status != "active" || joined.You != "o" { t.Fatalf("join failed: %#v %v", joined, err) }
	for _, move := range []struct{id int64; cell int}{{1,0},{2,3},{1,1},{2,4},{1,2}} {
		if _, err := m.move(waiting.Code, move.id, move.cell); err != nil { t.Fatal(err) }
	}
	finished, err := m.state(waiting.Code, first.ID)
	if err != nil || finished.Status != "finished" || finished.Winner != "x" { t.Fatalf("winner missing: %#v %v", finished, err) }
}
