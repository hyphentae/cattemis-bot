package config

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	BotToken            string
	APIFYToken          string
	APIFYInstagramActor string
	DonateURL           string
	AllowedLinksFile    string
	WebAppURL           string
	WebAppURLFile       string
	YTDownloadPath      string
	YTDownloadCookies   string
	YTDownloadBrowser   string
	RedditUserAgent     string
	MaxMediaItems       int
	MaxFileSize         int64
	RetryAttempts       int
	RetryDelay          time.Duration
	AdminCacheTTL       time.Duration
	LLMEnabled          bool
	LLMBaseURL          string
	LLMAPIKey           string
	LLMModel            string
	LLMSystemPrompt     string
	LLMCooldown         time.Duration
	LLMTimeout          time.Duration
	LLMMaxTokens        int
	LLMTemperature      float64
	LLMMaxHistory       int
	LLMHistoryFile      string
	LLMWebSearch        bool
	LLMWebSearchResults int
	LLMTimezone         string
	LLMVision           bool
	LLMVideoFrames      int
	WhisperEnabled      bool
	WhisperPath         string
	WhisperModel        string
	WhisperLanguage     string
}

func Load() (Config, error) {
	_ = loadDotEnv(".env")
	cfg := Config{
		BotToken:            firstEnv("BOT_TOKEN", "TELEGRAM_BOT_TOKEN"),
		APIFYToken:          firstEnv("APIFY_TOKEN", "APIFY_API_TOKEN"),
		APIFYInstagramActor: envString("APIFY_INSTAGRAM_ACTOR", "elis~instagram-downloader-api"),
		DonateURL:           firstEnv("KOFI_URL", "DONATE_URL"),
		AllowedLinksFile:    envString("ALLOWED_LINKS_FILE", ".cattemis-allowed-links.json"),
		WebAppURL:           strings.TrimSpace(os.Getenv("TELEGRAM_WEBAPP_URL")),
		WebAppURLFile:       envString("TELEGRAM_WEBAPP_URL_FILE", "/tunnel/url.txt"),
		YTDownloadPath:      envString("YTDLP_PATH", "yt-dlp"),
		YTDownloadCookies:   strings.TrimSpace(os.Getenv("YTDLP_COOKIES_FILE")),
		YTDownloadBrowser:   strings.TrimSpace(os.Getenv("YTDLP_COOKIES_FROM_BROWSER")),
		RedditUserAgent:     envString("REDDIT_USER_AGENT", "linux:cattemis-bot:1.0"),
		MaxMediaItems:       envInt("MAX_MEDIA_ITEMS", 50, 1, 100),
		MaxFileSize:         envInt64("MAX_FILE_SIZE", 50*1024*1024, 1024, 2*1024*1024*1024),
		RetryAttempts:       envInt("RETRY_ATTEMPTS", 3, 1, 10),
		RetryDelay:          envDurationSeconds("RETRY_DELAY", 1200*time.Millisecond),
		AdminCacheTTL:       envDurationSeconds("ADMIN_CACHE_TTL", 60*time.Second),
		LLMEnabled:          envBool("LLM_ENABLED", false),
		LLMBaseURL:          strings.TrimRight(envString("LLM_BASE_URL", "https://openrouter.ai/api/v1"), "/"),
		LLMAPIKey:           strings.TrimSpace(os.Getenv("LLM_API_KEY")),
		LLMModel:            strings.TrimSpace(os.Getenv("LLM_MODEL")),
		LLMSystemPrompt:     strings.TrimSpace(os.Getenv("LLM_SYSTEM_PROMPT")),
		LLMCooldown:         envDurationSeconds("LLM_COOLDOWN_SECONDS", 0),
		LLMTimeout:          envDurationSeconds("LLM_REQUEST_TIMEOUT_SECONDS", 120*time.Second),
		LLMMaxTokens:        envInt("LLM_MAX_TOKENS", 480, 1, 65536),
		LLMTemperature:      envFloat("LLM_TEMPERATURE", 0.6, 0, 2),
		LLMMaxHistory:       envInt("LLM_MAX_HISTORY_MESSAGES", 8, 0, 100),
		LLMHistoryFile:      envString("LLM_HISTORY_FILE", ".cattemis-llm-history.json"),
		LLMWebSearch:        envBool("LLM_WEB_SEARCH_ENABLED", false),
		LLMWebSearchResults: envInt("LLM_WEB_SEARCH_MAX_RESULTS", 5, 1, 10),
		LLMTimezone:         firstNonEmpty(os.Getenv("LLM_TIMEZONE"), os.Getenv("LLM_TIMEZONE_OFFSET"), "Asia/Almaty"),
		LLMVision:           envBool("LLM_VISION_ENABLED", true),
		LLMVideoFrames:      envInt("LLM_VIDEO_FRAME_COUNT", 3, 1, 6),
		WhisperEnabled:      envBool("WHISPER_ENABLED", false),
		WhisperPath:         envString("WHISPER_PATH", "whisper"),
		WhisperModel:        envString("WHISPER_MODEL_SIZE", "base"),
		WhisperLanguage:     envString("WHISPER_LANGUAGE", "auto"),
	}
	if cfg.BotToken == "" {
		return Config{}, errors.New("BOT_TOKEN is required")
	}
	if cfg.LLMEnabled && (cfg.LLMAPIKey == "" || cfg.LLMModel == "") {
		return Config{}, errors.New("LLM_ENABLED requires LLM_API_KEY and LLM_MODEL")
	}
	return cfg, nil
}

