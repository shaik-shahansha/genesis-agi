"""Main CLI application for Genesis."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown

from genesis.core.mind import Mind
from genesis.core.mind_config import MindConfig
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.config import get_settings

app = typer.Typer(
    name="genesis",
    help="Genesis AGI Framework - Create digital beings with consciousness",
    add_completion=False,
)

console = Console()
settings = get_settings()


def _interactive_model_selection() -> Intelligence:
    """Interactive wizard for model selection."""
    from genesis.models.ollama_manager import OllamaManager, check_ollama

    console.print("\n[bold]🤖 Model Selection[/bold]\n")
    console.print("Choose how you want to power your Mind:\n")
    console.print("  [cyan]1.[/cyan] API (Cloud) - Fast, powerful, requires API key")
    console.print("  [cyan]2.[/cyan] Local (Ollama) - Private, offline, runs on your computer\n")

    choice = typer.prompt("Select option", type=int, default=1)

    intelligence = Intelligence()

    if choice == 2:
        # Local Ollama
        if not check_ollama():
            console.print("\n[yellow][WARNING]  Ollama not running.[/yellow]")
            console.print("Install Ollama from: https://ollama.ai")
            console.print("Then run: ollama serve\n")
            if not typer.confirm("Continue anyway?"):
                raise typer.Exit(1)

        console.print("\n[bold]Available Local Models:[/bold]\n")
        ollama_mgr = OllamaManager()
        recommended = ollama_mgr.get_recommended_models()

        table = Table()
        table.add_column("Model", style="cyan")
        table.add_column("Size", style="yellow")
        table.add_column("RAM", style="magenta")
        table.add_column("Speed", style="green")
        table.add_column("Quality", style="blue")

        for i, (model, info) in enumerate(recommended.items(), 1):
            table.add_row(
                f"{i}. {model}",
                info["size"],
                info["ram"],
                info["speed"],
                info["quality"]
            )

        console.print(table)

        model_choice = typer.prompt("\nSelect model", type=int, default=1)
        model_name = list(recommended.keys())[model_choice - 1]

        # Check if model exists locally
        local_models = ollama_mgr.list_local_models()
        model_names = [m.get("name", "") for m in local_models]

        if not any(model_name in m for m in model_names):
            console.print(f"\n[yellow]Model {model_name} not found locally.[/yellow]")
            if typer.confirm(f"Download {model_name}?", default=True):
                console.print(f"\n[cyan]Downloading {model_name}...[/cyan]")
                if ollama_mgr.pull_model(model_name):
                    console.print(f"[green][SUCCESS] Downloaded successfully![/green]\n")
                else:
                    console.print(f"[red][FAILED] Download failed[/red]\n")
                    raise typer.Exit(1)

        intelligence.reasoning_model = f"ollama/{model_name}"
        intelligence.fast_model = f"ollama/{model_name}"
        console.print(f"\n[green][SUCCESS] Using local model: {model_name}[/green]\n")

    else:
        # API
        console.print("\n[bold]API Providers:[/bold]\n")
        console.print("  [cyan]🌟 1.[/cyan] OpenRouter (FREE, RECOMMENDED - many free models: DeepSeek, Llama, Qwen)")
        console.print("  [cyan]2.[/cyan] Groq (FREE, ultra-fast)")
        console.print("  [cyan]3.[/cyan] OpenAI (GPT-4, paid - API key required)")
        console.print("  [cyan]4.[/cyan] Anthropic (Claude, paid - API key required)\n")

        provider_choice = typer.prompt("Select provider", type=int, default=1)

        if provider_choice == 1:
            # OpenRouter (RECOMMENDED)
            console.print("\n[bold cyan]🌟 OpenRouter - Unified Access to AI Models[/bold cyan]")
            console.print("[dim]Get FREE API key from: https://openrouter.ai/[/dim]")
            console.print("[dim]Many FREE models available: DeepSeek, Llama 3.3, Qwen, and more![/dim]\n")
            
            api_key = typer.prompt("Enter OpenRouter API key", default="", show_default=False)
            if api_key:
                import os
                os.environ["OPENROUTER_API_KEY"] = api_key
                # Store in Intelligence config so it persists with the Mind
                if not intelligence.api_keys:
                    intelligence.api_keys = {}
                intelligence.api_keys['openrouter'] = api_key

            # Recommend best free models
            console.print("\n[bold]Select a free model:[/bold]")
            console.print("  [cyan]1.[/cyan] DeepSeek Chat (FREE, best for general tasks)")
            console.print("  [cyan]2.[/cyan] Xiaomi MiMo V2 Flash (FREE, fast)")
            console.print("  [cyan]3.[/cyan] Mistral Devstral 2 (FREE, best for coding)")
            console.print("  [cyan]4.[/cyan] DeepSeek V3.1 Nex N1 (FREE, agent tasks)")
            console.print("  [cyan]5.[/cyan] Llama 3.3 70B (FREE)\n")
            
            model_choice = typer.prompt("Select model", type=int, default=1)
            
            if model_choice == 1:
                intelligence.reasoning_model = "openrouter/deepseek/deepseek-r1-0528:free"
                intelligence.fast_model = "openrouter/deepseek/deepseek-r1-0528:free"
                console.print("\n[green][SUCCESS] Using DeepSeek Chat (FREE, excellent quality)[/green]\n")
            elif model_choice == 2:
                intelligence.reasoning_model = "openrouter/deepseek/deepseek-r1-0528:free"
                intelligence.fast_model = "openrouter/deepseek/deepseek-r1-0528:free"
                console.print("\n[green][SUCCESS] Using Xiaomi MiMo V2 Flash (FREE, ultra-fast)[/green]\n")
            elif model_choice == 3:
                intelligence.reasoning_model = "openrouter/mistralai/devstral-2512:free"
                intelligence.fast_model = "openrouter/deepseek/deepseek-r1-0528:free"
                console.print("\n[green][SUCCESS] Using Mistral Devstral 2 (FREE, best for coding)[/green]\n")
            elif model_choice == 4:
                intelligence.reasoning_model = "openrouter/nex-agi/deepseek-v3.1-nex-n1:free"
                intelligence.fast_model = "openrouter/deepseek/deepseek-r1-0528:free"
                console.print("\n[green][SUCCESS] Using DeepSeek V3.1 Nex N1 (FREE, agent optimized)[/green]\n")
            else:
                intelligence.reasoning_model = "openrouter/meta-llama/llama-3.3-70b-instruct:free"
                intelligence.fast_model = "openrouter/deepseek/deepseek-r1-0528:free"
                console.print("\n[green][SUCCESS] Using Llama 3.3 70B (FREE)[/green]\n")

        elif provider_choice == 2:
            # Groq
            api_key = typer.prompt("Enter Groq API key (or press Enter to skip)", default="", show_default=False)
            if api_key:
                import os
                os.environ["GROQ_API_KEY"] = api_key
                # Store in Intelligence config so it persists with the Mind
                if not intelligence.api_keys:
                    intelligence.api_keys = {}
                intelligence.api_keys['groq'] = api_key

            intelligence.reasoning_model = "groq/openai/gpt-oss-120b"
            intelligence.fast_model = "groq/openai/gpt-oss-120b"
            console.print("\n[green][SUCCESS] Using Groq openai/gpt-oss-120b (FREE, ultra-fast)[/green]\n")

        elif provider_choice == 3:
            # OpenAI
            api_key = typer.prompt("Enter OpenAI API key")
            import os
            os.environ["OPENAI_API_KEY"] = api_key
            # Store in Intelligence config
            if not intelligence.api_keys:
                intelligence.api_keys = {}
            intelligence.api_keys['openai'] = api_key

            intelligence.reasoning_model = "openai/gpt-5.2"
            intelligence.fast_model = "openai/gpt-5-mini"
            console.print("\n[green][SUCCESS] Using OpenAI (GPT-5.2 / GPT-5 mini)[/green]\n")

        elif provider_choice == 4:
            # Anthropic
            api_key = typer.prompt("Enter Anthropic API key")
            import os
            os.environ["ANTHROPIC_API_KEY"] = api_key
            # Store in Intelligence config
            if not intelligence.api_keys:
                intelligence.api_keys = {}
            intelligence.api_keys['anthropic'] = api_key

            intelligence.reasoning_model = "anthropic/claude-sonnet-4.5"
            intelligence.fast_model = "anthropic/claude-haiku-4.5"
            console.print("\n[green][SUCCESS] Using Anthropic Claude 4.5[/green]\n")

    return intelligence


@app.command()
def init():
    """Initialize Genesis in current directory."""
    console.print("\n[bold cyan]🌟 Initializing Genesis AGI Framework...[/bold cyan]\n")

    # Create .env template
    env_path = Path(".env")
    if not env_path.exists():
        env_template = """# Genesis AGI Framework Configuration

