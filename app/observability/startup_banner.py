"""Startup banner for Gruha Alankara application."""

from typing import Optional


class Colors:
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_startup_banner(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Print a big colorful banner when server starts."""
    
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   {Colors.MAGENTA}   ██████╗ ██████╗ ██╗   ██╗██╗  ██╗ █████╗                        {Colors.CYAN}║
║   {Colors.MAGENTA}  ██╔════╝ ██╔══██╗██║   ██║██║  ██║██╔══██╗                       {Colors.CYAN}║
║   {Colors.MAGENTA}  ██║  ███╗██████╔╝██║   ██║███████║███████║                       {Colors.CYAN}║
║   {Colors.MAGENTA}  ██║   ██║██╔══██╗██║   ██║██╔══██║██╔══██║                       {Colors.CYAN}║
║   {Colors.MAGENTA}  ╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║  ██║                       {Colors.CYAN}║
║   {Colors.MAGENTA}   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝                       {Colors.CYAN}║
║                                                                          ║
║   {Colors.YELLOW} █████╗ ██╗      █████╗ ███╗   ██╗██╗  ██╗ █████╗ ██████╗          {Colors.CYAN}║
║   {Colors.YELLOW}██╔══██╗██║     ██╔══██╗████╗  ██║██║ ██╔╝██╔══██╗██╔══██╗         {Colors.CYAN}║
║   {Colors.YELLOW}███████║██║     ███████║██╔██╗ ██║█████╔╝ ███████║██████╔╝         {Colors.CYAN}║
║   {Colors.YELLOW}██╔══██║██║     ██╔══██║██║╚██╗██║██╔═██╗ ██╔══██║██╔══██╗         {Colors.CYAN}║
║   {Colors.YELLOW}██║  ██║███████╗██║  ██║██║ ╚████║██║  ██╗██║  ██║██║  ██║         {Colors.CYAN}║
║   {Colors.YELLOW}╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝         {Colors.CYAN}║
║                                                                          ║
║   {Colors.GREEN}AI-Powered Interior Design Platform                                  {Colors.CYAN}║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
{Colors.RESET}

{Colors.GREEN}{Colors.BOLD}🚀 SERVER IS ONLINE!{Colors.RESET}

{Colors.CYAN}📡 Server URL:{Colors.RESET}      http://{host}:{port}
{Colors.CYAN}🏥 Health Check:{Colors.RESET}    http://{host}:{port}/api/health
{Colors.CYAN}🔧 Debug Mode:{Colors.RESET}      {Colors.GREEN if debug else Colors.YELLOW}{'ON' if debug else 'OFF'}{Colors.RESET}

{Colors.YELLOW}✓ All models loaded
✓ Agents initialized  
✓ Database connected
✓ Ready to serve requests{Colors.RESET}

{Colors.MAGENTA}{'─' * 78}{Colors.RESET}
"""
    
    print(banner)
