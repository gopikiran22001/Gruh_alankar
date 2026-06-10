# Colored Logging Usage Guide

## Overview
The colored logging system provides visual distinction between different agents and task types in terminal output.

## Agent Colors
- **Supervisor**: Cyan
- **Critic**: Magenta
- **Buddy**: Green
- **Design**: Blue
- **Furniture**: Orange
- **Budget**: Yellow
- **Booking**: Purple
- **Vision**: Pink
- **Voice**: White
- **Web**: Red
- **Memory**: Cyan

## Task Type Colors
- **Chat**: Green
- **Design**: Blue
- **Analysis**: Cyan
- **Budget**: Yellow
- **Booking**: Purple
- **Scraping**: Red
- **Vision**: Pink
- **Voice**: White
- **Orchestration**: Magenta

## Usage Examples

### Basic Usage
```python
from app.observability.colored_logger import get_colored_logger

logger = get_colored_logger("buddy")

# Simple info log
logger.info("Processing user message")

# Info with task type
logger.info("Analyzing design preferences", task_type="chat")

# Warning
logger.warning("Rate limit approaching")

# Error
logger.error("Failed to connect to LLM")

# Debug with task type
logger.debug("Request payload received", task_type="analysis")
```

### In Agent Classes
```python
from app.observability.colored_logger import get_colored_logger

class BuddyAgent:
    def __init__(self):
        self.logger = get_colored_logger("buddy")
    
    def process(self, message: str):
        self.logger.info("Starting conversation", task_type="chat")
        # Your logic here
        self.logger.info("Conversation completed", task_type="chat")
```

### In Supervisor
```python
from app.observability.colored_logger import get_colored_logger

logger = get_colored_logger("supervisor")

def route_task(task):
    logger.info(f"Routing to {task.agent}", task_type="orchestration")
```

### In Tasks
```python
from app.observability.colored_logger import get_colored_logger

logger = get_colored_logger("web")

@celery.task
def scrape_furniture():
    logger.info("Starting scrape job", task_type="scraping")
    # Your scraping logic
    logger.info("Scrape completed", task_type="scraping")
```

## Terminal Output Format
```
[BUDDY] [chat] Processing user message
[DESIGN] [design] Generating 3D model
[BUDGET] [budget] Calculating costs
[SUPERVISOR] [orchestration] Routing to design agent
[WEB] [ERROR] Connection timeout
```

## Benefits
- Quick visual identification of agents in logs
- Easy tracking of task types
- Better debugging experience
- No performance overhead
- Works alongside existing structlog configuration
