package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"net/url"
	"sort"
	"strings"
	"testing"
	"time"
)

func TestValidateTelegramInitData(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	token := "123456:test-token"
	values := url.Values{
		"auth_date": {"1700000000"},
		"query_id":  {"query"},
		"user":      {`{"id":42,"first_name":"Cat"}`},
	}
	values.Set("hash", signInitData(values, token))

	user, err := validateTelegramInitData(values.Encode(), token, now)
	if err != nil {
		t.Fatal(err)
	}
	if user.ID != 42 || user.FirstName != "Cat" {
		t.Fatalf("unexpected user: %#v", user)
	}
}

func TestRejectsExpiredTelegramInitData(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	token := "123456:test-token"
	values := url.Values{
		"auth_date": {"1699800000"},
		"user":      {`{"id":42,"first_name":"Cat"}`},
	}
	values.Set("hash", signInitData(values, token))

	if _, err := validateTelegramInitData(values.Encode(), token, now); err == nil {
		t.Fatal("expected expired init data to be rejected")
	}
}

func TestValidateGameAuthToken(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	token := signGameToken(t, map[string]any{
		"id": 42, "first_name": "Cat", "auth_date": now.Unix(),
	}, "123456:test-token")

	user, err := validateGameAuthToken(token, "123456:test-token", now)
	if err != nil {
		t.Fatal(err)
	}
	if user.ID != 42 || user.FirstName != "Cat" {
		t.Fatalf("unexpected game user: %#v", user)
	}
}

func TestValidatePythonGameAuthToken(t *testing.T) {
	const token = "eyJpZCI6NDIsImZpcnN0X25hbWUiOiJDYXQiLCJsYXN0X25hbWUiOiIiLCJ1c2VybmFtZSI6IiIsImNoYXRfaW5zdGFuY2UiOiIiLCJhdXRoX2RhdGUiOjE3MDAwMDAwMDB9.S0TZzSLwsY1QB5-xvZe0Gf52I6KrHFZLiqDPHztdELM"
	user, err := validateGameAuthToken(token, "123456:test-token", time.Unix(1_700_000_000, 0))
	if err != nil || user.ID != 42 || user.FirstName != "Cat" {
		t.Fatalf("Python game token was not accepted: user=%#v err=%v", user, err)
	}
}

func TestRejectsTamperedGameAuthToken(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	token := signGameToken(t, map[string]any{
		"id": 42, "first_name": "Cat", "auth_date": now.Unix(),
	}, "123456:test-token")
	if _, err := validateGameAuthToken(token+"x", "123456:test-token", now); err == nil {
		t.Fatal("expected tampered game token to be rejected")
	}
}

func signInitData(values url.Values, token string) string {
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

	secretMAC := hmac.New(sha256.New, []byte("WebAppData"))
	_, _ = secretMAC.Write([]byte(token))
	dataMAC := hmac.New(sha256.New, secretMAC.Sum(nil))
	_, _ = dataMAC.Write([]byte(strings.Join(parts, "\n")))
	return hex.EncodeToString(dataMAC.Sum(nil))
}

func signGameToken(t *testing.T, payload map[string]any, token string) string {
	t.Helper()
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	encoded := base64.RawURLEncoding.EncodeToString(raw)
	mac := hmac.New(sha256.New, []byte(token))
	_, _ = mac.Write([]byte(gameAuthPrefix + "." + encoded))
	return encoded + "." + base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
}
