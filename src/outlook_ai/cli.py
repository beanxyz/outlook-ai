"""CLI module for Outlook AI."""

import sys
from datetime import date, datetime, timedelta
from typing import Optional, Union

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.markdown import Markdown

from outlook_ai.config import Config, get_config
from outlook_ai.mail import OutlookMailClient
from outlook_ai.graph import OutlookGraphClient
from outlook_ai.ai import OllamaEmailAI
from outlook_ai.cache import EmailCache
from outlook_ai.models import Priority, Email as MailEmail
from outlook_ai.utils import truncate_string

# Rich console
console = Console()

# Typer app
app = typer.Typer(
    name="outlook-ai",
    help="AI-powered Outlook.com CLI assistant using Ollama",
    add_completion=False,
)

# Global client instances
_graph_client: Optional[OutlookGraphClient] = None
_imap_client: Optional[OutlookMailClient] = None


def get_graph_client() -> OutlookGraphClient:
    """Get or create Graph API client."""
    global _graph_client
    if _graph_client is None:
        config = get_config()
        _graph_client = OutlookGraphClient(
            client_id=config.azure_client_id,
            authority="https://login.microsoftonline.com/consumers"
        )
    return _graph_client


def get_imap_client() -> OutlookMailClient:
    """Get or create IMAP client."""
    global _imap_client
    if _imap_client is None:
        config = get_config()
        _imap_client = OutlookMailClient(
            email=config.email,
            app_password=config.app_password,
            host=config.imap_host,
            port=config.imap_port,
        )
    return _imap_client


def get_ai_client() -> OllamaEmailAI:
    """Get AI client."""
    config = get_config()
    return OllamaEmailAI(
        model=config.ollama_model,
        base_url=config.ollama_base_url,
        timeout=config.ollama_timeout,
    )


def get_cache_client() -> EmailCache:
    """Get cache client."""
    config = get_config()
    return EmailCache(db_path=str(config.get_cache_db_path()))


def get_clients() -> tuple[Union[OutlookGraphClient, OutlookMailClient], OllamaEmailAI, EmailCache, Config]:
    """Initialize all clients and return them.
    
    Uses Graph API if AZURE_CLIENT_ID is configured, otherwise uses IMAP.
    """
    config = get_config()
    
    if config.use_graph_api:
        mail = get_graph_client()
        # Try to get token silently first, only prompt if needed
        try:
            # Check if we already have a valid token
            if mail._token is None:
                # Try silent token acquisition
                accounts = mail._app.get_accounts() if mail._app else []
                if accounts:
                    result = mail._app.acquire_token_silent(
                        scopes=mail.scopes,
                        account=accounts[0]
                    )
                    if "access_token" in result:
                        mail._token = result["access_token"]
                    else:
                        # Token expired or invalid, need to re-authenticate
                        mail.get_token_interactive()
                else:
                    # No cached account, need to authenticate
                    mail.get_token_interactive()
        except Exception as e:
            # Fallback to interactive login
            mail.get_token_interactive()
    else:
        mail = get_imap_client()
    
    ai = get_ai_client()
    cache = get_cache_client()
    return mail, ai, cache, config


