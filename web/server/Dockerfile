# --- frontend ---
FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY web/client/package.json web/client/package-lock.json ./
RUN npm ci
COPY web/client/ ./
RUN mkdir -p public
COPY resources/strings.json /tmp/strings.json
RUN node -e "const fs=require('fs');const all=JSON.parse(fs.readFileSync('/tmp/strings.json'));const web=Object.fromEntries(Object.entries(all).filter(([key])=>key.startsWith('web.')));fs.writeFileSync('public/strings.json',JSON.stringify(web))"
RUN npm run build

# --- server build ---
FROM golang:1.24-alpine AS builder
WORKDIR /src
COPY go.mod ./
COPY web/server ./web/server
RUN go test ./web/server && go build -o /webserver ./web/server

# --- run (scratch = ~0MB overhead) ---
FROM scratch
COPY --from=builder /webserver /webserver
COPY --from=frontend /frontend/dist /static
EXPOSE 8080
ENTRYPOINT ["/webserver"]
