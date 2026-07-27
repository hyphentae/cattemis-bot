package llm

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
	_ "time/tzdata"

	"github.com/hyphentae/cattemis-bot/internal/config"
	"github.com/hyphentae/cattemis-bot/resources"
)

const maxAgentSteps = 3

type Image struct {
	MIME string
	Data []byte
}

type Request struct {
	ChatID      int64
	UserName    string
	Text        string
	Images      []Image
	Transcripts []string
}

type Client struct {
	cfg     config.Config
	http    *http.Client
	mu      sync.Mutex
	history map[int64][]chatMessage
}

type chatMessage struct {
	Role       string     `json:"role"`
	Content    any        `json:"content,omitempty"`
	ToolCalls  []toolCall `json:"tool_calls,omitempty"`
	ToolCallID string     `json:"tool_call_id,omitempty"`
	Name       string     `json:"name,omitempty"`
}

type toolCall struct {
	ID       string       `json:"id"`
	Type     string       `json:"type"`
	Function toolFunction `json:"function"`
}

type toolFunction struct {
	Name      string `json:"name"`
	Arguments any    `json:"arguments"`
}

type completionResponse struct {
	Choices []struct {
		FinishReason string `json:"finish_reason"`
		Message      struct {
			Role      string     `json:"role"`
			Content   string     `json:"content"`
			ToolCalls []toolCall `json:"tool_calls"`
		} `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
		Type    string `json:"type"`
		Code    any    `json:"code"`
	} `json:"error,omitempty"`
}

func New(cfg config.Config) *Client {
	return &Client{
		cfg: cfg,
		http: &http.Client{
			Timeout: cfg.LLMTimeout,
		},
		history: make(map[int64][]chatMessage),
	}
}

func (c *Client) Enabled() bool {
	return c.cfg.LLMEnabled
}

func (c *Client) Reset(chatID int64) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	_, exists := c.history[chatID]
	delete(c.history, chatID)
	return exists
}

func (c *Client) Ask(ctx context.Context, request Request) (string, error) {
	if !c.cfg.LLMEnabled {
		return "", errors.New("LLM is disabled")
	}
	started := time.Now()
	userName := strings.TrimSpace(request.UserName)
	if userName == "" {
		userName = resources.Get("llm.default_user_name")
	}
	text := strings.TrimSpace(request.Text)
	if text == "" {
		switch {
		case len(request.Images) > 0:
			text = resources.Get("llm.prompt.images_only")
		case len(request.Transcripts) > 0:
			text = resources.Get("llm.prompt.audio_only")
		default:
			return "", errors.New("empty LLM request")
		}
	}
	userText := userName + ": " + text
	if len(request.Transcripts) > 0 {
		userText += resources.Get("llm.prompt.media_transcript_heading")
		for index, transcript := range request.Transcripts {
			userText += resources.Format("llm.prompt.audio_transcript", map[string]any{
				"index": index + 1, "transcript": transcript,
			}) + "\n\n"
		}
	}

	var content any = userText
	if len(request.Images) > 0 {
		parts := []map[string]any{{"type": "text", "text": userText}}
		for _, image := range request.Images {
			if len(image.Data) == 0 {
				continue
			}
			mimeType := image.MIME
			if mimeType == "" {
				mimeType = "image/jpeg"
			}
			parts = append(parts, map[string]any{
				"type": "image_url",
				"image_url": map[string]string{
					"url": "data:" + mimeType + ";base64," + base64.StdEncoding.EncodeToString(image.Data),
				},
			})
		}
		content = parts
	}

	systemPrompt := c.cfg.LLMSystemPrompt
	if systemPrompt == "" {
		systemPrompt = resources.Get("llm.default_system_prompt")
	}
	systemPrompt += "\n\n" + currentTime(c.cfg.LLMTimezone) + resources.Get("llm.prompt.current_date_instruction")
	if c.cfg.LLMWebSearch {
		systemPrompt += resources.Get("llm.prompt.web_search_instruction")
	}

	c.mu.Lock()
	history := append([]chatMessage(nil), c.history[request.ChatID]...)
	c.mu.Unlock()
	messages := []chatMessage{{Role: "system", Content: systemPrompt}}
	messages = append(messages, history...)
	messages = append(messages, chatMessage{Role: "user", Content: content})
	if c.cfg.LLMCooldown > 0 {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		case <-time.After(c.cfg.LLMCooldown):
		}
	}

	tools := []map[string]any{currentTimeTool()}
	if c.cfg.LLMWebSearch {
		tools = append(tools, webSearchTool())
	}
	var response completionResponse
	searchCache := map[string]string{}
	for step := 0; step < maxAgentSteps; step++ {
		var err error
		response, err = c.complete(ctx, messages, tools, true)
		if err != nil {
			if step == 0 {
				log.Printf("[llm] request with tools failed, retrying without tools: %v", err)
				response, err = c.complete(ctx, messages, nil, false)
			}
			if err != nil {
				return "", err
			}
		}
		if len(response.Choices) == 0 {
			return "", errors.New("LLM returned no choices")
		}
		choice := response.Choices[0]
		calls := choice.Message.ToolCalls
		if len(calls) == 0 {
			calls = parseTextToolCalls(choice.Message.Content, step)
		}
		if len(calls) == 0 {
			answer := cleanAnswer(choice.Message.Content)
			if answer == "" {
				return "", errors.New("LLM returned an empty answer")
			}
			c.saveHistory(request.ChatID, userText, answer)
			log.Printf("[llm] completed chat=%d elapsed_ms=%d answer_chars=%d", request.ChatID, time.Since(started).Milliseconds(), len([]rune(answer)))
			return answer, nil
		}
		messages = append(messages, chatMessage{
			Role: "assistant", Content: choice.Message.Content, ToolCalls: calls,
		})
		for _, call := range calls {
			arguments := decodeArguments(call.Function.Arguments)
			var result string
			switch call.Function.Name {
			case "current_time":
				result = currentTime(c.cfg.LLMTimezone)
			case "web_search":
				query := strings.TrimSpace(arguments["query"])
				if query == "" {
					result = resources.Get("llm.prompt.empty_search")
				} else if cached, exists := searchCache[strings.ToLower(query)]; exists {
					result = resources.Format("llm.prompt.repeated_search", map[string]any{"cached": cached})
				} else {
					result = c.searchWeb(ctx, query)
					searchCache[strings.ToLower(query)] = result
				}
			default:
				result = resources.Get("llm.prompt.unknown_tool")
			}
			messages = append(messages, chatMessage{
				Role: "tool", ToolCallID: call.ID, Name: call.Function.Name, Content: result,
			})
		}
	}

	finalMessages := append([]chatMessage(nil), messages...)
	finalMessages = append(finalMessages, chatMessage{
		Role:    "user",
		Content: resources.Format("llm.prompt.force_final", map[string]any{"original_prompt": text}),
	})
	response, err := c.complete(ctx, finalMessages, nil, false)
	if err != nil || len(response.Choices) == 0 {
		if err == nil {
			err = errors.New("LLM returned no choices")
		}
		return "", err
	}
	answer := cleanAnswer(response.Choices[0].Message.Content)
	if answer == "" {
		return "", errors.New("LLM returned an empty final answer")
	}
	c.saveHistory(request.ChatID, userText, answer)
	return answer, nil
}

func (c *Client) complete(ctx context.Context, messages []chatMessage, tools []map[string]any, allowTools bool) (completionResponse, error) {
	payload := map[string]any{
		"model": c.cfg.LLMModel, "messages": messages,
		"temperature": c.cfg.LLMTemperature, "max_tokens": c.cfg.LLMMaxTokens,
	}
	if allowTools && len(tools) > 0 {
		payload["tools"] = tools
		payload["tool_choice"] = "auto"
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return completionResponse{}, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.cfg.LLMBaseURL+"/chat/completions", bytes.NewReader(data))
	if err != nil {
		return completionResponse{}, err
	}
	request.Header.Set("Authorization", "Bearer "+c.cfg.LLMAPIKey)
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("HTTP-Referer", "https://github.com/hyphentae/cattemis-bot")
	request.Header.Set("X-Title", "cattemis-bot")
	response, err := c.http.Do(request)
	if err != nil {
		return completionResponse{}, err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 8*1024*1024))
	if err != nil {
		return completionResponse{}, err
	}
	var parsed completionResponse
	if err := json.Unmarshal(body, &parsed); err != nil {
		return completionResponse{}, fmt.Errorf("LLM returned invalid JSON (HTTP %d): %w", response.StatusCode, err)
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		message := strings.TrimSpace(string(body))
		if parsed.Error != nil && parsed.Error.Message != "" {
			message = parsed.Error.Message
		}
		return completionResponse{}, fmt.Errorf("LLM HTTP %d: %s", response.StatusCode, truncate(message, 1000))
	}
	return parsed, nil
}

func (c *Client) saveHistory(chatID int64, user, assistant string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	history := append(c.history[chatID],
		chatMessage{Role: "user", Content: user},
		chatMessage{Role: "assistant", Content: assistant},
	)
	if maximum := c.cfg.LLMMaxHistory; maximum > 0 && len(history) > maximum {
		history = history[len(history)-maximum:]
	}
	c.history[chatID] = history
}

func currentTimeTool() map[string]any {
	return map[string]any{
		"type": "function",
		"function": map[string]any{
			"name":        "current_time",
			"description": "Get the current date and time configured for the user.",
			"parameters":  map[string]any{"type": "object", "properties": map[string]any{}, "additionalProperties": false},
		},
	}
}

func webSearchTool() map[string]any {
	return map[string]any{
		"type": "function",
		"function": map[string]any{
			"name": "web_search", "description": resources.Get("llm.tool.web_search.description"),
			"parameters": map[string]any{
				"type":       "object",
				"properties": map[string]any{"query": map[string]string{"type": "string"}},
				"required":   []string{"query"}, "additionalProperties": false,
			},
		},
	}
}

func currentTime(timezone string) string {
	location, err := time.LoadLocation(timezone)
	if err != nil {
		location = parseOffset(timezone)
	}
	now := time.Now().In(location)
	_, offsetSeconds := now.Zone()
	sign := "+"
	if offsetSeconds < 0 {
		sign = "-"
		offsetSeconds = -offsetSeconds
	}
	offset := fmt.Sprintf("%s%02d:%02d", sign, offsetSeconds/3600, offsetSeconds%3600/60)
	return resources.Format("llm.time.current", map[string]any{
		"date": now.Format("2006-01-02"), "time": now.Format("15:04:05"),
		"offset": offset, "utc_seconds": now.Unix(),
	})
}

func parseOffset(value string) *time.Location {
	match := regexp.MustCompile(`^([+-])(\d{1,2}):?(\d{2})$`).FindStringSubmatch(strings.TrimSpace(value))
	if len(match) != 4 {
		return time.UTC
	}
	hours, _ := strconv.Atoi(match[2])
	minutes, _ := strconv.Atoi(match[3])
	if hours > 23 || minutes > 59 {
		return time.UTC
	}
	seconds := hours*3600 + minutes*60
	if match[1] == "-" {
		seconds = -seconds
	}
	return time.FixedZone(value, seconds)
}

func decodeArguments(raw any) map[string]string {
	result := map[string]string{}
	switch value := raw.(type) {
	case string:
		var decoded map[string]any
		if json.Unmarshal([]byte(value), &decoded) == nil {
			for key, item := range decoded {
				result[key] = fmt.Sprint(item)
			}
		}
	case map[string]any:
		for key, item := range value {
			result[key] = fmt.Sprint(item)
		}
	}
	return result
}

var (
	completeToolPattern = regexp.MustCompile(`(?is)<tool_call>.*?</tool_call>`)
	toolPattern         = regexp.MustCompile(`(?is)<tool_call>\s*([a-zA-Z0-9_]+)\s*(.*?)</tool_call>`)
	argumentPattern     = regexp.MustCompile(`(?is)<arg_key>\s*([^<]+?)\s*</arg_key>\s*<arg_value>\s*(.*?)\s*</arg_value>`)
	thinkingPattern     = regexp.MustCompile(`(?is)<(?:analysis|think)>.*?</(?:analysis|think)>`)
	controlPattern      = regexp.MustCompile(`(?i)<\|(?:channel|im_start|im_end|end|eot|assistant|user|system)\|>|</?(?:analysis|think)>`)
)

func parseTextToolCalls(content string, step int) []toolCall {
	matches := toolPattern.FindAllStringSubmatch(content, -1)
	result := make([]toolCall, 0, len(matches))
	for index, match := range matches {
		if len(match) != 3 {
			continue
		}
		arguments := map[string]string{}
		for _, argument := range argumentPattern.FindAllStringSubmatch(match[2], -1) {
			if len(argument) == 3 {
				arguments[strings.TrimSpace(argument[1])] = strings.TrimSpace(argument[2])
			}
		}
		data, _ := json.Marshal(arguments)
		result = append(result, toolCall{
			ID: fmt.Sprintf("text_tool_call_%d_%d", step, index), Type: "function",
			Function: toolFunction{Name: strings.TrimSpace(match[1]), Arguments: string(data)},
		})
	}
	return result
}

func cleanAnswer(value string) string {
	lower := strings.ToLower(value)
	for _, marker := range []string{"<|channel|>final", "<channel|>final"} {
		if index := strings.LastIndex(lower, marker); index >= 0 {
			value = value[index+len(marker):]
			lower = strings.ToLower(value)
		}
	}
	value = thinkingPattern.ReplaceAllString(value, "")
	value = completeToolPattern.ReplaceAllString(value, "")
	if index := strings.Index(strings.ToLower(value), "<tool_call>"); index >= 0 {
		value = value[:index]
	}
	value = controlPattern.ReplaceAllString(value, "")
	value = strings.TrimSpace(value)
	runes := []rune(value)
	if len(runes) > 4000 {
		value = string(runes[:4000])
	}
	return value
}

func truncate(value string, maximum int) string {
	value = strings.TrimSpace(value)
	if len(value) <= maximum {
		return value
	}
	return value[:maximum] + "…"
}
