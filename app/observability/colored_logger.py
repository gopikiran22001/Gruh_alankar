"""Colored terminal logging for agents and tasks."""

import structlog

# ANSI color codes
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    ORANGE = "\033[38;5;214m"
    PURPLE = "\033[38;5;141m"
    PINK = "\033[38;5;213m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

# Agent color mapping
AGENT_COLORS = {
    "supervisor": Colors.CYAN,
    "critic": Colors.MAGENTA,
    "buddy": Colors.GREEN,
    "design": Colors.BLUE,
    "furniture": Colors.ORANGE,
    "budget": Colors.YELLOW,
    "booking": Colors.PURPLE,
    "vision": Colors.PINK,
    "voice": Colors.WHITE,
    "web": Colors.RED,
    "memory": Colors.CYAN,
}

# Task type color mapping
TASK_COLORS = {
    "chat": Colors.GREEN,
    "design": Colors.BLUE,
    "analysis": Colors.CYAN,
    "budget": Colors.YELLOW,
    "booking": Colors.PURPLE,
    "scraping": Colors.RED,
    "vision": Colors.PINK,
    "voice": Colors.WHITE,
    "orchestration": Colors.MAGENTA,
}


def get_colored_logger(agent_name: str):
    """Get logger with colored output for specific agent."""
    logger = structlog.get_logger(agent_name)
    color = AGENT_COLORS.get(agent_name.lower(), Colors.WHITE)
    
    class ColoredLogger:
        def info(self, msg: str, task_type: str = None, **kwargs):
            prefix = f"{color}[{agent_name.upper()}]{Colors.RESET}"
            task = f" {TASK_COLORS.get(task_type, Colors.WHITE)}[{task_type}]{Colors.RESET}" if task_type else ""
            print(f"{prefix}{task} {msg}")
            logger.info(msg, agent=agent_name, task_type=task_type, **kwargs)
            
        def error(self, msg: str, **kwargs):
            prefix = f"{color}[{agent_name.upper()}]{Colors.RESET}"
            print(f"{prefix} {Colors.RED}[ERROR]{Colors.RESET} {msg}")
            logger.error(msg, agent=agent_name, **kwargs)
            
        def warning(self, msg: str, **kwargs):
            prefix = f"{color}[{agent_name.upper()}]{Colors.RESET}"
            print(f"{prefix} {Colors.YELLOW}[WARN]{Colors.RESET} {msg}")
            logger.warning(msg, agent=agent_name, **kwargs)
            
        def debug(self, msg: str, task_type: str = None, **kwargs):
            prefix = f"{color}[{agent_name.upper()}]{Colors.RESET}"
            task = f" {TASK_COLORS.get(task_type, Colors.WHITE)}[{task_type}]{Colors.RESET}" if task_type else ""
            print(f"{prefix}{task} {Colors.WHITE}[DEBUG]{Colors.RESET} {msg}")
            logger.debug(msg, agent=agent_name, task_type=task_type, **kwargs)
    
    return ColoredLogger()
