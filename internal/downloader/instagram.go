package downloader

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"html"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"sort"
	"strings"
)

var (
	instagramShortcode = regexp.MustCompile(`(?i)/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)`)
	metaTagPattern     = regexp.MustCompile(`(?is)<meta\s+[^>]*>`)
	metaProperty       = regexp.MustCompile(`(?i)(?:property|name)\s*=\s*["']([^"']+)["']`)
	metaContent        = regexp.MustCompile(`(?i)content\s*=\s*["']([^"']*)["']`)
	displayURLPattern  = regexp.MustCompile(`(?s)"(?:display_url|video_url)"\s*:\s*"((?:\\.|[^"])*)"`)
)

func (d *Downloader) downloadInstagram(ctx context.Context, value *url.URL) (Result, error) {
	match := instagramShortcode.FindStringSubmatch(value.Path)
	if len(match) != 2 {
		return Result{}, errors.New("Instagram URL does not contain a post or Reel shortcode")
	}
	canonical := "https://www.instagram.com/p/" + match[1] + "/"
	embed := canonical + "embed/captioned/"
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, embed, nil)
	if err != nil {
		return Result{}, err
	}
	request.Header.Set("User-Agent", browserUserAgent)
	request.Header.Set("Accept-Language", "en-US,en;q=0.9")
	response, err := d.client.Do(request)
	if err == nil {
		defer response.Body.Close()
		if response.StatusCode >= 200 && response.StatusCode < 300 {
			page, readErr := io.ReadAll(io.LimitReader(response.Body, 5*1024*1024))
			if readErr == nil {
				urls, caption := instagramPageMedia(string(page))
				if len(urls) > 0 {
					items, downloadErr := d.downloadInstagramItems(ctx, urls)
					if downloadErr == nil && len(items) > 0 {
						return Result{Items: items, Caption: caption, Source: "instagram"}, nil
					}
				}
			}
		}
	}
	return d.downloadInstagramApify(ctx, canonical)
}

func instagramPageMedia(page string) ([]string, string) {
	caption := firstNonEmpty(metaValue(page, "og:description"), metaValue(page, "description"))
	caption = cleanInstagramDescription(html.UnescapeString(caption))
	urls := make([]string, 0)
	for _, property := range []string{"og:video:secure_url", "og:video", "og:image"} {
		if value := metaValue(page, property); value != "" {
			urls = append(urls, html.UnescapeString(value))
		}
	}
	for _, match := range displayURLPattern.FindAllStringSubmatch(page, -1) {
		if len(match) != 2 {
			continue
		}
		var decoded string
		if json.Unmarshal([]byte(`"`+match[1]+`"`), &decoded) == nil {
			urls = append(urls, decoded)
		}
	}
	return uniqueHTTPS(urls), caption
}

func metaValue(page, requested string) string {
	for _, tag := range metaTagPattern.FindAllString(page, -1) {
		property := metaProperty.FindStringSubmatch(tag)
		content := metaContent.FindStringSubmatch(tag)
		if len(property) == 2 && len(content) == 2 && strings.EqualFold(property[1], requested) {
			return content[1]
		}
	}
	return ""
}

func cleanInstagramDescription(value string) string {
	value = strings.TrimSpace(value)
	if quote := strings.Index(value, `: "`); quote >= 0 && strings.HasSuffix(value, `"`) {
		return strings.TrimSuffix(value[quote+3:], `"`)
	}
	return cleanText(value)
}

