package llm

import "testing"

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
	if cleanAnswer("Ответ"+raw) != "Ответ" {
		t.Fatal("text tool call leaked into final answer")
	}
}

func TestCleanAnswerRemovesThinkingBlocks(t *testing.T) {
	if result := cleanAnswer("<think>internal</think>Готово"); result != "Готово" {
		t.Fatalf("unexpected clean answer: %q", result)
	}
	if result := cleanAnswer("<|channel|>analysis hidden<|channel|>final Ответ"); result != "Ответ" {
		t.Fatalf("channel analysis leaked: %q", result)
	}
}
