package bot

import (
	"context"
	"strings"

	"github.com/hyphentae/cattemis-bot/internal/telegram"
	"github.com/hyphentae/cattemis-bot/resources"
)

var games = []struct {
	ShortName string
	Title     string
}{
	{"tictactoe", "крестики-нолики"},
	{"minesweeper", "сапёр"},
	{"sudoku", "судоку"},
	{"canvas", "общий холст"},
	{"chess", "шахматы"},
	{"parabolic_chess", "parabolic chess"},
	{"checkers", "шашки"},
	{"flappy", "Flappy Kat"},
}

func (b *Bot) sendWebApp(ctx context.Context, message *telegram.Message) error {
	webAppURL := b.cfg.CurrentWebAppURL()
	if webAppURL == "" {
		_, err := b.telegram.SendMessage(ctx, message.Chat.ID, resources.Get("bot.webapp.tunnel_starting"), message.MessageID, nil)
		return err
	}
	button := map[string]any{"text": resources.Get("telegram.games.open")}
	if message.IsPrivate() {
		button["web_app"] = map[string]string{"url": webAppURL}
	} else {
		button["url"] = webAppURL
	}
	_, err := b.telegram.SendMessage(ctx, message.Chat.ID, resources.Get("telegram.games.choose"), message.MessageID,
		map[string]any{"inline_keyboard": [][]map[string]any{{button}}})
	return err
}

func (b *Bot) sendGames(ctx context.Context, message *telegram.Message) error {
	rows := make([][]map[string]any, 0, len(games))
	for _, game := range games {
		rows = append(rows, []map[string]any{{
			"text": game.Title, "switch_inline_query_current_chat": game.ShortName,
		}})
	}
	_, err := b.telegram.SendMessage(ctx, message.Chat.ID, resources.Get("telegram.games.choose"), message.MessageID,
		map[string]any{"inline_keyboard": rows})
	return err
}

func (b *Bot) handleInlineQuery(ctx context.Context, query *telegram.InlineQuery) error {
	search := strings.ToLower(strings.TrimSpace(query.Query))
	results := make([]map[string]any, 0, len(games))
	for _, game := range games {
		if search != "" && !strings.Contains(strings.ToLower(game.ShortName), search) && !strings.Contains(strings.ToLower(game.Title), search) {
			continue
		}
		results = append(results, map[string]any{
			"type": "game", "id": "cattemis-" + game.ShortName, "game_short_name": game.ShortName,
		})
	}
	return b.telegram.AnswerInlineQuery(ctx, query.ID, results)
}

func (b *Bot) launchGame(ctx context.Context, callback *telegram.CallbackQuery) error {
	webAppURL := b.cfg.CurrentWebAppURL()
	if webAppURL == "" {
		return b.telegram.AnswerCallback(ctx, callback.ID, resources.Get("bot.webapp.tunnel_starting"), "", true)
	}
	valid := false
	for _, game := range games {
		if callback.GameShortName == game.ShortName {
			valid = true
			break
		}
	}
	if !valid {
		return b.telegram.AnswerCallback(ctx, callback.ID, resources.Get("bot.game.invalid"), "", true)
	}
	token := signGameUser(callback.From, b.cfg.BotToken, callback.ChatInstance)
	return b.telegram.AnswerCallback(ctx, callback.ID, "", buildGameURL(webAppURL, callback.GameShortName, token), false)
}
