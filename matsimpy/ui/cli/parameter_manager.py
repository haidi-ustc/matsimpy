"""
Parameter manager for CLI interface.
"""

from typing import Dict, Any, Optional, Callable, List, Union, Tuple
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import print_formatted_text as _print_formatted_text
from prompt_toolkit.completion import WordCompleter, PathCompleter
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.history import FileHistory
import json
from dataclasses import dataclass
from pathlib import Path
import os
from datetime import datetime

# Import matsimpy core modules
from ...core import Crystal, Molecule
from ...io import read


def _safe_print_formatted_text(formatted_text, style=None):
    """Wrapper around print_formatted_text that gracefully handles non-TTY environments."""
    try:
        _print_formatted_text(formatted_text, style=style)
    except Exception:
        pass


@dataclass
class ParameterDefinition:
    """Parameter definition for interface parameters."""

    name: str
    type: type
    description: str
    default: Any = None
    required: bool = False
    validator: Optional[Callable[[Any], bool]] = None
    choices: Optional[List[Any]] = None  # For choice-based parameters
    completer: Optional[Any] = None  # For auto-completion


class ParameterValidator(Validator):
    """Custom validator for parameter input."""

    def __init__(self, param_def: ParameterDefinition):
        self.param_def = param_def

    def validate(self, document):
        text = document.text

        # Allow empty for non-required parameters
        if not text and not self.param_def.required:
            return

        # Check required
        if not text and self.param_def.required and self.param_def.default is None:
            raise ValidationError(message="This parameter is required")

        # Type validation
        if text:
            try:
                if self.param_def.type == bool:
                    if text.lower() not in [
                        "true",
                        "false",
                        "yes",
                        "no",
                        "y",
                        "n",
                        "1",
                        "0",
                    ]:
                        raise ValidationError(
                            message="Please enter true/false, yes/no, y/n, or 1/0"
                        )
                elif self.param_def.type == dict:
                    json.loads(text)
                else:
                    self.param_def.type(text)
            except (ValueError, json.JSONDecodeError):
                raise ValidationError(
                    message=f"Invalid {self.param_def.type.__name__} format"
                )

        # Custom validator
        if text and self.param_def.validator:
            try:
                value = self.param_def.type(text)
                if not self.param_def.validator(value):
                    raise ValidationError(
                        message="Value does not meet validation criteria"
                    )
            except:
                pass


class StructureManager:
    """Separate manager for structure-related operations."""

    def __init__(self, style: Style):
        self.style = style
        self._session = None
        self._recent_structures: List[str] = self._load_recent_structures()

    @property
    def session(self):
        if self._session is None:
            self._session = PromptSession()
        return self._session

    def _load_recent_structures(self) -> List[str]:
        """Load recent structure files from history."""
        history_file = Path.home() / ".matsimpy" / "structure_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    return json.load(f).get("recent", [])
            except:
                pass
        return []

    def _save_recent_structure(self, filepath: str):
        """Save recent structure to history."""
        history_file = Path.home() / ".matsimpy" / "structure_history.json"
        history_file.parent.mkdir(exist_ok=True)

        if filepath not in self._recent_structures:
            self._recent_structures.insert(0, filepath)
            self._recent_structures = self._recent_structures[:10]  # Keep last 10

        try:
            with open(history_file, "w") as f:
                json.dump({"recent": self._recent_structures}, f)
        except:
            pass

    def get_structure_file(
        self, prompt_text: str = "Enter structure file path"
    ) -> Optional[str]:
        """Get structure file path with enhanced features."""
        # Show recent files if available
        if self._recent_structures:
            _safe_print_formatted_text(
                FormattedText([("class:info", "\nRecent structure files:")]),
                style=self.style,
            )

            for i, filepath in enumerate(self._recent_structures[:5], 1):
                if os.path.exists(filepath):
                    _safe_print_formatted_text(
                        FormattedText(
                            [
                                ("class:menu_code", f"  [{i}]"),
                                ("class:menu_item", f" {filepath}"),
                            ]
                        ),
                        style=self.style,
                    )

            _safe_print_formatted_text(
                FormattedText(
                    [
                        (
                            "class:info",
                            "\nEnter number for recent file, or path for new file:",
                        )
                    ]
                ),
                style=self.style,
            )

        # Get input with path completion
        path_completer = PathCompleter(only_directories=False, expanduser=True)

        while True:
            user_input = self.session.prompt(
                FormattedText([("class:prompt", f"{prompt_text}: ")]),
                style=self.style,
                completer=path_completer,
            ).strip()

            if not user_input:
                return None

            # Check if it's a number for recent files
            if user_input.isdigit() and self._recent_structures:
                idx = int(user_input) - 1
                if 0 <= idx < len(self._recent_structures[:5]):
                    filepath = self._recent_structures[idx]
                    if os.path.exists(filepath):
                        self._save_recent_structure(filepath)
                        return filepath
                    else:
                        _safe_print_formatted_text(
                            FormattedText(
                                [("class:error", f"File no longer exists: {filepath}")]
                            ),
                            style=self.style,
                        )
                        continue

            # Expand user path
            filepath = os.path.expanduser(user_input)

            # Check if file exists
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self._save_recent_structure(filepath)
                return filepath
            else:
                _safe_print_formatted_text(
                    FormattedText([("class:error", f"File not found: {filepath}")]),
                    style=self.style,
                )

                # Offer to retry or cancel
                retry = (
                    self.session.prompt(
                        FormattedText([("class:prompt", "Try again? (y/n): ")]),
                        style=self.style,
                    )
                    .strip()
                    .lower()
                )

                if retry not in ["y", "yes"]:
                    return None

    def load_structure(self, filepath: str) -> Optional[Union[Crystal, Molecule]]:
        """Load structure from file using matsimpy.io."""
        try:
            structure = read(filepath)
            _safe_print_formatted_text(
                FormattedText(
                    [
                        (
                            "class:success",
                            f"Successfully loaded structure from: {filepath}",
                        )
                    ]
                ),
                style=self.style,
            )
            return structure
        except Exception as e:
            _safe_print_formatted_text(
                FormattedText([("class:error", f"Error loading structure: {str(e)}")]),
                style=self.style,
            )
            return None


