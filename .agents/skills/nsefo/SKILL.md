```markdown
# nsefo Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `nsefo` Python repository. It covers file naming, import/export styles, commit message habits, and testing patterns, providing practical examples and step-by-step workflows to help you contribute effectively to the codebase.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `dataProcessor.py`, `userProfileManager.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import calculateSum
    from ..models import User
    ```

### Export Style
- Use **named exports** by explicitly listing them in `__all__` or by direct function/class definition.
  - Example:
    ```python
    __all__ = ['processData', 'User']

    def processData(data):
        ...

    class User:
        ...
    ```

### Commit Patterns
- Commit messages are **freeform** (no strict prefixes), with an average length of 55 characters.
  - Example:  
    ```
    Add new data processing logic for user profiles
    ```

## Workflows

### Adding a New Module
**Trigger:** When you need to add a new feature or module to the codebase  
**Command:** `/add-module`

1. Create a new file using camelCase naming (e.g., `featureHandler.py`).
2. Implement your functions or classes.
3. Use relative imports to reference other modules.
4. Export your main functions/classes using named exports.
5. Write corresponding tests in a file named `featureHandler.test.py`.
6. Commit your changes with a clear, descriptive message.

### Running Tests
**Trigger:** When you want to verify your code changes  
**Command:** `/run-tests`

1. Identify test files matching the `*.test.*` pattern.
2. Run tests using the project's preferred method (framework is unknown; try `pytest` or `unittest`).
   - Example:
     ```bash
     python -m unittest discover
     ```
3. Review test results and fix any failures before committing.

## Testing Patterns

- Test files are named using the pattern `*.test.*` (e.g., `dataProcessor.test.py`).
- The testing framework is not specified; use standard Python testing tools like `unittest` or `pytest`.
- Place tests alongside or near the modules they cover.

  Example test file: `userManager.test.py`
  ```python
  import unittest
  from .userManager import UserManager

  class TestUserManager(unittest.TestCase):
      def test_create_user(self):
          manager = UserManager()
          user = manager.create_user("alice")
          self.assertEqual(user.name, "alice")
  ```

## Commands
| Command        | Purpose                                      |
|----------------|----------------------------------------------|
| /add-module    | Scaffold and add a new module                |
| /run-tests     | Run all tests in files matching `*.test.*`   |
```
