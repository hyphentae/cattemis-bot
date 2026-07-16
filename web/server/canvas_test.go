package main

import (
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func TestCanvasPlacementCooldownAndPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "canvas.json")
	manager := newCanvasManager(path)
	now := time.Date(2026, 7, 16, 10, 0, 0, 0, time.UTC)
	manager.now = func() time.Time { return now }

	placed, err := manager.place(7, 12, 23, 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(placed.Changes) != 1 || placed.Changes[0].Color != 5 || placed.Version != 2 {
		t.Fatalf("pixel was not placed: %#v", placed)
	}
	if _, err := manager.place(7, 13, 23, 6); err == nil {
		t.Fatal("expected placement cooldown")
	} else {
		var cooldown canvasCooldownError
		if !errors.As(err, &cooldown) || cooldown.RetryAfter != canvasCooldown {
			t.Fatalf("unexpected cooldown error: %v", err)
		}
	}

	now = now.Add(canvasCooldown)
	if _, err := manager.place(7, 13, 23, 6); err != nil {
		t.Fatal(err)
	}
	delta := manager.view(99, 2)
	if delta.Pixels != "" || len(delta.Changes) != 1 || delta.Changes[0].Color != 6 {
		t.Fatalf("expected one incremental pixel update, got %#v", delta)
	}
	reloaded := newCanvasManager(path)
	view := reloaded.view(99, 0)
	if view.Pixels[23*canvasWidth+12] != '5' || view.Pixels[23*canvasWidth+13] != '6' {
		t.Fatalf("saved canvas was not restored")
	}
}

func TestCanvasRejectsInvalidPlacement(t *testing.T) {
	manager := newCanvasManager(filepath.Join(t.TempDir(), "canvas.json"))
	if _, err := manager.place(1, -1, 0, 1); !errors.Is(err, errCanvasPosition) {
		t.Fatalf("expected position error, got %v", err)
	}
	if _, err := manager.place(1, 0, 0, canvasColors); !errors.Is(err, errCanvasColor) {
		t.Fatalf("expected color error, got %v", err)
	}
}
