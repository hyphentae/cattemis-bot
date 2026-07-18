package main

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

const leaderboardLimit = 20

var errInvalidLeaderboardScore = errors.New("некорректный результат")

type leaderboardEntry struct {
	UserID    int64  `json:"user_id,omitempty"`
	Name      string `json:"name"`
	Seconds   int    `json:"seconds"`
	Mistakes  int    `json:"mistakes,omitempty"`
	CreatedAt int64  `json:"created_at"`
}

type leaderboardView struct {
	Game       string             `json:"game"`
	Difficulty string             `json:"difficulty"`
	Entries    []leaderboardEntry `json:"entries"`
}

type leaderboardManager struct {
	mu      sync.Mutex
	path    string
	entries map[string][]leaderboardEntry
}

func newLeaderboardManager(path string) *leaderboardManager {
	m := &leaderboardManager{path: path, entries: make(map[string][]leaderboardEntry)}
	_ = m.load()
	return m
}

func leaderboardKey(game, difficulty string) (string, error) {
	if game != "minesweeper" && game != "sudoku" {
		return "", errInvalidLeaderboardScore
	}
	if difficulty != "easy" && difficulty != "medium" && difficulty != "hard" {
		return "", errInvalidLeaderboardScore
	}
	return game + ":" + difficulty, nil
}

func (m *leaderboardManager) view(game, difficulty string) (leaderboardView, error) {
	key, err := leaderboardKey(game, difficulty)
	if err != nil {
		return leaderboardView{}, err
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	return leaderboardView{Game: game, Difficulty: difficulty, Entries: publicLeaderboardEntries(m.entries[key])}, nil
}

func (m *leaderboardManager) submit(user telegramUser, game, difficulty string, seconds, mistakes int) (leaderboardView, error) {
	key, err := leaderboardKey(game, difficulty)
	if err != nil || seconds < 1 || seconds > 86400 || mistakes < 0 || mistakes > 999 {
		return leaderboardView{}, errInvalidLeaderboardScore
	}
	if game == "minesweeper" && mistakes != 0 {
		return leaderboardView{}, errInvalidLeaderboardScore
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	entries := m.entries[key]
	candidate := leaderboardEntry{UserID: user.ID, Name: user.displayName(), Seconds: seconds, Mistakes: mistakes, CreatedAt: time.Now().Unix()}
	replaced := false
	for index, entry := range entries {
		if entry.UserID != user.ID {
			continue
		}
		replaced = true
		if betterScore(candidate, entry) {
			entries[index] = candidate
		}
		break
	}
	if !replaced {
		entries = append(entries, candidate)
	}
	sort.SliceStable(entries, func(i, j int) bool { return betterScore(entries[i], entries[j]) })
	if len(entries) > leaderboardLimit {
		entries = entries[:leaderboardLimit]
	}
	m.entries[key] = entries
	if err := m.saveLocked(); err != nil {
		return leaderboardView{}, err
	}
	return leaderboardView{Game: game, Difficulty: difficulty, Entries: publicLeaderboardEntries(entries)}, nil
}

func publicLeaderboardEntries(entries []leaderboardEntry) []leaderboardEntry {
	public := append([]leaderboardEntry(nil), entries...)
	for index := range public {
		public[index].UserID = 0
	}
	return public
}

func betterScore(left, right leaderboardEntry) bool {
	if left.Seconds != right.Seconds {
		return left.Seconds < right.Seconds
	}
	if left.Mistakes != right.Mistakes {
		return left.Mistakes < right.Mistakes
	}
	return left.CreatedAt < right.CreatedAt
}

func (m *leaderboardManager) load() error {
	data, err := os.ReadFile(m.path)
	if err != nil {
		return err
	}
	var entries map[string][]leaderboardEntry
	if err := json.Unmarshal(data, &entries); err != nil {
		return err
	}
	if entries == nil {
		entries = make(map[string][]leaderboardEntry)
	}
	m.entries = entries
	return nil
}

func (m *leaderboardManager) saveLocked() error {
	if err := os.MkdirAll(filepath.Dir(m.path), 0o755); err != nil {
		return err
	}
	data, err := json.Marshal(m.entries)
	if err != nil {
		return err
	}
	temporary := m.path + ".tmp"
	if err := os.WriteFile(temporary, data, 0o644); err != nil {
		return err
	}
	return os.Rename(temporary, m.path)
}