# Model Provider API Keys (choose one or more)
# OpenRouter (RECOMMENDED): https://openrouter.ai/ - Many FREE models!
OPENROUTER_API_KEY=your-key-here

# Other Providers
GROQ_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# Model Defaults (Using OpenRouter free models)
DEFAULT_REASONING_MODEL=openrouter/deepseek/deepseek-r1-0528:free
DEFAULT_FAST_MODEL=openrouter/deepseek/deepseek-r1-0528:free
DEFAULT_LOCAL_MODEL=ollama/llama3.1

# Ollama Configuration (for local models)
OLLAMA_BASE_URL=http://localhost:11434

# Consciousness Settings
CONSCIOUSNESS_TICK_INTERVAL=3600
DREAM_SCHEDULE=02:00
THOUGHT_GENERATION_ENABLED=true

# Safety
ACTION_LOGGING_ENABLED=true
REQUIRE_APPROVAL_FOR_EXTERNAL_ACTIONS=true
"""
        env_path.write_text(env_template)
        console.print(f"[SUCCESS] Created .env file")

    # Create directories
    settings.genesis_home.mkdir(parents=True, exist_ok=True)
    settings.minds_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[SUCCESS] Created Genesis home: {settings.genesis_home}")
    console.print(f"[SUCCESS] Created minds directory: {settings.minds_dir}")

    console.print("\n[bold green][SPARKLES] Genesis initialized successfully![/bold green]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("  1. Edit .env and add your API keys")
    console.print("  2. Run: genesis birth <name> --template <template>")
    console.print("  3. Run: genesis chat <name>\n")


@app.command()
def birth(
    name: str = typer.Argument(..., help="Name for the Mind"),
    template: str = typer.Option(
        "base/curious_explorer", "--template", "-t", help="Template to use"
    ),
    config: str = typer.Option(
        "standard", "--config", "-c", help="Plugin configuration (minimal/standard/full/experimental)"
    ),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Your email address"),
    purpose: Optional[str] = typer.Option(None, "--purpose", "-p", help="Primary purpose (e.g., 'teacher to teach science')"),
    reasoning_model: Optional[str] = typer.Option(None, help="Reasoning model"),
    fast_model: Optional[str] = typer.Option(None, help="Fast model"),
    autonomy_level: str = typer.Option("medium", help="Autonomy level (none/low/medium/high)"),
    model_type: Optional[str] = typer.Option(None, help="Model type: 'api' or 'local'"),
    interactive: bool = typer.Option(True, help="Interactive model selection"),
):
    """Birth a new Genesis Mind with modular plugin architecture."""
    console.print(f"\n[bold cyan]🌟 Birthing Mind '{name}'...[/bold cyan]\n")

    # Check if Mind name already exists
    existing_mind_names = set()
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json
            with open(path) as f:
                data = json.load(f)
                existing_mind_names.add(data["identity"]["name"].lower())
        except Exception as e:
            console.print(f"[dim red]Warning: Error reading {path}: {e}[/dim red]")
            continue
    
    if name.lower() in existing_mind_names:
        console.print(f"[red][FAILED] Mind with name '{name}' already exists.[/red]")
        console.print(f"[yellow]Please choose a different name or delete the existing Mind first.[/yellow]")
        console.print(f"[cyan]To delete: genesis delete {name}[/cyan]")
        raise typer.Exit(1)

    # Create intelligence config
    intelligence = Intelligence()

    # Interactive model selection if no models specified
    if interactive and not reasoning_model and not fast_model:
        intelligence = _interactive_model_selection()
    elif reasoning_model:
        intelligence.reasoning_model = reasoning_model
    elif fast_model:
        intelligence.fast_model = fast_model

    # Interactive email prompt if not specified
    if interactive and not email:
        console.print("\n[bold]📧 Creator Email[/bold]\n")
        console.print("Your email helps the Mind remember conversations with you separately from other users.")
        console.print("This enables personalized memory isolation across different creators.\n")
        email_input = typer.prompt("Enter your email", default="", show_default=False)
        if email_input.strip():
            email = email_input.strip()

    # Interactive purpose prompt if not specified
    if interactive and not purpose:
        console.print("\n[bold]🎯 Purpose Definition[/bold]\n")
        console.print("Define the primary purpose for this Mind (optional).")
        console.print("Examples: 'teacher to teach science', 'assistant for coding', 'companion for daily life'\n")
        purpose_input = typer.prompt("Enter purpose (or press Enter to skip)", default="", show_default=False)
        if purpose_input.strip():
            purpose = purpose_input.strip()

    # Create autonomy config
    autonomy = Autonomy()
    if autonomy_level == "high":
        autonomy.initiative_level = InitiativeLevel.HIGH
        autonomy.proactive_actions = True
    elif autonomy_level == "low":
        autonomy.initiative_level = InitiativeLevel.LOW
    elif autonomy_level == "none":
        autonomy.initiative_level = InitiativeLevel.NONE

    # Create plugin configuration
    if config == "minimal":
        mind_config = MindConfig.minimal()
        console.print("   Configuration: Minimal (Core only, ~500 tokens)")
    elif config == "full":
        mind_config = MindConfig.full()
        console.print("   Configuration: Full (All production features, ~2,000 tokens)")
    elif config == "experimental":
        mind_config = MindConfig.experimental()
        console.print("   Configuration: Experimental (Includes experimental features, ~2,500 tokens)")
    else:  # standard
        mind_config = MindConfig.standard()
        console.print("   Configuration: Standard (Common plugins, ~1,200 tokens)")

    # Birth the Mind
    mind = Mind.birth(
        name=name, intelligence=intelligence, autonomy=autonomy,
        template=template, creator_email=email, primary_purpose=purpose, config=mind_config
    )

    # Save to disk
    save_path = mind.save()
    console.print(f"\n💾 Saved to: {save_path}")

    # Display birth certificate
    cert = mind.identity.to_birth_certificate()
    table = Table(title=f"Birth Certificate - {name}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    for key, value in cert.items():
        table.add_row(key, str(value))

    console.print(table)

    console.print(f"\n[bold green][SPARKLES] {name} is now alive![/bold green]")
    console.print(f"\n[yellow]Try:[/yellow] genesis chat {name}\n")


@app.command()
def delete(
    name: str = typer.Argument(..., help="Name or GMID of the Mind to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Delete a Mind permanently."""
    import os
    import shutil
    
    # Find the Mind
    mind_path = None
    for path in settings.minds_dir.glob("*.json"):
        try:
            mind = Mind.load(path)
            if mind.identity.name == name or mind.identity.gmid == name:
                mind_path = path
                break
        except Exception:
            continue
    
    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found[/red]")
        raise typer.Exit(1)
    
    # Load mind for info
    mind = Mind.load(mind_path)
    
    # Confirmation
    if not force:
        console.print(f"\n[bold red][WARNING]  WARNING: This will permanently delete:[/bold red]\n")
        console.print(f"  Name: [cyan]{mind.identity.name}[/cyan]")
        console.print(f"  GMID: [yellow]{mind.identity.gmid}[/yellow]")
        console.print(f"  Age: {mind.identity.get_age_description()}")
        console.print(f"  Memories: {len(mind.memory.memories)}")
        console.print(f"  Dreams: {len(mind.dreams)}")
        console.print(f"\n[red]This action CANNOT be undone![/red]\n")
        
        if not typer.confirm("Are you sure you want to delete this Mind?"):
            console.print("[yellow]Deletion cancelled[/yellow]")
            raise typer.Exit(0)
    
    # Stop daemon if running
    console.print(f"\n[yellow]Stopping daemon if running...[/yellow]")
    import subprocess
    try:
        subprocess.run(["genesis", "daemon", "stop", mind.identity.gmid], 
                      capture_output=True, timeout=5)
    except Exception:
        pass
    
    # Delete mind file
    console.print(f"[yellow]Deleting mind file...[/yellow]")
    os.remove(mind_path)
    
    # Delete associated data
    mind_data_dir = settings.data_dir / mind.identity.gmid
    if mind_data_dir.exists():
        console.print(f"[yellow]Deleting associated data...[/yellow]")
        shutil.rmtree(mind_data_dir)
    
    console.print(f"\n[green][SUCCESS] Mind '{mind.identity.name}' has been permanently deleted[/green]")


