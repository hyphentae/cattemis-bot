package main

import (
	"path/filepath"
	"testing"
)

func TestLeaderboardKeepsPersonalBestAndPersists(t *testing.T) {
	path := filepath.Join(t.TempDir(), "leaderboard.json")
	manager := newLeaderboardManager(path)
	user := telegramUser{ID: 7, FirstName: "Player"}

	if _, err := manager.submit(user, "sudoku", "easy", 90, 2); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.submit(user, "sudoku", "easy", 110, 0); err != nil {
		t.Fatal(err)
	}
	view, err := newLeaderboardManager(path).view("sudoku", "easy")
	if err != nil {
		t.Fatal(err)
	}
	if len(view.Entries) != 1 || view.Entries[0].Seconds != 90 || view.Entries[0].Name != "Player" {
		t.Fatalf("unexpected leaderboard: %#v", view)
	}
}

func TestLeaderboardSortsAndValidates(t *testing.T) {
	manager := newLeaderboardManager(filepath.Join(t.TempDir(), "leaderboard.json"))
	_, _ = manager.submit(telegramUser{ID: 1, FirstName: "Slow"}, "minesweeper", "hard", 80, 0)
	view, err := manager.submit(telegramUser{ID: 2, FirstName: "Fast"}, "minesweeper", "hard", 40, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(view.Entries) != 2 || view.Entries[0].Name != "Fast" {
		t.Fatalf("leaderboard is not sorted: %#v", view)
	}
	if _, err := manager.submit(telegramUser{ID: 3}, "unknown", "easy", 10, 0); err == nil {
		t.Fatal("expected invalid game error")
	}
}
