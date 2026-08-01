package llm

import (
	"strings"
	"testing"

	"github.com/hyphentae/cattemis-bot/internal/config"
)

func TestTextToolCallParsingAndCleanup(t *testing.T) {
	raw := `<tool_call>web_search
<arg_key>query</arg_key><arg_value>golang release</arg_value>
</tool_call>`
	calls := parseTextToolCalls(raw, 1)
	if len(calls) != 1 || calls[0].Function.Name != "web_search" {
		t.Fatalf("unexpected tool calls: %#v", calls)
	}
	arguments := decodeArguments(calls[0].Function.Arguments)
	if arguments["query"] != "golang release" {
		t.Fatalf("unexpected arguments: %#v", arguments)
	}
	if formatAnswer("Ответ"+raw) != "Ответ" {
		t.Fatal("text tool call leaked into final answer")
	}
}

func TestCleanAnswerRemovesThinkingBlocks(t *testing.T) {
	if result := formatAnswer("<think>internal</think>Готово"); result != "Готово" {
		t.Fatalf("unexpected clean answer: %q", result)
	}
	if result := formatAnswer("<|channel|>analysis hidden<|channel|>final Ответ"); result != "Ответ" {
		t.Fatalf("channel analysis leaked: %q", result)
	}
}

func TestCleanAnswerRepairsTrailingKaomoji(t *testing.T) {
	for input, expected := range map[string]string{
		"мяу >///":  "мяу >///<",
		"мяу >///<": "мяу >///<",
		"мяу >w":    "мяу >w<",
		"мяу >w<":   "мяу >w<",
		"мяу >_":    "мяу >_<",
		"мяу >o":    "мяу >o<",
		"x > 5":     "x > 5",
	} {
		if result := formatAnswer(input); result != expected {
			t.Errorf("formatAnswer(%q) = %q, want %q", input, result, expected)
		}
	}
}

func TestCleanAnswerCollapsesRepeatedAsterisks(t *testing.T) {
	input := "**важно** и ****"
	if result := formatAnswer(input); result != "*важно* и *" {
		t.Fatalf("unexpected answer formatting: %q", result)
	}
}

func TestFormatAnswerDoesNotTruncateLongText(t *testing.T) {
	input := strings.Repeat("я", 5000)
	if result := formatAnswer(input); result != input {
		t.Fatalf("formatted answer was truncated to %d runes", len([]rune(result)))
	}
}

func TestOpenRouterUsesPerplexityWebSearchTool(t *testing.T) {
	client := New(config.Config{
		LLMBaseURL: "https://openrouter.ai/api/v1", LLMModel: "anthropic/claude-sonnet-4",
		LLMWebSearch: true, LLMWebSearchResults: 4,
	})
	tools := client.requestTools()
	if len(tools) != 2 || tools[1]["type"] != "openrouter:web_search" {
		t.Fatalf("unexpected tools: %#v", tools)
	}
	parameters, ok := tools[1]["parameters"].(map[string]any)
	if !ok || parameters["engine"] != "perplexity" || parameters["max_results"] != 4 {
		t.Fatalf("unexpected web search parameters: %#v", tools[1]["parameters"])
	}
}

func TestOpenRouterPerplexityModelUsesNativeSearch(t *testing.T) {
	client := New(config.Config{
		LLMBaseURL: "https://openrouter.ai/api/v1", LLMModel: "perplexity/sonar-pro",
	})
	if !client.webSearchAvailable() {
		t.Fatal("Perplexity model should expose native search")
	}
	if tools := client.requestTools(); len(tools) != 0 {
		t.Fatalf("native Perplexity search should not receive custom tools: %#v", tools)
	}
}
