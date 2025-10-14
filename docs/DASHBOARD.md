# Auto-M4B Dashboard UI

## Overview

The Auto-M4B Dashboard provides real-time monitoring of audiobook conversions through a web-based interface. It displays live metrics, queue status, and conversion history without requiring command-line access.

## Architecture

### Technology Stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: HTMX + Alpine.js (no build process required)
- **Templating**: Jinja2
- **Styling**: Custom CSS with CSS variables
- **Server**: Uvicorn (ASGI)

### Design Decisions

1. **No Frontend Build Process**: Using HTMX and Alpine.js eliminates the need for npm/webpack/vite, simplifying deployment
2. **Server-Side Rendering**: Initial HTML rendered by Jinja2, then hydrated with Alpine.js
3. **Polling Architecture**: Client polls API endpoints every 10 seconds for updates
4. **Unified Application**: Single FastAPI app serves both API endpoints and dashboard UI

## File Structure

```
src/api/
├── app.py                      # Main FastAPI application
├── routes/
│   ├── health.py              # Health check endpoint
│   ├── status.py              # System status endpoint
│   ├── queue.py               # Queue management endpoint
│   └── metrics.py             # Metrics endpoint
├── templates/
│   └── dashboard.html         # Dashboard HTML template
└── static/
    └── css/
        └── dashboard.css      # Dashboard styles
```

## Polling Cadence

The dashboard uses **10-second polling intervals**:

```javascript
setInterval(() => this.fetchData(), 10000);
```

### Endpoints Polled

1. **`/api/v1/status`** - System status, metrics, uptime
2. **`/api/v1/queue`** - Queue summary and book list

### Why 10 Seconds?

- Balance between freshness and server load
- Conversion processes typically take 40-245 seconds
- Sufficient for monitoring without excessive requests
- Can be adjusted in `dashboard.html:235` if needed

## Authentication

**Phase 2.1.1: No Authentication**

The current implementation is **read-only** with no authentication. Suitable for:
- Local network deployments
- Trusted environments
- Development/testing

**Future Phases** will add:
- API key authentication (Phase 2.1.2)
- User accounts (Phase 2.2)
- Role-based access control (Phase 2.2)

## UI Components

### 1. Header
- System status badge (idle/processing/waiting)
- Uptime display
- Last updated timestamp

### 2. Metrics Grid
Three cards displaying conversion statistics:

#### Lifetime Statistics
- Total conversions
- Successful conversions
- Failed conversions
- Success rate percentage
- Average duration
- Total bytes processed

#### Current Session
- Session conversions (resets on restart)
- Session success rate
- Session uptime
- Session bytes processed

#### Timing Statistics
- Fastest conversion
- Slowest conversion
- Average conversion time

### 3. Queue Section
- Queue summary (total, pending, processing, failed, retrying)
- Book list with:
  - Book name
  - Status badge
  - File size
  - Error messages (if failed)
  - Retry countdown (if retrying)

### 4. Empty State
Displayed when queue is empty with helpful message about adding books to inbox.

## Extending the Dashboard

### Adding New Widgets

1. **Add API Endpoint** (in `src/api/routes/`)
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/api/v1/my-new-endpoint")
def my_endpoint():
    return {"data": "value"}
```

2. **Register Router** (in `src/api/app.py`)
```python
from src.api.routes import my_new_route
app.include_router(my_new_route.router, tags=["custom"])
```

3. **Add to Alpine.js State** (in `dashboard.html`)
```javascript
function dashboard() {
    return {
        myNewData: {},

        async fetchData() {
            // Existing fetches...

            const newRes = await fetch('/api/v1/my-new-endpoint');
            this.myNewData = await newRes.json();
        }
    }
}
```

4. **Add HTML Section** (in `dashboard.html`)
```html
<div class="card">
    <div class="card-header">
        <h2 class="card-title">My New Widget</h2>
    </div>
    <div x-text="myNewData.value"></div>
</div>
```

### Customizing Styles

All colors and spacing use CSS variables defined in `dashboard.css`:

```css
:root {
    --primary: #10b981;      /* Main accent color */
    --danger: #ef4444;       /* Error states */
    --warning: #f59e0b;      /* Warning states */
    --success: #10b981;      /* Success states */
    --dark: #1f2937;         /* Dark backgrounds */
}
```

Modify these variables to change the entire color scheme.

### Changing Polling Interval

Edit `dashboard.html:235`:

```javascript
// Change from 10 seconds to 5 seconds
setInterval(() => this.fetchData(), 5000);
```

**Warning**: Shorter intervals increase server load.

## Running the Dashboard

### Via Docker Compose

1. **Enable API in your compose file**:
```yaml
services:
  auto-m4b:
    environment:
      - API_ENABLED=Y
      - API_HOST=0.0.0.0
      - API_PORT=8000
    ports:
      - "8000:8000"
```

2. **Start container**:
```bash
docker-compose up -d
```

3. **Access dashboard**:
```
http://localhost:8000
```

### Standalone (Development)

```bash
cd /path/to/auto-m4b
pipenv install
pipenv run python -m src.api.app
```

Access at `http://localhost:8000`

## API Endpoints

The dashboard consumes these read-only endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI (HTML) |
| `/api/v1/health` | GET | Health check |
| `/api/v1/status` | GET | System status + metrics |
| `/api/v1/queue` | GET | Queue summary + books |
| `/api/v1/queue/{book_key}` | GET | Individual book details |
| `/api/v1/metrics/recent` | GET | Recent conversion history |
| `/docs` | GET | Interactive API documentation |

## Browser Compatibility

Tested and working on:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires JavaScript enabled (Alpine.js).

## Troubleshooting

### Dashboard Not Loading

1. **Check API is enabled**:
```bash
docker logs <container-name> | grep "API started"
```

2. **Verify port mapping**:
```bash
docker ps | grep 8000
```

3. **Check browser console** for JavaScript errors

### Metrics Not Updating

1. **Check polling in browser console**:
```javascript
// Should see fetch requests every 10 seconds
```

2. **Verify API endpoints**:
```bash
curl http://localhost:8000/api/v1/status
curl http://localhost:8000/api/v1/queue
```

### Empty Metrics

Metrics populate after first conversion completes. If lifetime metrics are zero, no conversions have finished yet.

## Performance

- **Memory**: ~50MB additional for uvicorn process
- **CPU**: Negligible (<1% when idle)
- **Network**: ~2KB per polling cycle (every 10 seconds)
- **Concurrent Users**: Tested up to 10 simultaneous connections

## Future Enhancements

See `ROADMAP.md` for planned features:
- Phase 2.1.2: Authentication & authorization
- Phase 2.2: User management & settings UI
- Phase 2.3: Control actions (pause/resume/cancel)
- Phase 2.4: Real-time progress bars via WebSocket
- Phase 3.1: Job scheduling UI
- Phase 3.2: Notification system

## CLI Equivalence

Dashboard metrics match CLI output:

```bash
# CLI
python src --status

# Dashboard
http://localhost:8000
```

Both display:
- Lifetime stats (total, successful, failed, success rate)
- Session stats (current run)
- Timing stats (fastest, slowest, average)
- Queue status (pending, processing, failed)

## Security Considerations

**Current Phase**: No authentication - suitable for local/trusted networks only.

**Recommendations**:
- Use behind reverse proxy (nginx) with basic auth
- Restrict to localhost or internal network
- Enable HTTPS for production
- Implement API keys (coming in Phase 2.1.2)

**Do NOT expose publicly** without authentication in Phase 2.1.1.
