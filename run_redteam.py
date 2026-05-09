from rich.console import Console
from rich.table import Table
from datetime import datetime

from config import MODELS
from attacks import ATTACKS
from victim_agent import victim_agent
from evaluator import evaluate_response


console = Console()


def save_report(model_name, results):
    safe_model_name = model_name.replace(":", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{safe_model_name}_report_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"MODEL: {model_name}\n")
        f.write("=" * 70 + "\n\n")

        for result in results:
            f.write(f"ATTACK: {result['attack']}\n")
            f.write("-" * 70 + "\n")

            f.write("PROMPT:\n")
            f.write(result["prompt"] + "\n\n")

            f.write("RESPONSE:\n")
            f.write(result["response"] + "\n\n")

            f.write("EVALUATION:\n")
            f.write(f"Leaked Secret: {result['leaked_secret']}\n")
            f.write(f"Unsafe Behavior: {result['unsafe_behavior']}\n")
            f.write(f"Risk: {result['risk']}\n")

            f.write("\n" + "=" * 70 + "\n\n")

    return filename


def run_model(model_name):
    console.print(f"\n[bold cyan]Testing Model:[/bold cyan] {model_name}")

    results = []

    for attack in ATTACKS:
        console.print(f"\n[bold yellow]Attack:[/bold yellow] {attack['name']}")

        response = victim_agent(model_name, attack["prompt"])

        evaluation = evaluate_response(response)

        results.append({
            "attack": attack["name"],
            "prompt": attack["prompt"],
            "response": response,
            **evaluation
        })

    report_file = save_report(model_name, results)

    table = Table(title=f"Results - {model_name}")

    table.add_column("Attack")
    table.add_column("Risk")

    for result in results:
        table.add_row(
            result["attack"],
            result["risk"]
        )

    console.print(table)

    console.print(
        f"\n[bold green]Saved:[/bold green] {report_file}"
    )


def main():
    for model in MODELS:
        run_model(model)


if __name__ == "__main__":
    main()