@app.command()
def config_cmd(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Outlook email address"),
    app_password: Optional[str] = typer.Option(None, "--password", "-p", help="App password"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Ollama model"),
    save: bool = typer.Option(False, "--save", help="Save configuration to .env file"),
) -> None:
    """Configure outlook-ai settings."""
    console.print("\n[bold]📧 Outlook AI Configuration[/bold]\n")
    
    try:
        current_config = get_config()
        console.print(f"[green]Current email:[/green] {current_config.email}")
        console.print(f"[green]Current model:[/green] {current_config.ollama_model}")
        console.print(f"[green]Ollama URL:[/green] {current_config.ollama_base_url}")
    except ValueError:
        console.print("[yellow]No configuration found. Please set up your settings.[/yellow]")
        current_config = None
    
    if email or app_password or model:
        # Update config
        if current_config:
            if email:
                current_config.email = email
            if app_password:
                current_config.app_password = app_password
            if model:
                current_config.ollama_model = model
            
            if save:
                current_config.save_to_env_file()
                console.print("[green]Configuration saved to ~/.outlook-ai/.env[/green]")
            
            console.print("[green]✓ Configuration updated[/green]")
        else:
            console.print("[red]Cannot update: no base configuration[/red]")
    else:
        console.print("\n[bold]Usage:[/bold]")
        console.print("  outlook-ai config --email you@live.com --password xxxx-xxxx-xxxx-xxxx --model qwen2.5:14b --save")
        console.print("\n[bold]Note:[/bold] Get your app password from: https://account.microsoft.com/security")


@app.command()
def inbox(
    count: int = typer.Option(20, "--count", "-c", help="Number of emails to fetch"),
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
) -> None:
    """View recent emails in inbox."""
    console.print(f"\n[bold]📬 Fetching {count} emails from {folder}...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            emails = mail.fetch_recent(count=count, folder=folder)
            
            if not emails:
                console.print("[yellow]No emails found.[/yellow]")
                return
            
            # Cache emails
            cache.cache_emails(emails)
            
            # Display emails
            _display_email_list(emails)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def unread(
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
) -> None:
    """View unread emails."""
    console.print(f"\n[bold]📬 Fetching unread emails from {folder}...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            emails = mail.fetch_unread(folder=folder)
            
            if not emails:
                console.print("[green]✓ No unread emails.[/green]")
                return
            
            # Cache emails
            cache.cache_emails(emails)
            
            # Display emails
            _display_email_list(emails, show_unread_only=True)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def read(
    uid: str = typer.Argument(..., help="Email UID to read"),
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
) -> None:
    """Read a specific email by UID."""
    console.print(f"\n[bold]📧 Reading email {uid}...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            # Search for the email
            emails = mail.fetch_recent(count=1000, folder=folder)
            target_email = None
            
            for email in emails:
                if email.uid == uid:
                    target_email = email
                    break
            
            if not target_email:
                console.print(f"[red]Email {uid} not found in {folder}.[/red]")
                return
            
            # Display email
            _display_email_content(target_email)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def summary(
    days: int = typer.Option(1, "--days", "-d", help="Number of days to summarize"),
    count: int = typer.Option(10, "--count", "-c", help="Max number of emails to process"),
) -> None:
    """Generate AI summary of recent emails."""
    console.print(f"\n[bold]🤖 Generating AI summary for last {days} days (max {count} emails)...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        # Check Ollama connection
        if not ai.check_connection():
            console.print("[red]Cannot connect to Ollama. Make sure Ollama is running.[/red]")
            raise typer.Exit(1)
        
        since = date.today() - timedelta(days=days)
        
        with mail:
            emails = mail.fetch_by_date_range(since=since)
            
            if not emails:
                console.print("[yellow]No emails found in the specified period.[/yellow]")
                return
            
            console.print(f"[dim]Processing {len(emails)} emails...[/]\n")
            
            # Generate batch summary (pass count to control truncation)
            summary_text = ai.batch_summarize(emails, max_emails=count)
            
            # Display summary
            console.print(Panel(
                summary_text,
                title="📊 Email Summary",
                border_style="blue",
                box=box.ROUNDED,
            ))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def classify(
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
    count: int = typer.Option(50, "--count", "-c", help="Max number of emails to classify"),
) -> None:
    """Classify unread emails using AI."""
    console.print(f"\n[bold]🏷️ Classifying emails in {folder} (max {count})...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            emails = mail.fetch_unread(folder=folder)
            
            if not emails:
                console.print("[green]✓ No unread emails to classify.[/green]")
                return
            
            # Limit to specified count
            emails = emails[:count]
            
            console.print(f"[dim]Classifying {len(emails)} emails...[/]\n")
            
            # Classify each email
            results = []
            for email in emails:
                classification = ai.classify(email)
                results.append((email, classification))
            
            # Display results
            _display_classifications(results)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def reply(
    uid: str = typer.Argument(..., help="Email UID to reply to"),
    intent: str = typer.Option("", "--intent", "-i", help="Reply intent/description"),
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
) -> None:
    """Draft an AI reply to an email."""
    console.print(f"\n[bold]✍️ Drafting reply for email {uid}...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        # Check Ollama connection
        if not ai.check_connection():
            console.print("[red]Cannot connect to Ollama. Make sure Ollama is running.[/red]")
            raise typer.Exit(1)
        
        with mail:
            # Find the email
            emails = mail.fetch_recent(count=1000, folder=folder)
            target_email = None
            
            for email in emails:
                if email.uid == uid:
                    target_email = email
                    break
            
            if not target_email:
                console.print(f"[red]Email {uid} not found.[/red]")
                return
            
            # Display original email
            _display_email_content(target_email)
            
            console.print("\n[bold]🤖 AI Draft Reply:[/bold]\n")
            
            # Generate reply
            draft = ai.draft_reply(target_email, intent=intent)
            
            console.print(Panel(
                draft,
                title="✉️ Draft",
                border_style="green",
                box=box.ROUNDED,
            ))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def actions() -> None:
    """Extract action items from recent emails."""
    console.print("\n[bold]📋 Extracting action items...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        # Check Ollama connection
        if not ai.check_connection():
            console.print("[red]Cannot connect to Ollama. Make sure Ollama is running.[/red]")
            raise typer.Exit(1)
        
        since = date.today() - timedelta(days=7)
        
        with mail:
            emails = mail.fetch_by_date_range(since=since)
            
            if not emails:
                console.print("[yellow]No recent emails found.[/yellow]")
                return
            
            console.print(f"[dim]Analyzing {len(emails)} emails...[/]\n")
            
            # Extract action items
            action_items = ai.extract_action_items(emails)
            
            if not action_items:
                console.print("[green]✓ No action items found.[/green]")
                return
            
            # Save to cache
            for item in action_items:
                item.email_uid = item.from_email_subject  # Use subject as identifier
                cache.save_action_item(item)
            
            # Display action items
            _display_action_items(action_items)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def translate(
    uid: str = typer.Argument(..., help="Email UID to translate"),
    lang: str = typer.Option("zh", "--lang", "-l", help="Target language code (zh, en, ja, etc.)"),
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
) -> None:
    """Translate an email."""
    console.print(f"\n[bold]🌐 Translating email {uid} to {lang}...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        # Check Ollama connection
        if not ai.check_connection():
            console.print("[red]Cannot connect to Ollama. Make sure Ollama is running.[/red]")
            raise typer.Exit(1)
        
        with mail:
            # Find the email
            emails = mail.fetch_recent(count=1000, folder=folder)
            target_email = None
            
            for email in emails:
                if email.uid == uid:
                    target_email = email
                    break
            
            if not target_email:
                console.print(f"[red]Email {uid} not found.[/red]")
                return
            
            # Translate
            translation = ai.translate(target_email, target_lang=lang)
            
            # Display
            console.print(Panel(
                translation,
                title=f"🌍 Translation ({lang})",
                border_style="cyan",
                box=box.ROUNDED,
            ))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
    semantic: bool = typer.Option(False, "--semantic", "-s", help="Use semantic search"),
) -> None:
    """Search emails."""
    console.print(f"\n[bold]🔍 Searching for: {query}[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            if semantic:
                # Semantic search with AI
                if not ai.check_connection():
                    console.print("[red]Cannot connect to Ollama for semantic search.[/red]")
                    raise typer.Exit(1)
                
                # First get recent emails
                emails = mail.fetch_recent(count=50, folder=folder)
                
                if not emails:
                    console.print("[yellow]No emails found.[/yellow]")
                    return
                
                console.print(f"[dim]Performing semantic search on {len(emails)} emails...[/]\n")
                
                # AI semantic search
                results = ai.smart_search(query, emails)
                
                if not results:
                    console.print("[yellow]No relevant emails found.[/yellow]")
                    return
                
                _display_email_list(results, title=f"Semantic Search Results ({len(results)})")
                
            else:
                # Basic IMAP search
                emails = mail.search(query, folder=folder)
                
                if not emails:
                    console.print("[yellow]No emails found.[/yellow]")
                    return
                
                _display_email_list(emails, title=f"Search Results ({len(emails)})")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def folders() -> None:
    """List all email folders."""
    console.print("\n[bold]📁 Email Folders[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            folder_list = mail.get_folders()
            
            if not folder_list:
                console.print("[yellow]No folders found.[/yellow]")
                return
            
            table = Table(box=box.SIMPLE)
            table.add_column("Folder Name", style="cyan")
            
            for folder in folder_list:
                table.add_row(folder)
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def mark_read(
    uid: str = typer.Argument(..., help="Email UID to mark as read"),
    folder: str = typer.Option("INBOX", "--folder", "-f", help="Folder name"),
) -> None:
    """Mark an email as read."""
    try:
        mail, ai, cache, config = get_clients()
        
        with mail:
            if mail.mark_as_read(uid, folder):
                console.print(f"[green]✓ Email {uid} marked as read.[/green]")
            else:
                console.print(f"[red]Failed to mark email {uid} as read.[/red]")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def models() -> None:
    """List available Ollama models."""
    console.print("\n[bold]🤖 Available Ollama Models[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        if not ai.check_connection():
            console.print("[red]Cannot connect to Ollama. Make sure Ollama is running.[/red]")
            raise typer.Exit(1)
        
        model_list = ai.list_models()
        
        if not model_list:
            console.print("[yellow]No models found.[/yellow]")
            return
        
        current_model = config.ollama_model
        
        table = Table(box=box.SIMPLE)
        table.add_column("Model Name", style="cyan")
        table.add_column("Status", style="green")
        
        for model in model_list:
            status = "✓ Current" if model == current_model else ""
            table.add_row(model, status)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cache_clear() -> None:
    """Clear the local cache."""
    console.print("\n[bold]🗑️ Clearing cache...[/]\n")
    
    try:
        mail, ai, cache, config = get_clients()
        
        cache.clear_cache()
        
        console.print("[green]✓ Cache cleared successfully.[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Helper functions for display

def _display_email_list(
    emails: list,
    title: str = "Email List",
    show_unread_only: bool = False,
) -> None:
    """Display a list of emails in a table."""
    header = f"📬 {title}"
    if show_unread_only:
        unread_count = sum(1 for e in emails if not e.is_read)
        header += f" — {unread_count} unread"
    
    table = Table(
        title=header,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Status", width=6)
    table.add_column("From", style="cyan", width=25)
    table.add_column("Subject", style="white", width=40)
    table.add_column("Date", style="dim", width=12)
    
    for i, email in enumerate(emails, 1):
        status = "🔴" if not email.is_read else "⚪"
        sender = truncate_string(email.sender_name or email.sender_email, 22)
        subject = truncate_string(email.subject, 38)
        date_str = email.date.strftime("%m-%d %H:%M")
        
        table.add_row(
            str(i),
            status,
            sender,
            subject,
            date_str,
        )
    
    console.print(table)
    
    # Show AI summaries for unread emails
    if show_unread_only:
        _display_unread_summaries(emails)


def _display_unread_summaries(emails: list) -> None:
    """Display AI summaries for unread emails."""
    try:
        mail, ai, cache, config = get_clients()
        
        if not ai.check_connection():
            return
        
        console.print("\n[bold cyan]─ AI 摘要 ─[/bold cyan]\n")
        
        unread_emails = [e for e in emails if not e.is_read][:5]  # Limit to 5
        
        for email in unread_emails:
            summary = ai.summarize(email)
            
            # Get priority indicator
            priority_indicator = "🔴"
            
            console.print(f"{priority_indicator} [bold]{email.subject[:50]}[/bold]")
            console.print(f"   {summary}\n")
            
    except Exception:
        pass  # Silently skip if AI not available


def _display_email_content(email) -> None:
    """Display full email content."""
    # Header
    header = f"""[bold cyan]From:[/bold cyan] {email.sender}
[bold cyan]To:[/bold cyan] {', '.join(email.to)}
[bold cyan]Date:[/bold cyan] {email.date.strftime('%Y-%m-%d %H:%M:%S')}
[bold cyan]Subject:[/bold cyan] {email.subject}"""
    
    console.print(Panel(
        header,
        title="📧 Email Header",
        border_style="blue",
        box=box.ROUNDED,
    ))
    
    # Body
    console.print("\n[bold cyan]─ Content ─[/bold cyan]\n")
    console.print(email.body_text[:2000])  # Limit display
    if len(email.body_text) > 2000:
        console.print("\n[dim]... (truncated)[/dim]")


def _display_classifications(results: list) -> None:
    """Display email classifications."""
    table = Table(
        title="🏷️ Email Classifications",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Subject", style="white", width=40)
    table.add_column("Category", style="cyan", width=15)
    table.add_column("Priority", style="yellow", width=10)
    table.add_column("Reason", style="dim", width=30)
    
    priority_colors = {
        "high": "red",
        "medium": "yellow",
        "low": "green",
    }
    
    for email, classification in results:
        subject = truncate_string(email.subject, 38)
        category = classification.category.value
        priority = classification.priority.value
        priority_style = priority_colors.get(priority, "white")
        reason = truncate_string(classification.reason, 28)
        
        table.add_row(
            subject,
            f"[cyan]{category}[/cyan]",
            f"[{priority_style}]{priority}[/{priority_style}]",
            reason,
        )
    
    console.print(table)


def _display_action_items(items: list) -> None:
    """Display action items."""
    table = Table(
        title="📋 Action Items",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Priority", width=8)
    table.add_column("Task", style="white", width=50)
    table.add_column("Deadline", style="cyan", width=15)
    table.add_column("From Email", style="dim", width=30)
    
    priority_colors = {
        "high": "red",
        "medium": "yellow",
        "low": "green",
    }
    
    for item in items:
        priority = item.priority.value
        priority_style = priority_colors.get(priority, "white")
        task = truncate_string(item.task, 48)
        deadline = item.deadline or "-"
        from_email = truncate_string(item.from_email_subject or "-", 28)
        
        table.add_row(
            f"[{priority_style}]{priority.upper()}[/{priority_style}]",
            task,
            deadline,
            from_email,
        )
    
    console.print(table)


if __name__ == "__main__":
    app()
