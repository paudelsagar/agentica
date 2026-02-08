import os
import sys
import uuid

import requests
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

SERVER_URL = "http://localhost:8000"
THREAD_ID = str(uuid.uuid4())


def display_welcome():
    console.clear()
    console.print(
        Panel.fit(
            "[bold cyan]Agentica - Terminal Interface[/bold cyan]\n"
            "[dim]Powered by Google GenAI Toolbox & Multi-Agent Orchestration[/dim]",
            border_style="cyan",
        )
    )
    rprint(f"[dim]Thread ID: {THREAD_ID}[/dim]\n")


def handle_response(response_data, thread_id):
    status = response_data.get("status")
    message = response_data.get("last_message", "")

    if status == "success":
        console.print(
            Panel(
                Markdown(message),
                title="[bold green]Agent Response[/bold green]",
                border_style="green",
            )
        )
    elif status == "requires_action":
        console.print(
            Panel(
                Markdown(message),
                title="[bold yellow]Approval Required[/bold yellow]",
                border_style="yellow",
            )
        )

        choice = Prompt.ask(
            "Approve this action?", choices=["yes", "no", "exit"], default="yes"
        )

        if choice == "yes":
            rprint("[blue]Resuming workflow...[/blue]")
            try:
                resp = requests.post(
                    f"{SERVER_URL}/approve",
                    json={"thread_id": thread_id, "message": "Approve"},
                )
                if resp.status_code == 200:
                    handle_response(resp.json(), thread_id)
                else:
                    rprint(f"[red]Error during approval: {resp.text}[/red]")
            except Exception as e:
                rprint(f"[red]Failed to connect to server: {str(e)}[/red]")
        elif choice == "no":
            rprint("[red]Action denied. Workflow paused.[/red]")
        else:
            sys.exit(0)
    else:
        rprint(f"[red]Unknown status: {status}[/red]")
        rprint(message)


def main():
    display_welcome()

    # Check if server is running
    try:
        requests.get(f"{SERVER_URL}/health")
    except:
        rprint(
            "[bold red]Error: API server is not running on http://localhost:8000[/bold red]"
        )
        rprint("[yellow]Please start the server using `./run.sh start` first.[/yellow]")
        return

    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")

            if user_input.lower() in ["exit", "quit"]:
                rprint("[dim]Goodbye![/dim]")
                break

            if not user_input.strip():
                continue

            with console.status("[bold blue]Agent is thinking...[/bold blue]"):
                response = requests.post(
                    f"{SERVER_URL}/run",
                    json={"thread_id": THREAD_ID, "message": user_input},
                )

            if response.status_code == 200:
                handle_response(response.json(), THREAD_ID)
            else:
                rprint(f"[red]Error: {response.status_code} - {response.text}[/red]")

        except KeyboardInterrupt:
            rprint("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            rprint(f"[red]An error occurred: {str(e)}[/red]")


if __name__ == "__main__":
    main()
