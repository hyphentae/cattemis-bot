package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sync"
	"time"
)

const (
	canvasWidth       = 1000
	canvasHeight      = 1000
	canvasCooldown    = 10 * time.Second
	canvasColors      = 16
	canvasChangeLimit = 5000
)

var (
	errCanvasPosition = errors.New("такой точки на холсте нет")
	errCanvasColor    = errors.New("такого цвета в палитре нет")
)

type canvasCooldownError struct{ RetryAfter time.Duration }

func (e canvasCooldownError) Error() string {
	return "лапкам нужно немного отдохнуть"
}

type canvasState struct {
	Pixels  string `json:"pixels"`
	Version int64  `json:"version"`
}

type canvasView struct {
	Width      int            `json:"width"`
	Height     int            `json:"height"`
	Pixels     string         `json:"pixels,omitempty"`
	Changes    []canvasChange `json:"changes,omitempty"`
	Version    int64          `json:"version"`
	CooldownMS int64          `json:"cooldown_ms"`
}

type canvasChange struct {
	X       int   `json:"x"`
	Y       int   `json:"y"`
	Color   int   `json:"color"`
	Version int64 `json:"version"`
}

type canvasManager struct {
	mu        sync.Mutex
	path      string
	pixels    []byte
	version   int64
	changes   []canvasChange
	lastPlace map[int64]time.Time
	now       func() time.Time
}

func newCanvasManager(path string) *canvasManager {
	m := &canvasManager{
		path: path, pixels: make([]byte, canvasWidth*canvasHeight), version: 1,
		lastPlace: make(map[int64]time.Time), now: time.Now,
	}
	for index := range m.pixels {
		m.pixels[index] = '0'
	}
	if err := m.load(); err != nil && !errors.Is(err, os.ErrNotExist) {
		fmt.Fprintf(os.Stderr, "[web] canvas load failed: %v\n", err)
	}
	return m
}

func (m *canvasManager) view(userID, since int64) canvasView {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.viewLocked(userID, since)
}

func (m *canvasManager) place(userID int64, x, y, color int) (canvasView, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if x < 0 || x >= canvasWidth || y < 0 || y >= canvasHeight {
		return canvasView{}, errCanvasPosition
	}
	if color < 0 || color >= canvasColors {
		return canvasView{}, errCanvasColor
	}
	now := m.now()
	if last := m.lastPlace[userID]; !last.IsZero() {
		remaining := canvasCooldown - now.Sub(last)
		if remaining > 0 {
			return canvasView{}, canvasCooldownError{RetryAfter: remaining}
		}
	}

	index := y*canvasWidth + x
	previous := m.pixels[index]
	previousVersion := m.version
	m.pixels[index] = "0123456789abcdef"[color]
	m.version++
	m.changes = append(m.changes, canvasChange{X: x, Y: y, Color: color, Version: m.version})
	if len(m.changes) > canvasChangeLimit {
		m.changes = m.changes[len(m.changes)-canvasChangeLimit:]
	}
	if err := m.saveLocked(); err != nil {
		m.pixels[index] = previous
		m.version = previousVersion
		m.changes = m.changes[:len(m.changes)-1]
		return canvasView{}, err
	}
	m.lastPlace[userID] = now
	return m.viewLocked(userID, previousVersion), nil
}

func (m *canvasManager) viewLocked(userID, since int64) canvasView {
	var cooldown int64
	if remaining := canvasCooldown - m.now().Sub(m.lastPlace[userID]); remaining > 0 {
		cooldown = remaining.Milliseconds()
	}
	view := canvasView{
		Width: canvasWidth, Height: canvasHeight, Version: m.version, CooldownMS: cooldown,
	}
	if since == m.version {
		return view
	}
	if since > 0 && len(m.changes) > 0 && since >= m.changes[0].Version-1 {
		for _, change := range m.changes {
			if change.Version > since {
				view.Changes = append(view.Changes, change)
			}
		}
		return view
	}
	view.Pixels = string(m.pixels)
	return view
}

func (m *canvasManager) load() error {
	data, err := os.ReadFile(m.path)
	if err != nil {
		return err
	}
	var stored canvasState
	if err := json.Unmarshal(data, &stored); err != nil {
		return err
	}
	for _, color := range []byte(stored.Pixels) {
		if !((color >= '0' && color <= '9') || (color >= 'a' && color <= 'f')) {
			return errors.New("неверный цвет в сохранённом холсте")
		}
	}
	if len(stored.Pixels) == canvasWidth*canvasHeight {
		copy(m.pixels, stored.Pixels)
	} else {
		oldSize := int(math.Sqrt(float64(len(stored.Pixels))))
		if oldSize*oldSize != len(stored.Pixels) || oldSize > canvasWidth || oldSize > canvasHeight {
			return errors.New("неверный размер сохранённого холста")
		}
		offsetX, offsetY := (canvasWidth-oldSize)/2, (canvasHeight-oldSize)/2
		for y := 0; y < oldSize; y++ {
			copy(
				m.pixels[(offsetY+y)*canvasWidth+offsetX:(offsetY+y)*canvasWidth+offsetX+oldSize],
				stored.Pixels[y*oldSize:(y+1)*oldSize],
			)
		}
	}
	if stored.Version > 0 {
		m.version = stored.Version
	}
	return nil
}

func (m *canvasManager) saveLocked() error {
	if err := os.MkdirAll(filepath.Dir(m.path), 0o755); err != nil {
		return err
	}
	data, err := json.Marshal(canvasState{Pixels: string(m.pixels), Version: m.version})
	if err != nil {
		return err
	}
	temporary := m.path + ".tmp"
	if err := os.WriteFile(temporary, data, 0o644); err != nil {
		return err
	}
	return os.Rename(temporary, m.path)
}
