# Gruha Alankara - Colored Logging & Startup Banner Examples

## 🎨 Colored Logging for Agents

### Setup in Agent Files

Replace standard logger with colored logger:

```python
# OLD - Standard logger
from config.logging_config import get_logger
logger = get_logger(__name__)

# NEW - Colored logger
from app.observability.colored_logger import get_colored_logger
logger = get_colored_logger("buddy")  # Use agent name
```

### Usage Examples

```python
# In buddy_agent.py
from app.observability.colored_logger import get_colored_logger

logger = get_colored_logger("buddy")

class BuddyAgent(BaseAgent):
    async def execute(self, task):
        logger.info("Processing user message", task_type="chat")
        # ... your logic
        logger.info("Response generated", task_type="chat")
```

```python
# In supervisor_agent.py
from app.observability.colored_logger import get_colored_logger

logger = get_colored_logger("supervisor")

class SupervisorAgent(BaseAgent):
    async def route_task(self, task):
        logger.info(f"Routing to {task.agent}", task_type="orchestration")
```

```python
# In design_agent.py
from app.observability.colored_logger import get_colored_logger

logger = get_colored_logger("design")

class DesignAgent(BaseAgent):
    async def generate_design(self, params):
        logger.info("Generating 3D model", task_type="design")
        logger.debug("Using style preferences", task_type="design")
```

## 🚀 Startup Banner

The startup banner automatically displays when the Flask server is ready.

### Banner Display

After all models load and agents initialize, you'll see:

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║      ██████╗ ██████╗ ██╗   ██╗██╗  ██╗ █████╗                           ║
║     ██╔════╝ ██╔══██╗██║   ██║██║  ██║██╔══██╗                          ║
║     ██║  ███╗██████╔╝██║   ██║███████║███████║                          ║
║     ██║   ██║██╔══██╗██║   ██║██╔══██║██╔══██║                          ║
║     ╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║  ██║                          ║
║      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝                          ║
║                                                                          ║
║      █████╗ ██╗      █████╗ ███╗   ██╗██╗  ██╗ █████╗ ██████╗          ║
║     ██╔══██╗██║     ██╔══██╗████╗  ██║██║ ██╔╝██╔══██╗██╔══██╗         ║
║     ███████║██║     ███████║██╔██╗ ██║█████╔╝ ███████║██████╔╝         ║
║     ██╔══██║██║     ██╔══██║██║╚██╗██║██╔═██╗ ██╔══██║██╔══██╗         ║
║     ██║  ██║███████╗██║  ██║██║ ╚████║██║  ██╗██║  ██║██║  ██║         ║
║     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝         ║
║                                                                          ║
║      AI-Powered Interior Design Platform                                ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

🚀 SERVER IS ONLINE!

📡 Server URL:      http://0.0.0.0:5000
🏥 Health Check:    http://0.0.0.0:5000/api/health
🔧 Debug Mode:      ON

✓ All models loaded
✓ Agents initialized  
✓ Database connected
✓ Ready to serve requests

──────────────────────────────────────────────────────────────────────────
```

## 📊 Color Reference

### Agent Colors
- **Supervisor** → Cyan
- **Critic** → Magenta
- **Buddy** → Green
- **Design** → Blue
- **Furniture** → Orange
- **Budget** → Yellow
- **Booking** → Purple
- **Vision** → Pink
- **Voice** → White
- **Web** → Red
- **Memory** → Cyan

### Task Colors
- **chat** → Green
- **design** → Blue
- **analysis** → Cyan
- **budget** → Yellow
- **booking** → Purple
- **scraping** → Red
- **vision** → Pink
- **voice** → White
- **orchestration** → Magenta

## 🔧 Configuration

### Enable Colored Logging

Edit `.env` file:
```env
LOG_FORMAT=console  # Use 'json' for production
LOG_LEVEL=INFO
```

## 📝 Terminal Output Examples

With colored logging enabled:

```
[BUDDY] [chat] Processing user message
[SUPERVISOR] [orchestration] Delegating to design agent
[DESIGN] [design] Generating room layout
[BUDGET] [budget] Calculating cost breakdown
[FURNITURE] Recommending products
[WEB] [scraping] Fetching product data
[BUDDY] [chat] Response ready
```

Without colored logging (production JSON):

```json
{"event": "Processing user message", "agent": "buddy", "task_type": "chat", "level": "info"}
{"event": "Delegating to design agent", "agent": "supervisor", "task_type": "orchestration", "level": "info"}
```

## 🎯 Best Practices

1. **Development**: Use `LOG_FORMAT=console` with colored logger
2. **Production**: Use `LOG_FORMAT=json` for structured logging
3. **Always specify task_type**: Helps with filtering and debugging
4. **Use appropriate log levels**: info, warning, error, debug
5. **Include context**: Add extra kwargs for detailed logging

```python
logger.info("User query processed", 
            task_type="chat",
            user_id=user_id,
            query_length=len(message),
            response_time_ms=duration)
```
