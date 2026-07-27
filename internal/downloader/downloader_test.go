package downloader

import "testing"

func TestSupportedPlatformsAndDirectMedia(t *testing.T) {
	valid := []string{
		"https://www.tiktok.com/@cat/video/123",
		"https://www.instagram.com/reel/ABC123/",
		"https://x.com/user/status/123",
		"https://www.reddit.com/r/cats/comments/abc/title/",
		"https://youtu.be/abcdefghijk",
		"https://cdn.example.com/cat.png",
	}
	for _, value := range valid {
		if !Supported(value) {
			t.Errorf("expected supported URL: %s", value)
		}
	}
	if Supported("https://example.com/article") {
		t.Fatal("ordinary article URL must not be treated as downloadable media")
	}
}

func TestCaptionTruncatesByRunes(t *testing.T) {
	value := truncateCaption(string(make([]rune, 0)))
	if value != "" {
		t.Fatalf("unexpected empty caption result: %q", value)
	}
	long := ""
	for range 1100 {
		long += "я"
	}
	result := truncateCaption(long)
	if len([]rune(result)) != 1024 {
		t.Fatalf("expected 1024 runes, got %d", len([]rune(result)))
	}
}
