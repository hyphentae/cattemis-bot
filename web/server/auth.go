package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"
)

var errUnauthorized = errors.New("не удалось подтвердить пользователя Telegram")

const gameAuthPrefix = "catemis-game-v1"

type telegramUser struct {
	ID        int64  `json:"id"`
	FirstName string `json:"first_name"`
	LastName  string `json:"last_name"`
	Username  string `json:"username"`
}

func (u telegramUser) displayName() string {
	name := strings.TrimSpace(u.FirstName + " " + u.LastName)
	if name == "" && u.Username != "" {
		return "@" + u.Username
	}
	if name == "" {
		return "Игрок"
	}
	return name
}

func validateTelegramInitData(raw, botToken string, now time.Time) (telegramUser, error) {
	if raw == "" || botToken == "" {
		return telegramUser{}, errUnauthorized
	}

	values, err := url.ParseQuery(raw)
	if err != nil {
		return telegramUser{}, errUnauthorized
	}

	receivedHash, err := hex.DecodeString(values.Get("hash"))
	if err != nil || len(receivedHash) != sha256.Size {
		return telegramUser{}, errUnauthorized
	}

	keys := make([]string, 0, len(values))
	for key := range values {
		if key != "hash" {
			keys = append(keys, key)
		}
	}
	sort.Strings(keys)

	parts := make([]string, 0, len(keys))
	for _, key := range keys {
		parts = append(parts, key+"="+values.Get(key))
	}
	dataCheckString := strings.Join(parts, "\n")

	secretMAC := hmac.New(sha256.New, []byte("WebAppData"))
	_, _ = secretMAC.Write([]byte(botToken))
	secretKey := secretMAC.Sum(nil)

	dataMAC := hmac.New(sha256.New, secretKey)
	_, _ = dataMAC.Write([]byte(dataCheckString))
	expectedHash := dataMAC.Sum(nil)
	if subtle.ConstantTimeCompare(receivedHash, expectedHash) != 1 {
		return telegramUser{}, errUnauthorized
	}

	authUnix, err := strconv.ParseInt(values.Get("auth_date"), 10, 64)
	if err != nil {
		return telegramUser{}, errUnauthorized
	}
	authTime := time.Unix(authUnix, 0)
	if now.Sub(authTime) > 24*time.Hour || authTime.After(now.Add(5*time.Minute)) {
		return telegramUser{}, errUnauthorized
	}

	var user telegramUser
	if err := json.Unmarshal([]byte(values.Get("user")), &user); err != nil || user.ID == 0 {
		return telegramUser{}, errUnauthorized
	}
	return user, nil
}

func validateGameAuthToken(raw, botToken string, now time.Time) (telegramUser, error) {
	if raw == "" || botToken == "" {
		return telegramUser{}, errUnauthorized
	}
	parts := strings.Split(raw, ".")
	if len(parts) != 2 {
		return telegramUser{}, errUnauthorized
	}
	payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return telegramUser{}, errUnauthorized
	}
	receivedSignature, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil || len(receivedSignature) != sha256.Size {
		return telegramUser{}, errUnauthorized
	}

	mac := hmac.New(sha256.New, []byte(botToken))
	_, _ = mac.Write([]byte(gameAuthPrefix + "." + parts[0]))
	if subtle.ConstantTimeCompare(receivedSignature, mac.Sum(nil)) != 1 {
		return telegramUser{}, errUnauthorized
	}

	var payload struct {
		telegramUser
		AuthDate int64 `json:"auth_date"`
	}
	if err := json.Unmarshal(payloadBytes, &payload); err != nil || payload.ID == 0 {
		return telegramUser{}, errUnauthorized
	}
	authTime := time.Unix(payload.AuthDate, 0)
	if now.Sub(authTime) > 24*time.Hour || authTime.After(now.Add(5*time.Minute)) {
		return telegramUser{}, errUnauthorized
	}
	return payload.telegramUser, nil
}
