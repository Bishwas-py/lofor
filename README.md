# Lofor - A reverse proxy for development

Lofor is a lightweight development server which acts as reverse proxy to solve your cors header problems.

CORS is a common problem faced when developing frontend and backend separated projects.

During development, you may like to use a backend in `localhost:7777/api/` and
frontend in `localhost:7777`.

This becomes more complex when you use two different frameworks for backend and frontend.

## How lofor solves the problem?

In lofor, you can map multiple hosts to single one.

### Installation

```bash
pip install lofor
```

### Forward command

```bash
lofor forward / http://localhost:5173 # Mapping to svelte dev server
lofor forward /api/ https://localhost:8000   # Mapping to django's dev server

# More examples
lofor forward api.localhost /api/ https://localhost:8000
lofor forward localhost http://localhost:3000

# You can also map to any real server
# lofor forward / https://example.com
```

### Start lofor server

The server will be listening at [http://localhost:7777](http://localhost:7777)

```bash
lofor start
```

### To list lofor forwards

```bash
lofor list
```

### Remove lofor forwards

```bash
lofor remove /api/
```