func (d *Downloader) downloadInstagramApify(ctx context.Context, postURL string) (Result, error) {
	if d.cfg.APIFYToken == "" {
		return Result{}, errors.New("Instagram hid this post; APIFY_TOKEN is required for the fallback")
	}
	actor := strings.ReplaceAll(d.cfg.APIFYInstagramActor, "/", "~")
	endpoint := fmt.Sprintf(
		"https://api.apify.com/v2/acts/%s/run-sync-get-dataset-items",
		url.PathEscape(actor),
	)
	input := map[string]any{
		"directUrls": []string{postURL}, "resultsType": "details", "resultsLimit": 1,
		"addParentData": false,
	}
	data, _ := json.Marshal(input)
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(data))
	if err != nil {
		return Result{}, err
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+d.cfg.APIFYToken)
	response, err := d.client.Do(request)
	if err != nil {
		return Result{}, err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		body, _ := io.ReadAll(io.LimitReader(response.Body, 2048))
		return Result{}, fmt.Errorf("Apify HTTP %d: %s", response.StatusCode, strings.TrimSpace(string(body)))
	}
	var items []map[string]any
	if err := json.NewDecoder(response.Body).Decode(&items); err != nil {
		return Result{}, err
	}
	if len(items) == 0 {
		return Result{}, errors.New("Apify returned no Instagram results")
	}
	mediaURLs := collectApifyMedia(items[0])
	if len(mediaURLs) == 0 {
		return Result{}, errors.New("Apify returned no Instagram media URLs")
	}
	downloaded, err := d.downloadInstagramItems(ctx, mediaURLs)
	if err != nil {
		return Result{}, err
	}
	caption := firstMapString(items[0], "caption", "text", "description", "alt")
	return Result{Items: downloaded, Caption: cleanText(caption), Source: "instagram"}, nil
}

func collectApifyMedia(item map[string]any) []string {
	type candidate struct {
		priority int
		value    string
	}
	candidates := make([]candidate, 0)
	var walk func(any, string)
	walk = func(value any, key string) {
		switch current := value.(type) {
		case map[string]any:
			for childKey, child := range current {
				walk(child, strings.ToLower(childKey))
			}
		case []any:
			for _, child := range current {
				walk(child, key)
			}
		case string:
			if !strings.HasPrefix(current, "https://") {
				return
			}
			lower := strings.ToLower(key)
			priority := 0
			switch {
			case strings.Contains(lower, "video"):
				priority = 4
			case strings.Contains(lower, "image") || strings.Contains(lower, "photo") || strings.Contains(lower, "display"):
				priority = 3
			case strings.Contains(lower, "url"):
				priority = 1
			}
			if priority > 0 {
				candidates = append(candidates, candidate{priority, current})
			}
		}
	}
	walk(item, "")
	sort.SliceStable(candidates, func(i, j int) bool { return candidates[i].priority > candidates[j].priority })
	raw := make([]string, 0, len(candidates))
	for _, candidate := range candidates {
		raw = append(raw, candidate.value)
	}
	return uniqueHTTPS(raw)
}

func (d *Downloader) downloadInstagramItems(ctx context.Context, rawURLs []string) ([]Media, error) {
	items := make([]Media, 0, len(rawURLs))
	for _, raw := range rawURLs {
		parsed, err := url.Parse(raw)
		if err != nil || parsed.Scheme != "https" {
			continue
		}
		if !instagramMediaHost(parsed.Hostname()) {
			continue
		}
		item, err := d.fetchMedia(ctx, parsed.String(), "")
		if err != nil {
			if len(items) == 0 {
				return nil, err
			}
			continue
		}
		items = append(items, item)
		if len(items) >= d.cfg.MaxMediaItems {
			break
		}
	}
	if len(items) == 0 {
		return nil, errors.New("Instagram media could not be downloaded")
	}
	return items, nil
}

func instagramMediaHost(host string) bool {
	return hostMatches(host, "cdninstagram.com", "fbcdn.net", "instagram.com", "apifyusercontent.com", "amazonaws.com")
}

func uniqueHTTPS(values []string) []string {
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.ReplaceAll(strings.TrimSpace(value), `\u0026`, "&")
		parsed, err := url.Parse(value)
		if err != nil || parsed.Scheme != "https" || seen[value] {
			continue
		}
		seen[value] = true
		result = append(result, value)
	}
	return result
}

func firstMapString(value map[string]any, keys ...string) string {
	for _, key := range keys {
		if result, ok := value[key].(string); ok && strings.TrimSpace(result) != "" {
			return result
		}
	}
	return ""
}
