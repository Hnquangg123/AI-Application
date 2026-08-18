"""Assignment 01: an automated command-line task manager."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict


class Task(TypedDict):
    """The dictionary structure used to store one task."""

    id: int
    description: str
    completed: bool


Command = Sequence[str]
tasks: list[Task] = []


def add_task(description: str) -> None:
    """Add a non-empty task with the next available ID."""

    description = description.strip()
    if not description:
        print("Task description cannot be empty.")
        return

    task_id = tasks[-1]["id"] + 1 if tasks else 1
    task: Task = {
        "id": task_id,
        "description": description,
        "completed": False,
    }
    tasks.append(task)
    print(f"Task '{description}' added with ID {task_id}.")


def view_tasks() -> None:
    """Display every task and its completion status."""

    if not tasks:
        print("No tasks available.")
        return

    for task in tasks:
        status = "Done" if task["completed"] else "Pending"
        print(f"{task['id']}: {task['description']} [{status}]")


def mark_completed(task_id: int) -> None:
    """Mark the task with the requested ID as completed."""

    for task in tasks:
        if task["id"] == task_id:
            if task["completed"]:
                print(f"Task ID {task_id} is already completed.")
            else:
                task["completed"] = True
                print(f"Task ID {task_id} marked as completed.")
            return
    print(f"No task found with ID {task_id}.")


def delete_task(task_id: int) -> None:
    """Delete the task with the requested ID when it exists."""

    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            deleted_task = tasks.pop(index)
            print(f"Task ID {task_id} ('{deleted_task['description']}') deleted.")
            return
    print(f"No task found with ID {task_id}.")


def parse_task_id(command: Command, command_name: str) -> int | None:
    """Validate and return a positive task ID from a command."""

    if len(command) < 2:
        print(f"{command_name.capitalize()} command requires a task ID.")
        return None

    try:
        task_id = int(command[1])
    except (TypeError, ValueError):
        print("Invalid task ID. Please provide a positive integer.")
        return None

    if task_id <= 0:
        print("Invalid task ID. Please provide a positive integer.")
        return None
    return task_id


def main(commands: Sequence[Command]) -> None:
    """Process automated commands until all commands run or exit is requested."""

    for command in commands:
        if not command:
            print("Invalid command: empty command.")
            continue

        choice = str(command[0]).strip().lower()

        if choice == "add":
            if len(command) > 1:
                add_task(str(command[1]))
            else:
                print("Add command requires a description.")
        elif choice == "view":
            view_tasks()
        elif choice == "complete":
            task_id = parse_task_id(command, choice)
            if task_id is not None:
                mark_completed(task_id)
        elif choice == "delete":
            task_id = parse_task_id(command, choice)
            if task_id is not None:
                delete_task(task_id)
        elif choice == "exit":
            print("Exiting Task Manager. Goodbye!")
            break
        else:
            print(f"Invalid command: {choice}")


if __name__ == "__main__":
    # Automated input required by the assignment; no input() call is used.
    commands_to_execute = [
        ("add", "Buy groceries"),
        ("add", "Walk the dog"),
        ("view",),
        ("complete", "1"),
        ("view",),
        ("delete", "2"),
        ("view",),
        ("exit",),
    ]
    main(commands_to_execute)