class CLIParameterManager:
    """CLI-based parameter manager with enhanced features."""

    def __init__(self, style: Style):
        self.style = style
        self._session = None
        self.parameter_definitions: List[ParameterDefinition] = []
        self.structure_manager = StructureManager(style)
        self._param_history: Dict[str, Any] = self._load_param_history()

    @property
    def session(self):
        if self._session is None:
            self._session = PromptSession(
                history=FileHistory(str(Path.home() / ".matsimpy" / "param_history"))
            )
        return self._session

    def _load_param_history(self) -> Dict[str, Any]:
        """Load parameter history."""
        history_file = Path.home() / ".matsimpy" / "param_values.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_param_history(self, params: Dict[str, Any]):
        """Save parameter values to history."""
        history_file = Path.home() / ".matsimpy" / "param_values.json"
        history_file.parent.mkdir(exist_ok=True)

        # Update history
        for key, value in params.items():
            if key not in self._param_history:
                self._param_history[key] = []
            if value not in self._param_history[key]:
                self._param_history[key].insert(0, value)
                self._param_history[key] = self._param_history[key][:5]  # Keep last 5

        try:
            with open(history_file, "w") as f:
                json.dump(self._param_history, f)
        except:
            pass

    def add_parameter(self, param_def: ParameterDefinition):
        """Add a parameter definition."""
        self.parameter_definitions.append(param_def)

    def get_parameters(self) -> Dict[str, Any]:
        """Get parameters through CLI interaction with enhanced features."""
        params = {}

        # Show parameter summary
        self._show_parameter_summary()

        # Ask for input method
        _safe_print_formatted_text(
            FormattedText(
                [
                    ("class:info", "\nParameter input options:"),
                    ("", "\n  [1] Individual parameters (recommended for beginners)"),
                    ("", "\n  [2] JSON format (faster for experienced users)"),
                    ("", "\n  [3] Load from file"),
                    ("", "\n  [4] Use previous values (if available)"),
                    ("", "\n\nChoice (default=1): "),
                ]
            ),
            style=self.style,
        )

        # Validate choice input - only accept 1, 2, 3, or 4
        while True:
            choice = (
                self.session.prompt(
                    FormattedText([("class:prompt", "> ")]), style=self.style
                ).strip()
                or "1"
            )

            # Validate choice
            if choice in ["1", "2", "3", "4"]:
                break
            else:
                _safe_print_formatted_text(
                    FormattedText(
                        [
                            (
                                "class:error",
                                f'\nInvalid choice: "{choice}". Please enter 1, 2, 3, or 4 (or press Enter for default).',
                            )
                        ]
                    ),
                    style=self.style,
                )

        if choice == "2":
            params = self._get_parameters_json()
        elif choice == "3":
            params = self._load_parameters_from_file()
        elif choice == "4":
            params = self._use_previous_values()
        else:
            # choice == "1" or default
            params = self._get_parameters_individual()

        # Save to history
        if params:
            self._save_param_history(params)

        return params

    def _show_parameter_summary(self):
        """Show a summary of all parameters."""
        _safe_print_formatted_text(
            FormattedText(
                [
                    ("class:header", "\nParameter Summary:"),
                    ("class:separator", "\n" + "-" * 50),
                ]
            ),
            style=self.style,
        )

        for param in self.parameter_definitions:
            required_mark = "*" if param.required else " "
            default_text = (
                f" (default: {param.default})" if param.default is not None else ""
            )
            _safe_print_formatted_text(
                FormattedText(
                    [
                        ("class:menu_code", f"\n{required_mark} {param.name}"),
                        ("class:info", f" [{param.type.__name__}]{default_text}"),
                        ("class:menu_item", f"\n  {param.description}"),
                    ]
                ),
                style=self.style,
            )

            if param.choices:
                _safe_print_formatted_text(
                    FormattedText(
                        [
                            (
                                "class:info",
                                f'  Choices: {", ".join(str(c) for c in param.choices)}',
                            )
                        ]
                    ),
                    style=self.style,
                )

        _safe_print_formatted_text(
            FormattedText([("class:separator", "\n" + "-" * 50)]), style=self.style
        )

    def _get_parameters_json(self) -> Dict[str, Any]:
        """Get parameters via JSON input."""
        # Generate example
        example_params = {}
        for param in self.parameter_definitions:
            if param.default is not None:
                example_params[param.name] = param.default
            elif param.type == str:
                example_params[param.name] = "example_value"
            elif param.type == int:
                example_params[param.name] = 0
            elif param.type == float:
                example_params[param.name] = 0.0
            elif param.type == bool:
                example_params[param.name] = True
            elif param.type == dict:
                example_params[param.name] = {}
            elif param.type == list:
                example_params[param.name] = []

        _safe_print_formatted_text(
            FormattedText(
                [
                    ("class:info", "\nExample JSON format:"),
                    ("", f"\n{json.dumps(example_params, indent=2)}"),
                    ("class:info", "\n\nYou can input JSON in two ways:"),
                    (
                        "class:info",
                        '\n  1. Single line: {"formula": "H2O", "min_distance": 1.0}',
                    ),
                    (
                        "class:info",
                        '\n  2. Multi-line: End with an empty line or type "END" on a new line',
                    ),
                    (
                        "class:info",
                        "\n\nPaste your JSON (or press Enter for individual input):",
                    ),
                ]
            ),
            style=self.style,
        )

        while True:
            # Try single-line input first
            first_line = self.session.prompt(
                FormattedText([("class:prompt", "> ")]), style=self.style
            ).strip()

            if not first_line:
                return self._get_parameters_individual()

            # Check if it's a complete JSON on one line
            try:
                input_params = json.loads(first_line)
                validated_params = self._validate_parameters(input_params)
                _safe_print_formatted_text(
                    FormattedText(
                        [("class:success", "\nParameters accepted successfully!")]
                    ),
                    style=self.style,
                )
                return validated_params
            except json.JSONDecodeError:
                # Not complete JSON, might be multiline
                pass

            # Collect multiline input
            json_lines = [first_line]
            _safe_print_formatted_text(
                FormattedText(
                    [
                        (
                            "class:info",
                            "Detected multi-line JSON. Continue entering lines.",
                        ),
                        ("", "\n"),
                        (
                            "class:info",
                            'Type "END" on a new line or press Enter twice to finish:',
                        ),
                    ]
                ),
                style=self.style,
            )

            empty_line_count = 0
            while True:
                line = self.session.prompt(
                    FormattedText([("class:prompt", "... ")]), style=self.style
                )

                # Check for end conditions
                if line.strip().upper() == "END":
                    break
                elif line == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                    json_lines.append(line)
                else:
                    empty_line_count = 0
                    json_lines.append(line)

            # Try to parse the collected JSON
            json_input = "\n".join(json_lines).strip()

            try:
                input_params = json.loads(json_input)
                validated_params = self._validate_parameters(input_params)
                _safe_print_formatted_text(
                    FormattedText(
                        [("class:success", "\nParameters accepted successfully!")]
                    ),
                    style=self.style,
                )
                return validated_params

            except json.JSONDecodeError as e:
                _safe_print_formatted_text(
                    FormattedText(
                        [
                            ("class:error", f"\nInvalid JSON: {str(e)}"),
                            (
                                "class:info",
                                "\nTry again or press Enter for individual input:",
                            ),
                        ]
                    ),
                    style=self.style,
                )

    def _load_parameters_from_file(self) -> Dict[str, Any]:
        """Load parameters from a JSON file."""
        path_completer = PathCompleter(only_directories=False, expanduser=True)

        filepath = self.session.prompt(
            FormattedText([("class:prompt", "Enter parameter file path: ")]),
            style=self.style,
            completer=path_completer,
        ).strip()

        if not filepath:
            return self._get_parameters_individual()

        filepath = os.path.expanduser(filepath)

        try:
            with open(filepath, "r") as f:
                input_params = json.load(f)
            validated_params = self._validate_parameters(input_params)
            _safe_print_formatted_text(
                FormattedText(
                    [
                        (
                            "class:success",
                            f"Successfully loaded parameters from: {filepath}",
                        )
                    ]
                ),
                style=self.style,
            )
            return validated_params

        except Exception as e:
            _safe_print_formatted_text(
                FormattedText(
                    [
                        ("class:error", f"Error loading file: {str(e)}"),
                        ("class:info", "\nFalling back to individual input..."),
                    ]
                ),
                style=self.style,
            )
            return self._get_parameters_individual()

    def _use_previous_values(self) -> Dict[str, Any]:
        """Use previous parameter values if available."""
        params = {}
        has_previous = False

        for param in self.parameter_definitions:
            if param.name in self._param_history and self._param_history[param.name]:
                params[param.name] = self._param_history[param.name][0]
                has_previous = True
            else:
                params[param.name] = param.default

        if not has_previous:
            _safe_print_formatted_text(
                FormattedText(
                    [
                        ("class:warning", "No previous values found."),
                        ("class:info", "Falling back to individual input..."),
                    ]
                ),
                style=self.style,
            )
            return self._get_parameters_individual()

        # Show what will be used
        _safe_print_formatted_text(
            FormattedText([("class:info", "\nUsing previous values:")]),
            style=self.style,
        )

        for key, value in params.items():
            _safe_print_formatted_text(
                FormattedText(
                    [("class:menu_code", f"  {key}:"), ("class:menu_item", f" {value}")]
                ),
                style=self.style,
            )

        # Confirm
        confirm = (
            self.session.prompt(
                FormattedText([("class:prompt", "\nUse these values? (y/n): ")]),
                style=self.style,
            )
            .strip()
            .lower()
        )

        if confirm in ["y", "yes"]:
            return params
        else:
            return self._get_parameters_individual()

    def _validate_parameters(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input parameters."""
        params = {}
        errors = []

        for param in self.parameter_definitions:
            if param.name in input_params:
                try:
                    value = param.type(input_params[param.name])
                    if param.validator and not param.validator(value):
                        errors.append(f"{param.name}: validation failed")
                    else:
                        params[param.name] = value
                except Exception as e:
                    errors.append(f"{param.name}: {str(e)}")
            elif param.required and param.default is None:
                errors.append(f"{param.name}: required parameter missing")
            else:
                params[param.name] = param.default

        if errors:
            _safe_print_formatted_text(
                FormattedText([("class:error", "\nValidation errors:")]),
                style=self.style,
            )
            for error in errors:
                _safe_print_formatted_text(
                    FormattedText([("class:error", f"  - {error}")]), style=self.style
                )
            raise ValueError("Parameter validation failed")

        return params

    def _get_parameters_individual(self) -> Dict[str, Any]:
        """Get parameters one by one with enhanced features."""
        params = {}

        _safe_print_formatted_text(
            FormattedText(
                [
                    ("class:info", "\nEnter parameter values:"),
                    ("class:info", "(Tab for completion, ↑/↓ for history)"),
                    (
                        "class:info",
                        "\nTip: Press Enter to use default values for optional parameters",
                    ),
                ]
            ),
            style=self.style,
        )

        for param in self.parameter_definitions:
            # Skip coordinates parameter if position_type is 'random'
            if param.name == "coordinates" and params.get("position_type") == "random":
                # Automatically use default and skip input
                params[param.name] = param.default
                continue

            # Handle non-required parameters with defaults - allow quick skip with Enter
            if not param.required and param.default is not None:
                while True:
                    # Show the parameter with clear indication it's optional
                    prompt_parts = [
                        ("class:info", f"\n{param.name}"),
                        ("", f" ({param.description})"),
                        ("class:info", f" [{param.type.__name__}]"),
                        ("", f" (default: {param.default})"),
                        ("class:info", " - Press Enter to use default"),
                    ]
                    prompt_parts.append(("", "\n"))
                    _safe_print_formatted_text(FormattedText(prompt_parts), style=self.style)

                    value = self.session.prompt(
                        FormattedText([("class:prompt", "> ")]),
                        style=self.style,
                        validator=(
                            ParameterValidator(param) if param.validator else None
                        ),
                    ).strip()

                    # Use default if empty
                    if not value:
                        params[param.name] = param.default
                        break

                    # Convert and validate
                    try:
                        if param.type == bool:
                            if value.lower() in ["true", "yes", "y", "1"]:
                                converted_value = True
                            elif value.lower() in ["false", "no", "n", "0"]:
                                converted_value = False
                            else:
                                raise ValueError("Invalid boolean value")
                        elif param.type == dict:
                            converted_value = json.loads(value)
                        else:
                            converted_value = param.type(value)

                        # Validate
                        if param.validator and not param.validator(converted_value):
                            _safe_print_formatted_text(
                                FormattedText(
                                    [
                                        (
                                            "class:error",
                                            "Value does not meet validation criteria. Please try again.",
                                        )
                                    ]
                                ),
                                style=self.style,
                            )
                            continue  # Retry input

                        params[param.name] = converted_value
                        break  # Success, move to next parameter
                    except (ValueError, json.JSONDecodeError) as e:
                        _safe_print_formatted_text(
                            FormattedText(
                                [
                                    (
                                        "class:error",
                                        f"Invalid value: {str(e)}. Please try again.",
                                    )
                                ]
                            ),
                            style=self.style,
                        )
                        continue  # Retry input
                continue  # Move to next parameter
            while True:
                # Build prompt
                prompt_parts = [
                    ("class:info", f"\n{param.name}"),
                    ("", f" ({param.description})"),
                ]

                if param.type != type(None):
                    prompt_parts.append(("class:info", f" [{param.type.__name__}]"))

                if param.required:
                    prompt_parts.append(("class:error", " *"))

                if param.default is not None:
                    prompt_parts.append(("", f" (default: {param.default})"))

                if param.choices:
                    prompt_parts.append(
                        (
                            "class:info",
                            f'\nChoices: {", ".join(str(c) for c in param.choices)}',
                        )
                    )

                prompt_parts.append(("", "\n"))

                # Show recent values if available
                if (
                    param.name in self._param_history
                    and self._param_history[param.name]
                ):
                    _safe_print_formatted_text(
                        FormattedText(
                            [
                                ("class:info", "Recent values: "),
                                (
                                    "class:menu_item",
                                    ", ".join(
                                        str(v)
                                        for v in self._param_history[param.name][:3]
                                    ),
                                ),
                            ]
                        ),
                        style=self.style,
                    )

                # Get completer
                completer = None
                if param.completer:
                    completer = param.completer
                elif param.choices:
                    completer = WordCompleter([str(c) for c in param.choices])
                elif param.type == bool:
                    completer = WordCompleter(["true", "false", "yes", "no", "y", "n"])

                # Get input
                _safe_print_formatted_text(FormattedText(prompt_parts), style=self.style)

                value = self.session.prompt(
                    FormattedText([("class:prompt", "> ")]),
                    style=self.style,
                    completer=completer,
                    validator=(
                        ParameterValidator(param)
                        if param.required or param.validator
                        else None
                    ),
                ).strip()

                # Handle empty input
                if not value:
                    if param.required and param.default is None:
                        _safe_print_formatted_text(
                            FormattedText(
                                [("class:error", "This parameter is required")]
                            ),
                            style=self.style,
                        )
                        continue
                    params[param.name] = param.default
                    break

                # Convert value
                try:
                    if param.type == bool:
                        # Special handling for boolean
                        if value.lower() in ["true", "yes", "y", "1"]:
                            converted_value = True
                        elif value.lower() in ["false", "no", "n", "0"]:
                            converted_value = False
                        else:
                            raise ValueError(
                                "Please enter true/false, yes/no, y/n, or 1/0"
                            )
                    elif param.type == dict:
                        converted_value = json.loads(value)
                    else:
                        converted_value = param.type(value)

                    # Validate
                    if param.validator and not param.validator(converted_value):
                        _safe_print_formatted_text(
                            FormattedText(
                                [
                                    (
                                        "class:error",
                                        "Value does not meet validation criteria",
                                    )
                                ]
                            ),
                            style=self.style,
                        )
                        continue

                    params[param.name] = converted_value
                    break

                except Exception as e:
                    _safe_print_formatted_text(
                        FormattedText([("class:error", f"Error: {str(e)}")]),
                        style=self.style,
                    )

        return params

    # Maintain original interface methods
    def define_structure_parameter(
        self,
        name: str = "structure_file",
        description: str = "Input structure file path",
        required: bool = True,
    ) -> None:
        """Define a structure file parameter for the CLI interface."""
        self.define_parameter(
            name=name,
            description=description,
            param_type=str,
            required=required,
            default=None,
            validator=self._validate_structure_file,
            completer=PathCompleter(only_directories=False, expanduser=True),
        )

    def _validate_structure_file(self, filepath: str) -> bool:
        """Validate structure file path."""
        try:
            path = Path(filepath)
            return path.exists() and path.is_file()
        except:
            return False

    def get_structure_from_params(
        self, params: Dict[str, Any], param_name: str = "structure_file"
    ) -> Optional[Union[Crystal, Molecule]]:
        """Get structure from parameters using matsimpy.io."""
        if param_name not in params or not params[param_name]:
            return None

        return self.structure_manager.load_structure(params[param_name])

    def get_input_structure(self) -> Optional[Union[Crystal, Molecule]]:
        """Get input structure from user using enhanced features."""
        filepath = self.structure_manager.get_structure_file(
            "Enter input structure file path"
        )
        if filepath:
            return self.structure_manager.load_structure(filepath)
        return None

    def define_parameter(
        self,
        name: str,
        description: str,
        param_type: type,
        required: bool = False,
        default: Any = None,
        validator: Optional[Callable[[Any], bool]] = None,
        choices: Optional[List[Any]] = None,
        completer: Optional[Any] = None,
    ) -> None:
        """Define a parameter for the CLI interface with enhanced features."""
        self.parameter_definitions.append(
            ParameterDefinition(
                name=name,
                type=param_type,
                description=description,
                default=default,
                required=required,
                validator=validator,
                choices=choices,
                completer=completer,
            )
        )

    def save_parameters_to_file(
        self, params: Dict[str, Any], filepath: Optional[str] = None
    ) -> str:
        """Save parameters to a JSON file."""
        if not filepath:
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"parameters_{timestamp}.json"

        filepath = os.path.expanduser(filepath)

        try:
            with open(filepath, "w") as f:
                json.dump(params, f, indent=2)

            _safe_print_formatted_text(
                FormattedText([("class:success", f"Parameters saved to: {filepath}")]),
                style=self.style,
            )
            return filepath

        except Exception as e:
            _safe_print_formatted_text(
                FormattedText([("class:error", f"Error saving parameters: {str(e)}")]),
                style=self.style,
            )
            raise

    def clear_definitions(self):
        """Clear all parameter definitions."""
        self.parameter_definitions.clear()

    def get_quick_params(self, param_string: str) -> Dict[str, Any]:
        """Parse quick parameter string (e.g., 'param1=value1,param2=value2')."""
        params = {}

        if not param_string:
            return params

        try:
            # Split by comma and parse key=value pairs
            pairs = param_string.split(",")
            for pair in pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Find parameter definition
                    param_def = None
                    for pd in self.parameter_definitions:
                        if pd.name == key:
                            param_def = pd
                            break

                    if param_def:
                        # Convert to appropriate type
                        if param_def.type == bool:
                            params[key] = value.lower() in ["true", "yes", "y", "1"]
                        elif param_def.type == dict:
                            params[key] = json.loads(value)
                        else:
                            params[key] = param_def.type(value)
                    else:
                        # Guess type
                        try:
                            params[key] = json.loads(value)
                        except:
                            params[key] = value

            # Fill in defaults for missing required parameters
            for param_def in self.parameter_definitions:
                if param_def.name not in params:
                    if param_def.required and param_def.default is None:
                        raise ValueError(
                            f"Required parameter '{param_def.name}' not provided"
                        )
                    params[param_def.name] = param_def.default

            return params

        except Exception as e:
            _safe_print_formatted_text(
                FormattedText(
                    [("class:error", f"Error parsing quick parameters: {str(e)}")]
                ),
                style=self.style,
            )
            raise
