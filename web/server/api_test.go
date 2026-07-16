package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"testing"
	"time"
)

func TestCreateAndJoinRoomAPI(t *testing.T) {
	const token = "123456:test-token"
	now := time.Now().Unix()
	server := newServer(token)

	first := signedInitData(t, token, now, 1, "Red")
	createRequest := httptest.NewRequest(http.MethodPost, "/api/checkers/create", nil)
	createRequest.Header.Set("X-Telegram-Init-Data", first)
	createResponse := httptest.NewRecorder()
	server.createRoom(createResponse, createRequest)
	if createResponse.Code != http.StatusOK {
		t.Fatalf("create failed: %d %s", createResponse.Code, createResponse.Body.String())
	}
	var created roomView
	if err := json.NewDecoder(createResponse.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if len(created.Code) != 6 || created.Status != "waiting" || created.You != "red" {
		t.Fatalf("unexpected created room: %#v", created)
	}

	second := signedInitData(t, token, now, 2, "Blue")
	body, _ := json.Marshal(map[string]string{"code": created.Code})
	joinRequest := httptest.NewRequest(http.MethodPost, "/api/checkers/join", bytes.NewReader(body))
	joinRequest.Header.Set("X-Telegram-Init-Data", second)
	joinResponse := httptest.NewRecorder()
	server.joinRoom(joinResponse, joinRequest)
	if joinResponse.Code != http.StatusOK {
		t.Fatalf("join failed: %d %s", joinResponse.Code, joinResponse.Body.String())
	}
	var joined roomView
	if err := json.NewDecoder(joinResponse.Body).Decode(&joined); err != nil {
		t.Fatal(err)
	}
	if joined.Status != "active" || joined.You != "blue" || joined.Blue == nil {
		t.Fatalf("unexpected joined room: %#v", joined)
	}
}

func TestCheckersAPIRequiresTelegramSignature(t *testing.T) {
	server := newServer("token")
	request := httptest.NewRequest(http.MethodPost, "/api/checkers/create", nil)
	response := httptest.NewRecorder()
	server.createRoom(response, request)
	if response.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", response.Code)
	}
}

func TestCreateBotGameAPI(t *testing.T) {
	const token = "123456:test-token"
	server := newServer(token)
	initData := signedInitData(t, token, time.Now().Unix(), 7, "Player")
	request := httptest.NewRequest(http.MethodPost, "/api/checkers/create-bot", nil)
	request.Header.Set("X-Telegram-Init-Data", initData)
	response := httptest.NewRecorder()

	server.createBotGame(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("create bot game failed: %d %s", response.Code, response.Body.String())
	}
	var created roomView
	if err := json.NewDecoder(response.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if !created.Bot || created.Status != "active" || created.Blue == nil || created.Blue.Name != "катемис" {
		t.Fatalf("unexpected bot game: %#v", created)
	}
}

func TestCheckersAPIAcceptsGameAuthToken(t *testing.T) {
	const token = "123456:test-token"
	server := newServer(token)
	gameToken := signGameToken(t, map[string]any{
		"id": 9, "first_name": "Game Player", "auth_date": time.Now().Unix(),
	}, token)
	request := httptest.NewRequest(http.MethodPost, "/api/checkers/create", nil)
	request.Header.Set("X-Telegram-Game-Auth", gameToken)
	response := httptest.NewRecorder()

	server.createRoom(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("game auth was rejected: %d %s", response.Code, response.Body.String())
	}
}

func signedInitData(t *testing.T, token string, authDate, id int64, name string) string {
	t.Helper()
	userJSON, err := json.Marshal(telegramUser{ID: id, FirstName: name})
	if err != nil {
		t.Fatal(err)
	}
	values := url.Values{
		"auth_date": {strconv.FormatInt(authDate, 10)},
		"user":      {string(userJSON)},
	}
	values.Set("hash", signInitData(values, token))
	return values.Encode()
}