func (c Config) CurrentWebAppURL() string {
	if strings.HasPrefix(c.WebAppURL, "https://") {
		return strings.TrimRight(c.WebAppURL, "/")
	}
	data, err := os.ReadFile(c.WebAppURLFile)
	if err != nil {
		return ""
	}
	value := strings.TrimSpace(string(data))
	if !strings.HasPrefix(value, "https://") {
		return ""
	}
	return strings.TrimRight(value, "/")
}

func loadDotEnv(path string) error {
	file, err := os.Open(filepath.Clean(path))
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		key = strings.TrimSpace(strings.TrimPrefix(key, "export "))
		value = strings.TrimSpace(value)
		if len(value) >= 2 && ((value[0] == '"' && value[len(value)-1] == '"') || (value[0] == '\'' && value[len(value)-1] == '\'')) {
			value = value[1 : len(value)-1]
		}
		if key != "" {
			if _, exists := os.LookupEnv(key); !exists {
				_ = os.Setenv(key, value)
			}
		}
	}
	return scanner.Err()
}

func firstEnv(names ...string) string {
	for _, name := range names {
		if value := strings.TrimSpace(os.Getenv(name)); value != "" {
			return value
		}
	}
	return ""
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value = strings.TrimSpace(value); value != "" {
			return value
		}
	}
	return ""
}

func envString(name, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}

func envBool(name string, fallback bool) bool {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func envInt(name string, fallback, minimum, maximum int) int {
	value, err := strconv.Atoi(strings.TrimSpace(os.Getenv(name)))
	if err != nil || value < minimum || value > maximum {
		return fallback
	}
	return value
}

func envInt64(name string, fallback, minimum, maximum int64) int64 {
	value, err := strconv.ParseInt(strings.TrimSpace(os.Getenv(name)), 10, 64)
	if err != nil || value < minimum || value > maximum {
		return fallback
	}
	return value
}

func envFloat(name string, fallback, minimum, maximum float64) float64 {
	value, err := strconv.ParseFloat(strings.TrimSpace(os.Getenv(name)), 64)
	if err != nil || value < minimum || value > maximum {
		return fallback
	}
	return value
}

func envDurationSeconds(name string, fallback time.Duration) time.Duration {
	raw := strings.TrimSpace(os.Getenv(name))
	if raw == "" {
		return fallback
	}
	value, err := strconv.ParseFloat(raw, 64)
	if err != nil || value < 0 {
		return fallback
	}
	return time.Duration(value * float64(time.Second))
}

func (c Config) String() string {
	return fmt.Sprintf("llm=%t model=%q web_search=%t vision=%t whisper=%t", c.LLMEnabled, c.LLMModel, c.LLMWebSearch, c.LLMVision, c.WhisperEnabled)
}