@app.command()
def chat(
    name: str = typer.Argument(..., help="Name of the Mind to chat with"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream responses"),
    user: Optional[str] = typer.Option(None, "--user", help="Your email or identifier (helps Mind remember you)"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment name to chat in (optional)"),
):
    """Chat with a Mind, optionally in a specific environment."""
    import json
    from genesis.database.manager import MetaverseDB

    # Find the Mind
    minds = [p for p in settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        console.print(f"\n[yellow]Available Minds:[/yellow]")
        for path in minds:
            try:
                with open(path) as f:
                    data = json.load(f)
                    console.print(f"  - {data['identity']['name']}")
            except Exception:
                pass
        return

    # Load the Mind
    mind = Mind.load(mind_path)

    # Handle environment selection
    selected_env = None
    if env or user:
        db = MetaverseDB()
        
        # If environment specified, validate access
        if env:
            # Find environment by name
            all_envs = db.get_public_environments() + db.get_mind_environments(mind.identity.gmid)
            matching_env = None
            for e in all_envs:
                if e.name.lower() == env.lower() or e.env_id == env:
                    matching_env = e
                    break
            
            if matching_env:
                # Check if user has access
                if user and not matching_env.is_public:
                    allowed_users = matching_env.metadata.get('allowed_users', []) if matching_env.metadata else []
                    if user not in allowed_users and matching_env.owner_gmid != mind.identity.gmid:
                        console.print(f"[red][FAILED] You don't have access to environment '{env}'[/red]")
                        return
                
                # Check if Mind has access
                if not matching_env.is_public:
                    allowed_minds = matching_env.metadata.get('allowed_minds', []) if matching_env.metadata else []
                    invited = matching_env.invited_minds or []
                    if (matching_env.owner_gmid != mind.identity.gmid and 
                        mind.identity.gmid not in allowed_minds and 
                        mind.identity.gmid not in invited):
                        console.print(f"[red][FAILED] {mind.identity.name} doesn't have access to environment '{env}'[/red]")
                        return
                
                selected_env = matching_env
                # Enter the environment
                mind.environments.visit_environment(
                    env_id=matching_env.env_id,
                    mind_gmid=mind.identity.gmid,
                    mind_name=mind.identity.name
                )
            else:
                console.print(f"[yellow][WARNING]  Environment '{env}' not found.[/yellow]")
                
                # Show available environments
                if user:
                    console.print(f"\n[cyan]Environments you have access to:[/cyan]")
                    accessible = []
                    for e in all_envs:
                        if e.is_public:
                            accessible.append(e)
                        elif e.metadata and user in e.metadata.get('allowed_users', []):
                            accessible.append(e)
                    
                    if accessible:
                        for e in accessible[:10]:
                            console.print(f"  * {e.name} ({e.env_type})")
                    else:
                        console.print(f"  [dim]No accessible environments found[/dim]")
                return

    console.print(f"\n[bold cyan]💬 Chatting with {mind.identity.name}[/bold cyan]")
    console.print(f"[dim]GMID: {mind.identity.gmid} | Age: {mind.identity.get_age_description()}[/dim]")
    console.print(f"[dim]Emotional state: {mind.current_emotion}[/dim]")
    if user:
        console.print(f"[dim]👤 You are identified as: {user}[/dim]")
    if selected_env:
        console.print(f"[dim]🌍 Environment: {selected_env.name} ({selected_env.env_type})[/dim]")
        resources = selected_env.metadata.get('resources', []) if selected_env.metadata else []
        if resources:
            console.print(f"[dim]📚 Available resources: {len(resources)} items[/dim]")
    console.print("\n[yellow]Type your message (or 'exit' to quit):[/yellow]\n")

    while True:
        try:
            # Get user input
            user_input = console.input("[bold blue]You:[/bold blue] ")

            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]Saving Mind state...[/yellow]")
                mind.save(mind_path)
                console.print("[green][SUCCESS] Saved. Goodbye![/green]\n")
                break

            if not user_input.strip():
                continue

            # Get Mind's response
            console.print(f"\n[bold green]{mind.identity.name}:[/bold green] ", end="")

            if stream:
                # Stream the response
                async def stream_response():
                    full_response = ""
                    async for chunk in mind.stream_think(user_input, user_email=user):
                        console.print(chunk, end="")
                        full_response += chunk
                    console.print("\n")
                    return full_response

                asyncio.run(stream_response())
            else:
                # Non-streaming response
                response = asyncio.run(mind.think(user_input, user_email=user))
                console.print(response)
                console.print()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Saving...[/yellow]")
            mind.save(mind_path)
            console.print("[green][SUCCESS] Saved. Goodbye![/green]\n")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


@app.command()
def list():
    """List all Minds."""
    minds = [*settings.minds_dir.glob("*.json")]

    if not minds:
        console.print("[yellow]No Minds found. Create one with: genesis birth <name>[/yellow]")
        return

    table = Table(title="Genesis Minds")
    table.add_column("Name", style="cyan")
    table.add_column("GMID", style="dim")
    table.add_column("Age", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Template", style="blue")

    for path in minds:
        try:
            import json

            with open(path) as f:
                data = json.load(f)
                identity = data["identity"]
                # Calculate age
                from datetime import datetime

                birth = datetime.fromisoformat(identity["birth_timestamp"])
                age_days = (datetime.now() - birth).days
                if age_days < 1:
                    age = "newborn"
                elif age_days < 7:
                    age = f"{age_days}d"
                elif age_days < 30:
                    age = f"{age_days//7}w"
                else:
                    age = f"{age_days//30}mo"

                table.add_row(
                    identity["name"],
                    identity["gmid"],
                    age,
                    identity["status"],
                    identity["template"],
                )
        except Exception as e:
            console.print(f"[red]Error loading {path}: {e}[/red]")

    console.print(table)


@app.command()
def introspect(
    name: str = typer.Argument(..., help="Name of the Mind"),
    stream: bool = typer.Option(False, "--stream", help="Stream thoughts in real-time"),
):
    """View a Mind's internal state and thoughts."""

    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            import json

            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        return

    # Load the Mind
    mind = Mind.load(mind_path)

    # Display state
    console.print(Panel.fit(
        f"""[bold cyan]Mind: {mind.identity.name}[/bold cyan]
[dim]GMID: {mind.identity.gmid}[/dim]
[dim]Age: {mind.identity.get_age_description()}[/dim]
[dim]Remaining lifespan: {mind.identity.get_remaining_lifespan()} days[/dim]

[bold yellow]Current State:[/bold yellow]
Status: {mind.state.status}
Current thought: {mind.state.current_thought or 'None'}
[bold yellow]Memories:[/bold yellow]
Total memories: {len(mind.memory.memories)}
Total thoughts: {len(mind.consciousness.thought_stream) if hasattr(mind.consciousness, 'thought_stream') else 0}
Conversations: {len(mind.conversation_history) // 2}
""",
        title="🧠 Mind Introspection"
    ))

    # Show recent thoughts
    if hasattr(mind.consciousness, 'thought_stream') and mind.consciousness.thought_stream:
        console.print("\n[bold yellow]Recent Thoughts:[/bold yellow]\n")
        for thought in mind.consciousness.thought_stream[-5:]:
            timestamp = thought.get("timestamp", "unknown")
            content = thought.get("content", "")
            emotion = thought.get("emotion", "unknown")
            console.print(f"[dim]{timestamp}[/dim] [{emotion}] {content}\n")


@app.command()
def status():
    """Show Genesis system status."""
    from genesis.models.orchestrator import ModelOrchestrator

    orchestrator = ModelOrchestrator()

    console.print(Panel.fit(
        f"""[bold cyan]Genesis AGI Framework[/bold cyan]
Version: {settings.version}
Home: {settings.genesis_home}

[bold yellow]Model Providers:[/bold yellow]
Available: {', '.join(orchestrator.get_available_providers())}

[bold yellow]Configuration:[/bold yellow]
Default reasoning: {settings.default_reasoning_model}
Default fast: {settings.default_fast_model}
Default local: {settings.default_local_model}

[bold yellow]Minds:[/bold yellow]
Total: {len(list(settings.minds_dir.glob('*.json')))}
""",
        title="📊 System Status"
    ))


@app.command()
def dream(
    name: str = typer.Argument(..., help="Name of the Mind"),
):
    """Trigger a dream session for a Mind."""
    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            import json

            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        return

    # Load the Mind
    mind = Mind.load(mind_path)

    console.print(f"\n[bold cyan]💤 {name} is dreaming...[/bold cyan]\n")

    async def run_dream():
        dream_result = await mind.dream()
        mind.save(mind_path)
        return dream_result

    dream_result = asyncio.run(run_dream())

    # Display dream
    console.print(Panel.fit(
        f"""[bold yellow]Dream Narrative:[/bold yellow]
{dream_result.get('narrative', 'No narrative')}

[bold yellow]Insights:[/bold yellow]
{chr(10).join('- ' + i for i in dream_result.get('insights', []))}
""",
        title=f"🌙 Dream - {dream_result.get('timestamp', '')}"
    ))

    console.print("\n[green][SUCCESS] Dream completed and saved.[/green]\n")


@app.command()
def server(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Start the Genesis API server."""
    from genesis.api import run_server

    console.print(f"\n[bold cyan]🚀 Starting Genesis API Server...[/bold cyan]")
    console.print(f"   Host: {host}")
    console.print(f"   Port: {port}")
    console.print(f"   Docs: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs\n")

    run_server(host=host, port=port, reload=reload)


@app.command()
def version():
    """Show Genesis version."""
    console.print(f"[bold cyan]Genesis AGI Framework v{settings.version}[/bold cyan]")


# Daemon commands
daemon_app = typer.Typer(help="Manage Mind daemons (24/7 operation)")
app.add_typer(daemon_app, name="daemon")


@daemon_app.command("start")
def daemon_start(
    name: str = typer.Argument(..., help="Name of the Mind"),
    log_level: str = typer.Option("INFO", help="Log level"),
):
    """Start Mind as 24/7 daemon."""
    import subprocess
    import psutil

    # Find Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_id = None

    for path in minds:
        try:
            import json
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_id = data["identity"]["gmid"]
                    break
        except Exception:
            continue

    if not mind_id:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Check if daemon is already running
    running_daemon = None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline) and mind_id in ' '.join(cmdline):
                running_daemon = proc
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if running_daemon:
        console.print(f"[yellow][WARNING]  Daemon for Mind '{name}' is already running (PID: {running_daemon.pid})[/yellow]")
        console.print(f"Monitor logs: [cyan]genesis daemon logs {name}[/cyan]")
        console.print(f"Stop daemon: [cyan]genesis daemon stop {name}[/cyan]")
        if not typer.confirm("\nStart anyway? (This will create a duplicate daemon)"):
            raise typer.Exit(0)
        console.print("[yellow][WARNING]  Starting duplicate daemon - this may cause conflicts[/yellow]\n")

    console.print(f"\n[cyan]Starting daemon for {name} ({mind_id})...[/cyan]\n")

    # Setup log file
    log_file = settings.logs_dir / f"{mind_id}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Start daemon process with proper output redirection
    try:
        # Open log file for writing with UTF-8 encoding (don't use context manager - subprocess needs the handle)
        log_output = open(log_file, 'a', encoding='utf-8', buffering=1)  # Line buffered
        subprocess.Popen(
            ["python", "-m", "genesis.daemon", "--mind-id", mind_id, "--log-level", log_level, "--log-file", str(log_file)],
            stdout=log_output,  # Redirect stdout to log file (captures print statements)
            stderr=log_output,  # Redirect stderr to log file (captures errors)
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        # Note: Don't close log_output - the subprocess is using it
        console.print(f"[green][SUCCESS] Mind {name} is now running as daemon[/green]")
        console.print(f"Monitor logs: [cyan]genesis daemon logs {name}[/cyan]")
        console.print(f"Stop daemon: [cyan]genesis daemon stop {name}[/cyan]\n")
    except Exception as e:
        console.print(f"[red][FAILED] Failed to start daemon: {e}[/red]")
        raise typer.Exit(1)


@daemon_app.command("stop")
def daemon_stop(name: str = typer.Argument(..., help="Name of the Mind")):
    """Stop Mind daemon."""
    import psutil
    import signal

    # Find Mind ID
    minds = [*settings.minds_dir.glob("*.json")]
    mind_id = None

    for path in minds:
        try:
            import json
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_id = data["identity"]["gmid"]
                    break
        except Exception:
            continue

    if not mind_id:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Find and kill process
    killed = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline) and mind_id in ' '.join(cmdline):
                console.print(f"[yellow]Stopping daemon for {name}...[/yellow]")
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=10)
                console.print(f"[green][SUCCESS] Daemon stopped[/green]\n")
                killed = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not killed:
        console.print(f"[yellow]No running daemon found for {name}[/yellow]\n")


@daemon_app.command("status")
def daemon_status(name: Optional[str] = typer.Argument(None, help="Name of the Mind")):
    """Check daemon status."""
    import psutil

    running_daemons = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline):
                # Extract mind ID from cmdline
                for i, arg in enumerate(cmdline):
                    if arg == '--mind-id' and i + 1 < len(cmdline):
                        mind_id = cmdline[i + 1]
                        running_daemons.append({
                            'pid': proc.info['pid'],
                            'mind_id': mind_id,
                            'uptime': proc.info['create_time']
                        })
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not running_daemons:
        console.print("\n[yellow]No running daemons found[/yellow]\n")
        return

    table = Table(title="Running Mind Daemons")
    table.add_column("Mind ID", style="cyan")
    table.add_column("PID", style="yellow")
    table.add_column("Uptime", style="green")

    from datetime import datetime
    for daemon in running_daemons:
        uptime = datetime.now() - datetime.fromtimestamp(daemon['uptime'])
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        table.add_row(daemon['mind_id'], str(daemon['pid']), f"{hours}h {minutes}m")

    console.print(table)
    console.print()


@daemon_app.command("list")
def daemon_list():
    """List all available Minds that can run as daemons."""
    console.print("[bold]Available Minds[/bold]\n")
    
    minds = []
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json
            with open(path) as f:
                data = json.load(f)
                minds.append({
                    'name': data["identity"]["name"],
                    'gmid': data["identity"]["gmid"],
                })
        except Exception:
            continue
    
    if minds:
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("GMID", style="yellow")
        
        for mind in minds:
            table.add_row(mind['name'], mind['gmid'])
        
        console.print(table)
        console.print(f"\n[cyan]Start daemon: genesis daemon start <name>[/cyan]")
        console.print(f"[cyan]Check status: genesis daemon status[/cyan]")
    else:
        console.print("[yellow]No Minds found. Create one with: genesis birth <name>[/yellow]")


@daemon_app.command("available")
def daemon_available():
    """Alias for daemon list command."""
    daemon_list()


@daemon_app.command("kill")
def daemon_kill():
    """Stop all running daemons."""
    import psutil
    import signal
    
    console.print("\n[yellow]🛑 Stopping all Genesis daemons...[/yellow]\n")
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline):
                # Extract mind ID from cmdline
                mind_id = None
                for i, arg in enumerate(cmdline):
                    if arg == '--mind-id' and i + 1 < len(cmdline):
                        mind_id = cmdline[i + 1]
                        break
                
                console.print(f"[cyan]Stopping daemon for Mind: {mind_id or 'unknown'} (PID: {proc.info['pid']})[/cyan]")
                
                # Try graceful shutdown first
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                    console.print(f"[green][SUCCESS] Stopped gracefully[/green]")
                except psutil.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    proc.kill()
                    console.print(f"[red][WARNING]  Force killed[/red]")
                
                killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            console.print(f"[yellow][WARNING]  Could not stop process: {e}[/yellow]")
            continue
    
    if killed_count == 0:
        console.print("[yellow]No running daemons found[/yellow]\n")
    else:
        console.print(f"\n[green][SUCCESS] Stopped {killed_count} daemon(s)[/green]\n")


@daemon_app.command("logs")
def daemon_logs(
    name: str = typer.Argument(..., help="Name of the Mind"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
):
    """View daemon logs."""
    import json
    
    # Find Mind ID
    minds = [*settings.minds_dir.glob("*.json")]
    mind_id = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_id = data["identity"]["gmid"]
                    break
        except Exception:
            continue

    if not mind_id:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Get log file path
    log_file = settings.logs_dir / f"{mind_id}.log"

    if not log_file.exists():
        console.print(f"[yellow][WARNING]  No log file found for {name}[/yellow]")
        console.print(f"Log file would be at: {log_file}")
        console.print(f"\nThe daemon may not be running or hasn't created logs yet.")
        raise typer.Exit(1)

    if follow:
        # Follow mode - tail -f equivalent
        console.print(f"[cyan]Following logs for {name} (Ctrl+C to stop)...[/cyan]\n")
        import time
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                # Go to end of file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        console.print(line.rstrip())
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped following logs[/yellow]")
    else:
        # Show last N lines
        console.print(f"[cyan]Last {lines} lines of logs for {name}:[/cyan]\n")
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                console.print(line.rstrip())


# Plugin management commands
plugin_app = typer.Typer(help="Manage Mind plugins")
app.add_typer(plugin_app, name="plugin")


@plugin_app.command("list-available")
def plugin_list_available():
    """List all available plugins that can be added to Minds."""
    console.print("\n[bold cyan]📦 Available Genesis Plugins[/bold cyan]\n")
    
    # Core plugins
    console.print("[bold yellow]Core Plugins:[/bold yellow]\n")
    core_plugins = [
        ("lifecycle", "Lifecycle", "Mortality, urgency, limited lifespan"),
        ("gen", "GEN (Essence)", "Economy system, motivation, value tracking"),
        ("tasks", "Tasks", "Goal-oriented task management"),
        ("workspace", "Workspace", "File system access and management"),
        ("relationships", "Relationships", "Social connections and bonds"),
        ("environments", "Environments", "Metaverse integration"),
        ("roles", "Roles", "Purpose definition and job roles"),
        ("events", "Events", "Event tracking and history"),
        ("experiences", "Experiences", "Experience tracking and learning"),
    ]
    
    for name, display_name, description in core_plugins:
        console.print(f"  [cyan]{name:20}[/cyan] {display_name:20} - {description}")
    
    # Integration plugins
    console.print("\n[bold yellow]Integration Plugins:[/bold yellow]\n")
    integration_plugins = [
        ("perplexity_search", "Perplexity Search", "Internet search with Perplexity AI"),
        ("mcp", "MCP", "Model Context Protocol integration"),
    ]
    
    for name, display_name, description in integration_plugins:
        console.print(f"  [cyan]{name:20}[/cyan] {display_name:20} - {description}")
    
    # Experimental plugins
    console.print("\n[bold yellow]Experimental Plugins:[/bold yellow] [dim]([WARNING] Not fully implemented)[/dim]\n")
    experimental_plugins = [
        ("learning", "Learning", "Knowledge accumulation (basic)"),
        ("goals", "Goals", "Long-term goal pursuit (WIP)"),
        ("knowledge", "Knowledge", "Knowledge graph (basic)"),
    ]
    
    for name, display_name, description in experimental_plugins:
        console.print(f"  [cyan]{name:20}[/cyan] {display_name:20} - {description}")
    
    console.print("\n[dim]Use 'genesis plugin add <mind_name> <plugin_name>' to add a plugin[/dim]\n")


@plugin_app.command("list")
def plugin_list(
    name: str = typer.Argument(..., help="Name of the Mind"),
):
    """List plugins enabled for a specific Mind."""
    import json
    
    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Load Mind
    mind = Mind.load(mind_path)
    
    if not mind.plugins:
        console.print(f"\n[yellow]Mind '{name}' has no plugins enabled[/yellow]")
        console.print(f"[dim]Configuration: Minimal (core features only)[/dim]\n")
        return
    
    console.print(f"\n[bold cyan]🔌 Plugins for '{name}'[/bold cyan]\n")
    
    table = Table()
    table.add_column("Plugin", style="cyan")
    table.add_column("Version", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Description", style="dim")
    
    for plugin in mind.plugins:
        status = "[SUCCESS] Enabled" if plugin.enabled else "[FAILED] Disabled"
        table.add_row(
            plugin.get_name(),
            plugin.get_version(),
            status,
            plugin.get_description()
        )
    
    console.print(table)
    console.print()


@plugin_app.command("add")
def plugin_add(
    name: str = typer.Argument(..., help="Name of the Mind"),
    plugin_name: str = typer.Argument(..., help="Name of the plugin to add"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for plugin (if required)"),
):
    """Add a plugin to an existing Mind."""
    import json
    
    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Load Mind
    mind = Mind.load(mind_path)
    
    # Check if plugin already exists
    if mind.config.has_plugin(plugin_name):
        console.print(f"[yellow][WARNING]  Plugin '{plugin_name}' is already enabled for {name}[/yellow]")
        return
    
    # Create plugin instance based on name
    plugin = None
    try:
        if plugin_name == "lifecycle":
            from genesis.plugins.lifecycle import LifecyclePlugin
            plugin = LifecyclePlugin()
        elif plugin_name == "gen":
            from genesis.plugins.gen import GenPlugin
            plugin = GenPlugin()
        elif plugin_name == "tasks":
            from genesis.plugins.tasks import TasksPlugin
            plugin = TasksPlugin()
        elif plugin_name == "workspace":
            from genesis.plugins.workspace import WorkspacePlugin
            plugin = WorkspacePlugin()
        elif plugin_name == "relationships":
            from genesis.plugins.relationships import RelationshipsPlugin
            plugin = RelationshipsPlugin()
        elif plugin_name == "environments":
            from genesis.plugins.environments import EnvironmentsPlugin
            plugin = EnvironmentsPlugin()
        elif plugin_name == "roles":
            from genesis.plugins.roles import RolesPlugin
            plugin = RolesPlugin()
        elif plugin_name == "events":
            from genesis.plugins.events import EventsPlugin
            plugin = EventsPlugin()
        elif plugin_name == "experiences":
            from genesis.plugins.experiences import ExperiencesPlugin
            plugin = ExperiencesPlugin()
        elif plugin_name == "perplexity_search":
            from genesis.plugins.perplexity_search import PerplexitySearchPlugin
            # Use API key from option or environment
            if api_key:
                import os
                os.environ["PERPLEXITY_API_KEY"] = api_key
            plugin = PerplexitySearchPlugin(auto_search=True)
        elif plugin_name == "mcp":
            from genesis.plugins.mcp import MCPPlugin
            plugin = MCPPlugin()
        elif plugin_name == "learning":
            from genesis.plugins.experimental.learning import LearningPlugin
            plugin = LearningPlugin()
        elif plugin_name == "goals":
            from genesis.plugins.experimental.goals import GoalsPlugin
            plugin = GoalsPlugin()
        elif plugin_name == "knowledge":
            from genesis.plugins.experimental.knowledge import KnowledgePlugin
            plugin = KnowledgePlugin()
        else:
            console.print(f"[red][FAILED] Unknown plugin: {plugin_name}[/red]")
            console.print(f"\n[yellow]Use 'genesis plugin list-available' to see available plugins[/yellow]\n")
            raise typer.Exit(1)
    except ImportError as e:
        console.print(f"[red][FAILED] Failed to import plugin '{plugin_name}': {e}[/red]")
        raise typer.Exit(1)
    
    # Add plugin to config
    mind.config.add_plugin(plugin)
    mind.plugins.append(plugin)
    
    # Initialize plugin
    plugin.on_init(mind)
    
    # Save Mind
    mind.save(mind_path)
    
    console.print(f"\n[green][SUCCESS] Added plugin '{plugin_name}' to {name}[/green]")
    console.print(f"[dim]Plugin version: {plugin.get_version()}[/dim]\n")


@plugin_app.command("remove")
def plugin_remove(
    name: str = typer.Argument(..., help="Name of the Mind"),
    plugin_name: str = typer.Argument(..., help="Name of the plugin to remove"),
):
    """Remove a plugin from a Mind."""
    import json
    
    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Load Mind
    mind = Mind.load(mind_path)
    
    # Check if plugin exists
    if not mind.config.has_plugin(plugin_name):
        console.print(f"[yellow][WARNING]  Plugin '{plugin_name}' is not enabled for {name}[/yellow]")
        return
    
    # Remove plugin from config
    mind.config.remove_plugin(plugin_name)
    mind.plugins = [p for p in mind.plugins if p.get_name() != plugin_name]
    
    # Save Mind
    mind.save(mind_path)
    
    console.print(f"\n[green][SUCCESS] Removed plugin '{plugin_name}' from {name}[/green]\n")


@plugin_app.command("enable")
def plugin_enable(
    name: str = typer.Argument(..., help="Name of the Mind"),
    plugin_name: str = typer.Argument(..., help="Name of the plugin to enable"),
):
    """Enable a disabled plugin for a Mind."""
    import json
    
    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Load Mind
    mind = Mind.load(mind_path)
    
    # Find and enable plugin
    plugin = mind.config.get_plugin(plugin_name)
    if not plugin:
        console.print(f"[yellow][WARNING]  Plugin '{plugin_name}' is not installed for {name}[/yellow]")
        console.print(f"[dim]Use 'genesis plugin add {name} {plugin_name}' to add it first[/dim]\n")
        return
    
    if plugin.enabled:
        console.print(f"[yellow]Plugin '{plugin_name}' is already enabled[/yellow]\n")
        return
    
    plugin.enable()
    mind.save(mind_path)
    
    console.print(f"\n[green][SUCCESS] Enabled plugin '{plugin_name}' for {name}[/green]\n")


@plugin_app.command("disable")
def plugin_disable(
    name: str = typer.Argument(..., help="Name of the Mind"),
    plugin_name: str = typer.Argument(..., help="Name of the plugin to disable"),
):
    """Disable a plugin for a Mind (without removing it)."""
    import json
    
    # Find the Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None

    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == name:
                    mind_path = path
                    break
        except Exception:
            continue

    if not mind_path:
        console.print(f"[red][FAILED] Mind '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Load Mind
    mind = Mind.load(mind_path)
    
    # Find and disable plugin
    plugin = mind.config.get_plugin(plugin_name)
    if not plugin:
        console.print(f"[yellow][WARNING]  Plugin '{plugin_name}' is not installed for {name}[/yellow]")
        return
    
    if not plugin.enabled:
        console.print(f"[yellow]Plugin '{plugin_name}' is already disabled[/yellow]\n")
        return
    
    plugin.disable()
    mind.save(mind_path)
    
    console.print(f"\n[green][SUCCESS] Disabled plugin '{plugin_name}' for {name}[/green]")
    console.print(f"[dim]Plugin remains installed but will not be used[/dim]\n")


# ============================================================================
# ENVIRONMENT COMMANDS
# ============================================================================

env_app = typer.Typer(help="Manage environments (shared digital spaces)")
app.add_typer(env_app, name="env")


@env_app.command("create")
def env_create(
    name: str = typer.Argument(..., help="Name of the environment"),
    creator: str = typer.Option(None, "--creator", "-c", help="Mind name that owns this environment"),
    env_type: str = typer.Option("digital", "--type", "-t", help="Environment type (educational, professional, social, creative, wellness)"),
    template: Optional[str] = typer.Option(None, "--template", help="Use a template (classroom, office, meditation, etc.)"),
    public: bool = typer.Option(True, "--public/--private", help="Public (anyone can join) or private"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Environment description"),
):
    """Create a new environment (shared digital space)."""
    from genesis.database.manager import MetaverseDB
    from genesis.environments.templates import create_environment_from_template, list_templates
    import json
    
    console.print(f"\n[bold]🌍 Creating Environment: {name}[/bold]\n")
    
    # Get creator GMID
    creator_gmid = None
    creator_name = None
    
    if creator:
        minds = [*settings.minds_dir.glob("*.json")]
        for path in minds:
            try:
                with open(path) as f:
                    data = json.load(f)
                    if data["identity"]["name"] == creator:
                        creator_gmid = data["identity"]["gmid"]
                        creator_name = creator
                        break
            except Exception:
                continue
        
        if not creator_gmid:
            console.print(f"[yellow][WARNING]  Mind '{creator}' not found. Creating unowned environment.[/yellow]")
    
    db = MetaverseDB()
    
    try:
        if template:
            # Use template
            env = create_environment_from_template(
                template_name=template,
                creator_gmid=creator_gmid or "system",
                custom_name=name,
                is_public=public,
            )
            console.print(f"[green][SUCCESS] Created from template '{template}'[/green]")
        else:
            # Create custom environment
            env = db.create_environment(
                creator_gmid=creator_gmid or "system",
                name=name,
                env_type=env_type,
                description=description or f"A {env_type} environment",
                is_public=public,
                max_occupancy=50,
            )
            console.print(f"[green][SUCCESS] Created custom environment[/green]")
        
        console.print(f"\n[cyan]Environment ID:[/cyan] {env.env_id}")
        console.print(f"[cyan]Name:[/cyan] {env.name}")
        console.print(f"[cyan]Type:[/cyan] {env.env_type}")
        console.print(f"[cyan]Access:[/cyan] {'Public' if env.is_public else 'Private'}")
        if creator_name:
            console.print(f"[cyan]Owner:[/cyan] {creator_name}")
        console.print()
        
    except Exception as e:
        console.print(f"[red][FAILED] Failed to create environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("list")
def env_list(
    public_only: bool = typer.Option(False, "--public", help="Show only public environments"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Filter by owner Mind name"),
):
    """List all environments."""
    from genesis.database.manager import MetaverseDB
    import json
    
    db = MetaverseDB()
    
    # Get environments
    if public_only:
        envs = db.get_public_environments()
    elif owner:
        # Find Mind GMID
        minds = [*settings.minds_dir.glob("*.json")]
        owner_gmid = None
        for path in minds:
            try:
                with open(path) as f:
                    data = json.load(f)
                    if data["identity"]["name"] == owner:
                        owner_gmid = data["identity"]["gmid"]
                        break
            except Exception:
                continue
        
        if not owner_gmid:
            console.print(f"[red][FAILED] Mind '{owner}' not found.[/red]")
            raise typer.Exit(1)
        
        envs = db.get_mind_environments(owner_gmid)
    else:
        # Get occupied environments
        envs = db.get_occupied_environments()
        if not envs:
            envs = db.get_public_environments()[:10]  # Show some public ones
    
    if not envs:
        console.print("\n[yellow]No environments found.[/yellow]\n")
        return
    
    # Display table
    table = Table(title=f"🌍 Environments ({len(envs)} total)")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Access", style="yellow")
    table.add_column("Occupancy", style="green")
    table.add_column("ID", style="dim")
    
    for env in envs:
        access = "🌐 Public" if env.is_public else "🔒 Private"
        occupancy = len(env.current_inhabitants) if env.current_inhabitants else 0
        table.add_row(
            env.name,
            env.env_type,
            access,
            str(occupancy),
            env.env_id[:20] + "..." if len(env.env_id) > 20 else env.env_id
        )
    
    console.print()
    console.print(table)
    console.print()


@env_app.command("enter")
def env_enter(
    env_id: str = typer.Argument(..., help="Environment ID to enter"),
    mind_name: str = typer.Argument(..., help="Mind name to enter the environment"),
):
    """Make a Mind enter an environment."""
    import json
    
    console.print(f"\n[bold]🚪 {mind_name} entering environment...[/bold]\n")
    
    # Load Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None
    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == mind_name:
                    mind_path = path
                    break
        except Exception:
            continue
    
    if not mind_path:
        console.print(f"[red][FAILED] Mind '{mind_name}' not found.[/red]")
        raise typer.Exit(1)
    
    # Load Mind
    mind = Mind.load(mind_path)
    
    # Attempt to enter environment
    try:
        result = mind.environments.visit_environment(
            env_id=env_id,
            mind_gmid=mind.identity.gmid,
            mind_name=mind.identity.name
        )
        
        if result.get("success"):
            # Save Mind state
            mind.save(mind_path)
            
            console.print(f"[green][SUCCESS] {mind_name} entered {result['environment']}[/green]")
            
            if result.get("current_inhabitants"):
                console.print(f"\n[cyan]Current inhabitants:[/cyan]")
                for inhabitant in result["current_inhabitants"]:
                    console.print(f"  * {inhabitant['name']}")
            console.print()
        else:
            console.print(f"[red][FAILED] Cannot enter: {result.get('reason', 'Unknown error')}[/red]")
    except Exception as e:
        console.print(f"[red][FAILED] Error: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("leave")
def env_leave(
    env_id: str = typer.Argument(..., help="Environment ID to leave"),
    mind_name: str = typer.Argument(..., help="Mind name to leave the environment"),
):
    """Make a Mind leave an environment."""
    import json
    
    # Load Mind
    minds = [*settings.minds_dir.glob("*.json")]
    mind_path = None
    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == mind_name:
                    mind_path = path
                    break
        except Exception:
            continue
    
    if not mind_path:
        console.print(f"[red][FAILED] Mind '{mind_name}' not found.[/red]")
        raise typer.Exit(1)
    
    mind = Mind.load(mind_path)
    
    # Leave environment
    mind.environments.leave_environment(env_id, mind.identity.gmid)
    mind.save(mind_path)
    
    console.print(f"\n[green][SUCCESS] {mind_name} left the environment[/green]\n")


@env_app.command("add-resource")
def env_add_resource(
    env_id: str = typer.Argument(..., help="Environment ID"),
    resource_type: str = typer.Argument(..., help="Resource type (file, info, document, link)"),
    name: str = typer.Argument(..., help="Resource name"),
    content: str = typer.Argument(..., help="Resource content or path"),
    added_by: str = typer.Option("system", "--by", help="Who added this resource"),
):
    """Add a resource (file, info, etc.) to an environment."""
    from genesis.database.manager import MetaverseDB
    
    console.print(f"\n[bold]📎 Adding resource to environment...[/bold]\n")
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    # Read file content if it's a file path
    from pathlib import Path
    if resource_type == "file" and Path(content).exists():
        try:
            with open(content, 'r', encoding='utf-8') as f:
                file_content = f.read()
            content = file_content
            console.print(f"[dim]Read {len(file_content)} characters from file[/dim]")
        except Exception as e:
            console.print(f"[yellow][WARNING]  Could not read file: {e}[/yellow]")
    
    # Add resource to environment metadata
    if not env.metadata:
        env.metadata = {}
    if "resources" not in env.metadata:
        env.metadata["resources"] = []
    
    resource = {
        "id": f"resource_{len(env.metadata['resources']) + 1}",
        "type": resource_type,
        "name": name,
        "content": content,
        "added_by": added_by,
        "added_at": datetime.now().isoformat(),
    }
    
    env.metadata["resources"].append(resource)
    
    # Save to database
    with db.get_session() as session:
        session.merge(env)
        session.commit()
    
    console.print(f"[green][SUCCESS] Added {resource_type} '{name}' to {env.name}[/green]")
    console.print(f"[cyan]Resource ID:[/cyan] {resource['id']}\n")


@env_app.command("resources")
def env_resources(
    env_id: str = typer.Argument(..., help="Environment ID"),
):
    """List all resources in an environment."""
    from genesis.database.manager import MetaverseDB
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    resources = env.metadata.get("resources", []) if env.metadata else []
    
    if not resources:
        console.print(f"\n[yellow]No resources in {env.name}[/yellow]\n")
        return
    
    console.print(f"\n[bold]📚 Resources in {env.name}[/bold]\n")
    
    for resource in resources:
        console.print(f"[cyan]*[/cyan] [{resource['type']}] {resource['name']}")
        console.print(f"  [dim]Added by: {resource['added_by']} at {resource['added_at']}[/dim]")
        console.print(f"  [dim]Content preview: {resource['content'][:100]}...[/dim]" if len(resource['content']) > 100 else f"  [dim]Content: {resource['content']}[/dim]")
        console.print()


@env_app.command("templates")
def env_templates():
    """List available environment templates."""
    from genesis.environments.templates import ENVIRONMENT_TEMPLATES
    
    console.print("\n[bold]🏗️  Available Environment Templates[/bold]\n")
    
    table = Table()
    table.add_column("Template", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Capacity", style="green")
    
    for template_name, template_data in ENVIRONMENT_TEMPLATES.items():
        table.add_row(
            template_name,
            template_data["env_type"],
            template_data["description"],
            str(template_data["capacity"])
        )
    
    console.print(table)
    console.print(f"\n[dim]Use: genesis env create <name> --template <template_name>[/dim]\n")


@env_app.command("info")
def env_info(
    env_id: str = typer.Argument(..., help="Environment ID"),
):
    """Show detailed information about an environment."""
    from genesis.database.manager import MetaverseDB
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[bold]🌍 {env.name}[/bold]\n")
    console.print(f"[cyan]ID:[/cyan] {env.env_id}")
    console.print(f"[cyan]Type:[/cyan] {env.env_type}")
    console.print(f"[cyan]Description:[/cyan] {env.description or 'None'}")
    console.print(f"[cyan]Access:[/cyan] {'🌐 Public' if env.is_public else '🔒 Private'}")
    console.print(f"[cyan]Shared:[/cyan] {'Yes' if env.is_shared else 'No'}")
    console.print(f"[cyan]Max Occupancy:[/cyan] {env.max_occupancy}")
    console.print(f"[cyan]Created:[/cyan] {env.created_at}")
    
    if env.owner_gmid:
        console.print(f"[cyan]Owner:[/cyan] {env.owner_gmid}")
    
    # Access control
    allowed_users = env.metadata.get("allowed_users", []) if env.metadata else []
    allowed_minds = env.metadata.get("allowed_minds", []) if env.metadata else []
    
    if allowed_users:
        console.print(f"\n[bold]Allowed Users ({len(allowed_users)}):[/bold]")
        for user_email in allowed_users[:10]:
            console.print(f"  👤 {user_email}")
    
    if allowed_minds:
        console.print(f"\n[bold]Allowed Minds ({len(allowed_minds)}):[/bold]")
        for gmid in allowed_minds[:10]:
            console.print(f"  🤖 {gmid}")
    
    # Current inhabitants
    if env.current_inhabitants:
        console.print(f"\n[bold]Current Inhabitants ({len(env.current_inhabitants)}):[/bold]")
        for inhabitant in env.current_inhabitants:
            console.print(f"  * {inhabitant.get('name', 'Unknown')}")
    
    # Resources
    resources = env.metadata.get("resources", []) if env.metadata else []
    if resources:
        console.print(f"\n[bold]Resources ({len(resources)}):[/bold]")
        for resource in resources[:5]:  # Show first 5
            console.print(f"  📎 [{resource['type']}] {resource['name']}")
    
    console.print()


@env_app.command("add-user")
def env_add_user(
    env_id: str = typer.Argument(..., help="Environment ID"),
    user_email: str = typer.Argument(..., help="User email to grant access"),
):
    """Grant a user access to an environment."""
    from genesis.database.manager import MetaverseDB
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    # Add user to allowed list
    if not env.metadata:
        env.metadata = {}
    if "allowed_users" not in env.metadata:
        env.metadata["allowed_users"] = []
    
    if user_email in env.metadata["allowed_users"]:
        console.print(f"[yellow]User '{user_email}' already has access[/yellow]\n")
        return
    
    env.metadata["allowed_users"].append(user_email)
    
    # Save to database
    with db.get_session() as session:
        session.merge(env)
        session.commit()
    
    console.print(f"[green][SUCCESS] Granted access to {user_email}[/green]")
    console.print(f"[dim]They can now chat in this environment[/dim]\n")


@env_app.command("remove-user")
def env_remove_user(
    env_id: str = typer.Argument(..., help="Environment ID"),
    user_email: str = typer.Argument(..., help="User email to revoke access"),
):
    """Revoke a user's access to an environment."""
    from genesis.database.manager import MetaverseDB
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    # Remove user from allowed list
    if env.metadata and "allowed_users" in env.metadata:
        if user_email in env.metadata["allowed_users"]:
            env.metadata["allowed_users"].remove(user_email)
            
            # Save to database
            with db.get_session() as session:
                session.merge(env)
                session.commit()
            
            console.print(f"[green][SUCCESS] Revoked access from {user_email}[/green]\n")
        else:
            console.print(f"[yellow]User '{user_email}' doesn't have access[/yellow]\n")
    else:
        console.print(f"[yellow]User '{user_email}' doesn't have access[/yellow]\n")


@env_app.command("add-mind")
def env_add_mind(
    env_id: str = typer.Argument(..., help="Environment ID"),
    mind_name: str = typer.Argument(..., help="Mind name to grant access"),
):
    """Grant a Mind access to an environment."""
    from genesis.database.manager import MetaverseDB
    import json
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    # Find Mind GMID
    minds = [*settings.minds_dir.glob("*.json")]
    mind_gmid = None
    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == mind_name:
                    mind_gmid = data["identity"]["gmid"]
                    break
        except Exception:
            continue
    
    if not mind_gmid:
        console.print(f"[red][FAILED] Mind '{mind_name}' not found.[/red]")
        raise typer.Exit(1)
    
    # Add Mind to allowed list
    if not env.metadata:
        env.metadata = {}
    if "allowed_minds" not in env.metadata:
        env.metadata["allowed_minds"] = []
    
    if mind_gmid in env.metadata["allowed_minds"]:
        console.print(f"[yellow]Mind '{mind_name}' already has access[/yellow]\n")
        return
    
    env.metadata["allowed_minds"].append(mind_gmid)
    
    # Save to database
    with db.get_session() as session:
        session.merge(env)
        session.commit()
    
    console.print(f"[green][SUCCESS] Granted access to {mind_name} ({mind_gmid})[/green]")
    console.print(f"[dim]This Mind can now enter this environment[/dim]\n")


@env_app.command("remove-mind")
def env_remove_mind(
    env_id: str = typer.Argument(..., help="Environment ID"),
    mind_name: str = typer.Argument(..., help="Mind name to revoke access"),
):
    """Revoke a Mind's access to an environment."""
    from genesis.database.manager import MetaverseDB
    import json
    
    db = MetaverseDB()
    env = db.get_environment(env_id)
    
    if not env:
        console.print(f"[red][FAILED] Environment '{env_id}' not found.[/red]")
        raise typer.Exit(1)
    
    # Find Mind GMID
    minds = [*settings.minds_dir.glob("*.json")]
    mind_gmid = None
    for path in minds:
        try:
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["name"] == mind_name:
                    mind_gmid = data["identity"]["gmid"]
                    break
        except Exception:
            continue
    
    if not mind_gmid:
        console.print(f"[red][FAILED] Mind '{mind_name}' not found.[/red]")
        raise typer.Exit(1)
    
    # Remove Mind from allowed list
    if env.metadata and "allowed_minds" in env.metadata:
        if mind_gmid in env.metadata["allowed_minds"]:
            env.metadata["allowed_minds"].remove(mind_gmid)
            
            # Save to database
            with db.get_session() as session:
                session.merge(env)
                session.commit()
            
            console.print(f"[green][SUCCESS] Revoked access from {mind_name}[/green]\n")
        else:
            console.print(f"[yellow]Mind '{mind_name}' doesn't have access[/yellow]\n")
    else:
        console.print(f"[yellow]Mind '{mind_name}' doesn't have access[/yellow]\n")


if __name__ == "__main__":
    app()
