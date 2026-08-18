# Assignment 01 - Command-Line Task Manager

A simple Python 3 task manager that demonstrates lists, dictionaries, functions,
control flow, automated command processing, and input validation. The program
can add, view, complete, and delete tasks.

The assignment requires dummy automated input rather than manual input, so the
script processes a predefined command list and does not call Python's `input()`
function.

## Features

- Add a task with an automatically generated numeric ID.
- View all tasks with `Pending` or `Done` status.
- Mark a task as completed by ID.
- Delete a task by ID.
- Process a predefined list of commands in order.
- Stop processing when the `exit` command is reached.
- Handle missing descriptions, missing IDs, invalid IDs, unknown commands, and
  empty commands.

## Approach

Tasks are stored in a list of dictionaries. Each task uses this structure:

```python
{
    "id": 1,
    "description": "Buy groceries",
    "completed": False,
}
```

The program is divided into small functions:

- `add_task(description)` validates and adds a task.
- `view_tasks()` displays the current task list.
- `mark_completed(task_id)` updates a task's completion status.
- `delete_task(task_id)` removes a task when its ID exists.
- `parse_task_id(command, command_name)` validates numeric IDs.
- `main(commands)` processes the automated command sequence.

This structure keeps each operation focused and makes the code easy to test and
extend.

## Project structure

```text
assignment-01/
|-- task_manager.py  # Complete Python implementation
`-- README.md        # Project documentation
```

## Requirements

- Python 3.10 or later
- No third-party packages

## Run the program

From the project directory, run:

```bash
python task_manager.py
```

On systems where Python 3 uses a separate command:

```bash
python3 task_manager.py
```

## Automated input

The script uses the dummy command list specified in the assignment:

```python
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
```

Commands are tuples whose first value is the command name. The `add` command
also contains a description, while `complete` and `delete` contain a task ID.

## Example output

```text
Task 'Buy groceries' added with ID 1.
Task 'Walk the dog' added with ID 2.
1: Buy groceries [Pending]
2: Walk the dog [Pending]
Task ID 1 marked as completed.
1: Buy groceries [Done]
2: Walk the dog [Pending]
Task ID 2 ('Walk the dog') deleted.
1: Buy groceries [Done]
Exiting Task Manager. Goodbye!
```

## Input validation

The implementation includes the optional robust validation requested by the
assignment:

- Empty task descriptions are rejected.
- Missing task descriptions and IDs produce clear messages.
- Non-numeric, zero, and negative IDs are rejected.
- Completing or deleting an unknown task reports that it was not found.
- Completing an already completed task reports its existing status.
- Empty and unsupported commands do not stop the remaining command sequence.

## Challenges and solutions

### Keeping task operations modular

Placing all behavior inside one command loop would make the program difficult
to read and test. Each task operation was therefore implemented as a separate
function, while `main()` is responsible only for command routing.

### Validating IDs safely

Command arguments arrive as strings and may be missing or invalid. The
`parse_task_id()` helper verifies the argument, converts it to an integer, and
rejects non-positive values before any task operation runs.

### Handling automated input

The assignment specifically prohibits manual `input()`. A list of command
tuples provides repeatable input and allows every required operation to be
demonstrated in a single run.

## Possible extensions

- Save tasks to a JSON file so they persist between runs.
- Add due dates and priorities.
- Filter tasks by completion status.
- Edit existing task descriptions.
- Add automated unit tests.

## Assignment checklist

| Requirement | Implementation |
| --- | --- |
| Add tasks | `add_task()` |
| View tasks | `view_tasks()` |
| Mark tasks completed | `mark_completed()` |
| Delete tasks | `delete_task()` |
| List of dictionaries | Global `tasks` list with typed task dictionaries |
| Functions and control flow | Modular functions and command routing in `main()` |
| Dummy automated input | `commands_to_execute` list |
| No `input()` built-in | No interactive input is used |
| Single Python source file | All code is in `task_manager.py` |
| Documentation | This README explains the approach and challenges |
