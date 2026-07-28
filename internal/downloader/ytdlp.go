package downloader

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

func (d *Downloader) downloadYTDLP(ctx context.Context, value *url.URL) (Result, error) {
	return d.downloadYTDLPWithOptions(ctx, value, false)
}

func (d *Downloader) downloadYTDLPWithOptions(ctx context.Context, value *url.URL, allowPlaylist bool) (Result, error) {
	directory, err := os.MkdirTemp("", "cattemis-ytdlp-*")
	if err != nil {
		return Result{}, err
	}
	defer os.RemoveAll(directory)

	output := filepath.Join(directory, "%(id)s.%(ext)s")
	arguments := []string{
		"--no-progress", "--newline",
		"--max-filesize", strconv.FormatInt(d.cfg.MaxFileSize, 10),
		"--merge-output-format", "mp4",
		"--write-info-json",
		"--output", output,
		"--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
	}
	if allowPlaylist {
		arguments = append(arguments, "--yes-playlist", "--playlist-end", strconv.Itoa(d.cfg.MaxMediaItems))
	} else {
		arguments = append(arguments, "--no-playlist")
	}
	if d.cfg.YTDownloadCookies != "" {
		arguments = append(arguments, "--cookies", d.cfg.YTDownloadCookies)
	}
	if d.cfg.YTDownloadBrowser != "" {
		arguments = append(arguments, "--cookies-from-browser", d.cfg.YTDownloadBrowser)
	}
	arguments = append(arguments, value.String())
	command := exec.CommandContext(ctx, d.cfg.YTDownloadPath, arguments...)
	command.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	outputData, err := command.CombinedOutput()
	if err != nil {
		return Result{}, fmt.Errorf("yt-dlp failed: %w: %s", err, tail(string(outputData), 3000))
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return Result{}, err
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name() < entries[j].Name() })
	items := make([]Media, 0)
	caption := ""
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		fullPath := filepath.Join(directory, entry.Name())
		if strings.HasSuffix(entry.Name(), ".info.json") {
			if caption == "" {
				caption = ytdlpCaption(fullPath)
			}
			continue
		}
		kind := kindFromExtension(entry.Name())
		if kind == "" {
			continue
		}
		info, err := entry.Info()
		if err != nil || info.Size() > d.cfg.MaxFileSize {
			continue
		}
		data, err := os.ReadFile(fullPath)
		if err != nil {
			return Result{}, err
		}
		items = append(items, Media{Kind: kind, Name: entry.Name(), MIME: mimeForName(entry.Name()), Data: data})
	}
	if len(items) == 0 {
		return Result{}, errors.New("yt-dlp produced no supported media")
	}
	source := "ytdlp"
	if IsYouTube(value) {
		source = "youtube"
	} else if IsReddit(value) {
		source = "reddit"
	} else if IsInstagram(value) {
		source = "instagram"
	}
	return Result{Items: items, Caption: caption, Source: source}, nil
}

func ytdlpCaption(filename string) string {
	data, err := os.ReadFile(filename)
	if err != nil {
		return ""
	}
	var info map[string]any
	if json.Unmarshal(data, &info) != nil {
		return ""
	}
	title, _ := info["title"].(string)
	description, _ := info["description"].(string)
	uploader := firstMapString(info, "uploader", "channel", "creator")
	parts := make([]string, 0, 3)
	if strings.TrimSpace(title) != "" {
		parts = append(parts, strings.TrimSpace(title))
	}
	if strings.TrimSpace(description) != "" && strings.TrimSpace(description) != strings.TrimSpace(title) {
		parts = append(parts, strings.TrimSpace(description))
	}
	if strings.TrimSpace(uploader) != "" {
		parts = append(parts, strings.TrimSpace(uploader))
	}
	return strings.Join(parts, "\n\n")
}

func mimeForName(name string) string {
	switch strings.ToLower(filepath.Ext(name)) {
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".png":
		return "image/png"
	case ".webp":
		return "image/webp"
	case ".gif":
		return "image/gif"
	case ".mp4":
		return "video/mp4"
	case ".webm":
		return "video/webm"
	case ".mov":
		return "video/quicktime"
	default:
		return "application/octet-stream"
	}
}

func tail(value string, maximum int) string {
	value = strings.TrimSpace(value)
	if len(value) <= maximum {
		return value
	}
	return value[len(value)-maximum:]
}
