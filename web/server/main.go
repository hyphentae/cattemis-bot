package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"time"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := newServer(os.Getenv("BOT_TOKEN"))
	parabolicTarget := os.Getenv("PARABOLIC_URL")
	if parabolicTarget == "" {
		parabolicTarget = "http://parabolic:3000"
	}
	parabolicURL, err := url.Parse(parabolicTarget)
	if err != nil {
		log.Fatalf("[web] invalid PARABOLIC_URL: %v", err)
	}
	parabolicProxy := httputil.NewSingleHostReverseProxy(parabolicURL)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", server.health)
	mux.HandleFunc("/api/canvas/state", server.canvasState)
	mux.HandleFunc("/api/canvas/place", server.placeCanvasPixel)
	mux.HandleFunc("/api/leaderboard", server.leaderboard)
	mux.HandleFunc("/api/tictactoe/create", server.createTTTRoom)
	mux.HandleFunc("/api/tictactoe/public", server.publicTTTRoom)
	mux.HandleFunc("/api/tictactoe/join", server.joinTTTRoom)
	mux.HandleFunc("/api/tictactoe/state", server.tttState)
	mux.HandleFunc("/api/tictactoe/move", server.tttMove)
	mux.HandleFunc("/api/checkers/create", server.createRoom)
	mux.HandleFunc("/api/checkers/create-bot", server.createBotGame)
	mux.HandleFunc("/api/checkers/public", server.matchPublicRoom)
	mux.HandleFunc("/api/checkers/join", server.joinRoom)
	mux.HandleFunc("/api/checkers/state", server.roomState)
	mux.HandleFunc("/api/checkers/move", server.move)
	mux.HandleFunc("/api/chess/create", server.createChessRoom)
	mux.HandleFunc("/api/chess/public", server.matchPublicChessRoom)
	mux.HandleFunc("/api/chess/join", server.joinChessRoom)
	mux.HandleFunc("/api/chess/state", server.chessRoomState)
	mux.HandleFunc("/api/chess/move", server.chessMove)
	mux.Handle("/parabolic/", http.StripPrefix("/parabolic", parabolicProxy))
	mux.HandleFunc("/parabolic-ws", func(w http.ResponseWriter, r *http.Request) {
		r.URL.Path = "/"
		parabolicProxy.ServeHTTP(w, r)
	})
	staticFiles := http.FileServer(http.Dir("/static"))
	mux.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-cache")
		staticFiles.ServeHTTP(w, r)
	}))

	httpServer := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	log.Printf("[web] serving Mini App and checkers API on :%s", port)
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
