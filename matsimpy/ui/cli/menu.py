#!/usr/bin/env python3
"""
MatSimPy Interactive Menu System - Enhanced Version
Features: Grouped main menu, system commands, simplified interface
"""

import json
import sys
import os
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.shortcuts import print_formatted_text, clear
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from dataclasses import dataclass
from prompt_toolkit.validation import Validator
from matsimpy.ui.cli.parameter_manager import CLIParameterManager


@dataclass
class MenuItem:
    """Menu item data structure"""

    code: str
    name: str
    level: int
    parent: Optional[str] = None


@dataclass
class MenuSession:
    """Session tracking data"""

    start_time: datetime
    commands_executed: int
    navigation_history: List[str]
    last_accessed: Dict[str, datetime]


class AdvancedInteractiveMenu:
    """Advanced interactive menu system with enhanced features"""

    def __init__(self, json_file: str):
        self.menu_data = None
        self.current_level = 1
        self.current_parent = None
        self.menu_history = []
        self.search_results = []
        self.session = MenuSession(
            start_time=datetime.now(),
            commands_executed=0,
            navigation_history=[],
            last_accessed={},
        )

        # Enhanced styling
        self.style = Style.from_dict(
            {
                "title": "#00aa00 bold",
                "header": "#0088ff bold",
                "menu_item": "#ffffff",
                "menu_code": "#ffaa00 bold",
                "separator": "#666666",
                "prompt": "#00ff88 bold",
                "error": "#ff0000 bold",
                "warning": "#ffaa00",
                "info": "#888888",
                "success": "#00ff00",
                "breadcrumb": "#00ffff",
                "stats": "#ffa500",
                "highlight": "#ffff00 bg:#0000aa",
                "group_header": "#ffffff bold",
            }
        )

        # Command completions
        self.base_commands = [
            "b",
            "back",
            "h",
            "help",
            "q",
            "quit",
            "search",
            "find",
            "stats",
            "impl",
            "implementation",
            "status",
            "history",
            "goto",
        ]

        self.key_bindings = KeyBindings()
        self.setup_key_bindings()

        self.load_menu_data(json_file)

    def setup_key_bindings(self):
        """Setup custom key bindings"""

        @self.key_bindings.add("c-c")
        def _(event):
            """Ctrl+C handling"""
            event.app.exit()

    def load_menu_data(self, json_file: str) -> bool:
        """Load menu data from JSON file"""
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                self.menu_data = json.load(f)
            return True
        except FileNotFoundError:
            print(f"Error: JSON file '{json_file}' not found.")
            return False
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format - {e}")
            return False
        except Exception as e:
            print(f"Error loading menu data: {e}")
            return False

    def get_command_completer(self) -> WordCompleter:
        """Get command completer with current menu codes"""
        current_items = self.get_current_menu_items()
        current_codes = [
            item["code"][1:-1] for item in current_items
        ]  # Remove brackets

        all_commands = self.base_commands + current_codes
        return WordCompleter(all_commands, ignore_case=True)

    def format_ascii_header(self) -> FormattedText:
        """Format ASCII header for the main menu"""
        lines = []
        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))
        # Create properly centered header
        title_text = " MatSimPy v2.0 "
        title_centered = title_text.center(70, "=")
        lines.append(("class:title", title_centered))
        lines.append(("", "\n"))
        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))
        return FormattedText(lines)

    def format_grouped_main_menu(self) -> FormattedText:
        """Format main menu with grouped categories"""
        lines = []

        # Header
        header = self.format_ascii_header()
        lines.extend(header)

        # Session info
        session_time = datetime.now() - self.session.start_time
        session_info = f"Session: {session_time.seconds // 60}m {session_time.seconds % 60}s | Commands: {self.session.commands_executed}"
        lines.append(("class:info", session_info.center(70)))
        lines.append(("", "\n"))
        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))

        # Breadcrumb navigation
        if self.menu_history:
            path_items = []
            for item in self.menu_history:
                path_items.append(f"{item['code']} {item['name']}")
            path_str = " → ".join(path_items)
            lines.append(("class:breadcrumb", f"Path: {path_str}"))
            lines.append(("", "\n"))
            lines.append(("class:separator", "-" * 70))
            lines.append(("", "\n"))

        # Main menu groups
        groups = {
            "Structure & Generation": [11, 12, 13, 14],
            "Properties & Analysis": [15, 16, 17, 18, 19, 21, 22, 23, 24, 25],
            "Computational Tools": [26, 27, 28, 29],
            "Database & Tools": [31, 32, 33, 34],
        }

        level1_items = self.get_current_menu_items()
        items_by_code = {int(item["code"][1:-1]): item for item in level1_items}

        for group_name, codes in groups.items():
            # Group header with proper centering using str.center()
            header_text = f" {group_name} "
            centered_header = header_text.center(70, "=")
            lines.append(("class:group_header", centered_header))
            lines.append(("", "\n"))

            # Group items in two columns
            group_items = [
                items_by_code[code] for code in codes if code in items_by_code
            ]

            for i in range(0, len(group_items), 2):
                left_item = group_items[i]
                right_item = group_items[i + 1] if i + 1 < len(group_items) else None

                # Format left item
                left_code = left_item["code"][1:-1]
                left_text = f" [{left_code}] {left_item['name']}"

                if right_item:
                    right_code = right_item["code"][1:-1]
                    right_text = f"[{right_code}] {right_item['name']}"

                    # Calculate spacing for alignment
                    left_width = 35
                    lines.append(("class:menu_item", left_text.ljust(left_width)))
                    lines.append(("class:menu_item", right_text))
                else:
                    lines.append(("class:menu_item", left_text))

                lines.append(("", "\n"))

        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))
        return FormattedText(lines)

    def format_standard_header(self) -> FormattedText:
        """Format standard header for non-main menus"""
        lines = []
        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))

        # Session info
        session_time = datetime.now() - self.session.start_time
        session_text = f"MatSimPy v2.0 - Session: {session_time.seconds // 60}m {session_time.seconds % 60}s | Commands: {self.session.commands_executed}"
        lines.append(("class:title", session_text.center(70)))
        lines.append(("", "\n"))
        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))

        # Breadcrumb navigation
        if self.menu_history:
            path_items = []
            for i, item in enumerate(self.menu_history):
                if i == len(self.menu_history) - 1:
                    # Highlight current item
                    path_items.append(f">>> {item['code']} {item['name']} <<<")
                else:
                    path_items.append(f"{item['code']} {item['name']}")

            path_str = " → ".join(path_items)
            lines.append(("class:breadcrumb", f"Path: {path_str}"))
            lines.append(("", "\n"))

        return FormattedText(lines)

    def format_menu_items(self, items: List[Dict]) -> FormattedText:
        """Format menu items with colored display"""
        lines = []

        if not items:
            lines.append(("class:error", "  No menu items found."))
            lines.append(("", "\n"))
            return FormattedText(lines)

        # Level info
        level_names = {1: "Main Categories", 2: "Sub-Categories", 3: "Operations"}
        lines.append(
            (
                "class:header",
                f"Available {level_names[self.current_level]} (Level {self.current_level}):",
            )
        )
        lines.append(("", "\n"))
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))

        # For level 3, show implementation status
        if self.current_level == 3:
            lines.append(
                (
                    "class:info",
                    "Status: ✓=Implemented ⚠=Partial ✗=Not Implemented ?=Error",
                )
            )
            lines.append(("", "\n"))
            lines.append(("class:separator", "-" * 50))
            lines.append(("", "\n"))

        # Group items for better display (2 columns)
        for i in range(0, len(items), 2):
            left_item = items[i]
            right_item = items[i + 1] if i + 1 < len(items) else None

            # Format left item
            left_code = left_item["code"][1:-1]
            lines.append(("class:menu_item", "  "))
            lines.append(("class:menu_code", f"[{left_code}]"))
            lines.append(("class:menu_item", f" {left_item['name']}"))

            # Add status indicator for level 3
            if self.current_level == 3:
                status = self.check_interface_status(left_item)
                status_icon = self.get_interface_status_icon(status)
                status_color = self.get_interface_status_color(status)
                lines.append(("", " "))
                lines.append((f"class:{status_color}", status_icon))

            if right_item:
                right_code = right_item["code"][1:-1]
                # Calculate spacing for alignment
                left_text_len = len(f"  [{left_code}] {left_item['name']}")
                # Add extra space for status indicator if level 3
                if self.current_level == 3:
                    left_text_len += 2
                spacing = max(3, 40 - left_text_len)
                lines.append(("", " " * spacing))
                lines.append(("class:menu_code", f"[{right_code}]"))
                lines.append(("class:menu_item", f" {right_item['name']}"))

                # Add status indicator for right item if level 3
                if self.current_level == 3:
                    status = self.check_interface_status(right_item)
                    status_icon = self.get_interface_status_icon(status)
                    status_color = self.get_interface_status_color(status)
                    lines.append(("", " "))
                    lines.append((f"class:{status_color}", status_icon))

            lines.append(("", "\n"))

        return FormattedText(lines)

    def format_footer(self) -> FormattedText:
        """Format footer with navigation options"""
        lines = []
        lines.append(("class:separator", "-" * 70))
        lines.append(("", "\n"))

        # Enhanced navigation options
        nav_options = []
        if self.current_level > 1:
            nav_options.append("[b]ack")

        nav_options.extend(
            ["[s]earch", "[h]elp", "[stats]", "[impl]", "[clear]", "[! cmd]", "[q]uit"]
        )

        lines.append(("class:info", "Navigation: "))
        for i, option in enumerate(nav_options):
            if i > 0:
                lines.append(("class:info", " | "))
            lines.append(("class:menu_code", option))
        lines.append(("", "\n"))

        # Quick tips
        tips = [
            "Tip: Type code number to navigate (e.g., '11' or 's11')",
            "Tip: Use 'search <term>' to find items, '! <cmd>' for system commands",
            "Tip: Press Tab for auto-completion, Ctrl+C to exit",
        ]

        import random

        tip = random.choice(tips)
        lines.append(("class:info", tip))
        lines.append(("", "\n"))
        lines.append(("class:separator", "=" * 70))
        lines.append(("", "\n"))

        return FormattedText(lines)

    def get_current_menu_items(self) -> List[Dict]:
        """Get menu items for current level and parent"""
        if self.current_level == 1:
            return self.menu_data["menu_structure"]["level1_items"]
        elif self.current_level == 2:
            if self.current_parent:
                return self.menu_data["menu_structure"]["level2_items"].get(
                    self.current_parent, []
                )
        elif self.current_level == 3:
            if self.current_parent:
                return self.menu_data["menu_structure"]["level3_items"].get(
                    self.current_parent, []
                )
        return []

    def validate_code_uniqueness(self) -> bool:
        """Validate that all menu codes are unique"""
        all_codes = set()
        duplicates = []

        for code, item in self.menu_data["all_items"].items():
            if code in all_codes:
                duplicates.append(code)
            all_codes.add(code)

        if duplicates:
            print(f'Error: Duplicate codes found: {", ".join(duplicates)}')
            return False

        return True

    def find_menu_item(self, code: str) -> Optional[Dict]:
        """Find menu item by code"""
        if not code.startswith("[") or not code.endswith("]"):
            code = f"[{code}]"
        return self.menu_data["all_items"].get(code)

    def search_menu(self, query: str) -> List[Dict]:
        """Search menu items by name or code"""
        results = []
        query_lower = query.lower()

        for code, item in self.menu_data["all_items"].items():
            if query_lower in item["name"].lower() or query_lower in code.lower():
                results.append(item)

        # Sort by level and then by name
        results.sort(key=lambda x: (x["level"], x["name"]))
        return results

    def display_search_results(self, query: str, results: List[Dict]):
        """Display search results with colored formatting"""
        if not results:
            print_formatted_text(
                FormattedText([("class:error", f"No results found for: {query}")]),
                style=self.style,
            )
            return

        lines = []
        lines.append(
            ("class:header", f'Search Results for "{query}" ({len(results)} found)')
        )
        lines.append(("", "\n"))
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))

        # Group by level
        by_level = {1: [], 2: [], 3: []}
        for item in results:
            by_level[item["level"]].append(item)

        level_names = {1: "Main Categories", 2: "Sub-Categories", 3: "Operations"}

        for level in [1, 2, 3]:
            items = by_level[level]
            if items:
                lines.append(("class:header", f"{level_names[level]} (Level {level}):"))
                lines.append(("", "\n"))

                for item in items:
                    lines.append(("class:menu_code", item["code"]))
                    lines.append(("class:menu_item", f" {item['name']}"))

                    if item.get("parent"):
                        parent_item = self.menu_data["all_items"].get(item["parent"])
                        if parent_item:
                            lines.append(
                                ("class:info", f" (under {parent_item['name']})")
                            )
                    lines.append(("", "\n"))
                lines.append(("", "\n"))

        print_formatted_text(FormattedText(lines), style=self.style)

    def execute_system_command(self, command: str) -> bool:
        """Execute system command"""
        try:
            print_formatted_text(
                FormattedText(
                    [
                        ("class:info", f"Executing: {command}"),
                        ("", "\n"),
                        ("class:separator", "-" * 40),
                        ("", "\n"),
                    ]
                ),
                style=self.style,
            )

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.stdout:
                print_formatted_text(
                    FormattedText(
                        [
                            ("class:success", "Output:"),
                            ("", "\n"),
                            ("class:menu_item", result.stdout),
                        ]
                    ),
                    style=self.style,
                )

            if result.stderr:
                print_formatted_text(
                    FormattedText(
                        [
                            ("class:error", "Error:"),
                            ("", "\n"),
                            ("class:error", result.stderr),
                        ]
                    ),
                    style=self.style,
                )

            if result.returncode != 0:
                print_formatted_text(
                    FormattedText(
                        [
                            (
                                "class:warning",
                                f"Command exited with code: {result.returncode}",
                            )
                        ]
                    ),
                    style=self.style,
                )

            print_formatted_text(
                FormattedText([("class:separator", "-" * 40), ("", "\n")]),
                style=self.style,
            )
            return True

        except subprocess.TimeoutExpired:
            print_formatted_text(
                FormattedText(
                    [("class:error", "Error: Command timed out (30s limit)")]
                ),
                style=self.style,
            )
            return False
        except Exception as e:
            print_formatted_text(
                FormattedText([("class:error", f"Error executing command: {e}")]),
                style=self.style,
            )
            return False

    def navigate_to_item(self, code: str) -> bool:
        """Navigate to a menu item with enhanced logic"""
        item = self.find_menu_item(code)

        if not item:
            return False

        # Update last accessed
        self.session.last_accessed[item["code"]] = datetime.now()

        # Smart navigation - can jump directly to any valid item
        if item["level"] == 1:
            # Reset to level 1 and navigate
            self.menu_history = []
            self.menu_history.append(
                {"code": item["code"], "name": item["name"], "level": item["level"]}
            )
            self.current_parent = item["code"]
            self.current_level = 2
            return True

        elif item["level"] == 2:
            # Can navigate if it's a child of current parent or jump directly
            if self.current_level == 2 and item["parent"] == self.current_parent:
                # Navigate to level 3
                self.menu_history.append(
                    {"code": item["code"], "name": item["name"], "level": item["level"]}
                )
                self.current_parent = item["code"]
                self.current_level = 3
                return True
            else:
                # Jump directly - rebuild path
                parent_item = self.find_menu_item(item["parent"])
                if parent_item:
                    self.menu_history = []
                    self.menu_history.append(
                        {
                            "code": parent_item["code"],
                            "name": parent_item["name"],
                            "level": parent_item["level"],
                        }
                    )
                    self.menu_history.append(
                        {
                            "code": item["code"],
                            "name": item["name"],
                            "level": item["level"],
                        }
                    )
                    self.current_parent = item["code"]
                    self.current_level = 3
                    return True

        elif item["level"] == 3:
            # Jump directly to level 3 item - rebuild full path
            parent_item = self.find_menu_item(item["parent"])
            if parent_item:
                grandparent_item = self.find_menu_item(parent_item["parent"])
                if grandparent_item:
                    self.menu_history = []
                    self.menu_history.append(
                        {
                            "code": grandparent_item["code"],
                            "name": grandparent_item["name"],
                            "level": grandparent_item["level"],
                        }
                    )
                    self.menu_history.append(
                        {
                            "code": parent_item["code"],
                            "name": parent_item["name"],
                            "level": parent_item["level"],
                        }
                    )
                    self.current_parent = parent_item["code"]
                    self.current_level = 3

                    # Show the specific operation
                    self.show_operation_details(item)
                    return True

        return False

    def show_operation_details(self, item: Dict):
        """Show details for a Level 3 operation"""
        lines = []
        lines.append(("class:header", f'Operation Details: {item["name"]}'))
        lines.append(("", "\n"))
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))
        lines.append(("class:menu_code", f'Code: {item["code"]}'))
        lines.append(("", "\n"))
        lines.append(("class:menu_item", f'Name: {item["name"]}'))
        lines.append(("", "\n"))
        lines.append(("class:info", f'Level: {item["level"]} (Operation)'))
        lines.append(("", "\n"))

        # Show path
        if item.get("parent"):
            parent_item = self.find_menu_item(item["parent"])
            if parent_item and parent_item.get("parent"):
                grandparent_item = self.find_menu_item(parent_item["parent"])
                if grandparent_item:
                    lines.append(("class:breadcrumb", "Full Path: "))
                    lines.append(("class:breadcrumb", f'{grandparent_item["name"]} → '))
                    lines.append(("class:breadcrumb", f'{parent_item["name"]} → '))
                    lines.append(("class:highlight", f'{item["name"]}'))
                    lines.append(("", "\n"))

        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))

        # Show interface status
        if item.get("interface"):
            status = self.check_interface_status(item)
            status_icon = self.get_interface_status_icon(status)
            status_color = self.get_interface_status_color(status)

            lines.append(("class:info", f'Interface: {item["interface"]}'))
            lines.append(("", " "))
            lines.append((f"class:{status_color}", f"[{status_icon}]"))
            lines.append(("", "\n"))

            # Show status description
            status_descriptions = {
                "implemented": "✓ Fully implemented and ready to use",
                "partial": "⚠ Module exists but function needs implementation",
                "not_implemented": "✗ Module not implemented yet",
                "error": "? Error checking implementation status",
            }
            lines.append(
                (
                    "class:info",
                    f'Status: {status_descriptions.get(status, "Unknown status")}',
                )
            )
            lines.append(("", "\n"))

            if status == "implemented":
                lines.append(("class:success", "This operation is ready to execute."))
                lines.append(("", "\n"))
                self.execute_interface(item)
            else:
                lines.append(
                    ("class:warning", "This operation is not yet fully implemented.")
                )
                lines.append(("", "\n"))
                lines.append(
                    ("class:info", "Press [b] to go back or try to execute anyway.")
                )
                lines.append(("", "\n"))
                print_formatted_text(FormattedText(lines), style=self.style)
                input("Press Enter to continue...")  # Pause for user to read
        else:
            lines.append(("class:warning", "No interface available"))
            lines.append(("", "\n"))
            lines.append(("class:info", "Press [b] to go back"))
            lines.append(("", "\n"))
            print_formatted_text(FormattedText(lines), style=self.style)
            input("Press Enter to continue...")  # Pause for user to read

    def execute_interface(self, item: Dict) -> bool:
        """Execute the interface for a Level 3 operation"""
        interface_path = item.get("interface", "")
        if not interface_path:
            print_formatted_text(
                FormattedText(
                    [
                        ("class:error", "No interface available for this operation"),
                        ("", "\n"),
                        ("class:warning", "This feature is not yet implemented."),
                        ("", "\n"),
                        ("class:info", "To implement this feature:"),
                        ("", "\n"),
                        (
                            "class:info",
                            "1. Create the interface module in matsimpy/ui/cli/interfaces/",
                        ),
                        (
                            "class:info",
                            "2. Define the required function with proper signature",
                        ),
                        (
                            "class:info",
                            "3. Update the menu configuration with the interface path",
                        ),
                        ("", "\n"),
                        ("class:warning", "Press Enter to continue..."),
                        ("", "\n"),
                    ]
                ),
                style=self.style,
            )
            input()  # Pause for user to read
            return False

        try:
            print_formatted_text(
                FormattedText(
                    [("class:info", f"Loading interface: {interface_path}"), ("", "\n")]
                ),
                style=self.style,
            )

            module_name = interface_path.split(":")[0]
            function_name = interface_path.split(":")[1]

            import importlib

            module = importlib.import_module(module_name)

            if hasattr(module, function_name):
                interface_func = getattr(module, function_name)

                print_formatted_text(
                    FormattedText(
                        [
                            ("class:success", f'Executing: {item["name"]}'),
                            ("", "\n"),
                            ("class:info", f"Running: {interface_path}"),
                            ("", "\n"),
                        ]
                    ),
                    style=self.style,
                )

                # Execute interface with parameter manager
                try:
                    result = interface_func(style=self.style)
                except KeyboardInterrupt:
                    print_formatted_text(
                        FormattedText(
                            [
                                ("", "\n"),
                                (
                                    "class:warning",
                                    "Execution interrupted by user. Returning to main menu...",
                                ),
                                ("", "\n"),
                            ]
                        ),
                        style=self.style,
                    )
                    return False

                # Handle result
                if isinstance(result, dict):
                    if result.get("status"):
                        print_formatted_text(
                            FormattedText(
                                [
                                    (
                                        "class:success",
                                        result.get(
                                            "message",
                                            "Operation completed successfully",
                                        ),
                                    ),
                                    ("", "\n"),
                                ]
                            ),
                            style=self.style,
                        )
                    else:
                        print_formatted_text(
                            FormattedText(
                                [
                                    (
                                        "class:error",
                                        result.get("message", "Operation failed"),
                                    ),
                                    ("", "\n"),
                                ]
                            ),
                            style=self.style,
                        )
                else:
                    print_formatted_text(
                        FormattedText(
                            [
                                ("class:success", "Operation completed successfully"),
                                ("", "\n"),
                            ]
                        ),
                        style=self.style,
                    )

                return True
            else:
                print_formatted_text(
                    FormattedText(
                        [
                            (
                                "class:error",
                                f'Function "{function_name}" not found in module "{module_name}"',
                            ),
                            ("", "\n"),
                            (
                                "class:warning",
                                "Module exists but function is not implemented.",
                            ),
                            ("", "\n"),
                            ("class:info", "To implement this function:"),
                            ("", "\n"),
                            (
                                "class:info",
                                f'1. Open file: {module_name.replace(".", "/")}.py',
                            ),
                            (
                                "class:info",
                                f"2. Add function: def {function_name}(style=None):",
                            ),
                            ("class:info", "3. Implement the required functionality"),
                            ("class:info", "4. Return appropriate result dictionary"),
                            ("", "\n"),
                            ("class:info", "Example implementation:"),
                            ("class:info", "def " + function_name + "(style=None):"),
                            ("class:info", "    # Your implementation here"),
                            (
                                "class:info",
                                '    return {"status": True, "message": "Success"}',
                            ),
                            ("", "\n"),
                            ("class:warning", "Press Enter to continue..."),
                            ("", "\n"),
                        ]
                    ),
                    style=self.style,
                )
                input()  # Pause for user to read
                return False

        except ImportError as e:
            # Extract module path from error message
            error_msg = str(e)
            if "No module named" in error_msg:
                missing_module = (
                    error_msg.split("'")[1] if "'" in error_msg else "unknown"
                )
                module_path = missing_module.replace(".", "/")

                print_formatted_text(
                    FormattedText(
                        [
                            (
                                "class:error",
                                f"Module not implemented: {missing_module}",
                            ),
                            ("", "\n"),
                            ("class:warning", "This feature is not yet implemented."),
                            ("", "\n"),
                            ("class:info", "To implement this module:"),
                            ("", "\n"),
                            (
                                "class:info",
                                f'1. Create directory: matsimpy/ui/cli/interfaces/{module_path.split("/")[-1]}/',
                            ),
                            (
                                "class:info",
                                f'2. Create file: {module_path.split("/")[-1]}.py',
                            ),
                            ("class:info", f"3. Add __init__.py file in the directory"),
                            ("class:info", "4. Implement the required functions"),
                            ("", "\n"),
                            ("class:info", "Example file structure:"),
                            (
                                "class:info",
                                f'matsimpy/ui/cli/interfaces/{module_path.split("/")[-1]}/',
                            ),
                            ("class:info", f"├── __init__.py"),
                            ("class:info", f'└── {module_path.split("/")[-1]}.py'),
                            ("", "\n"),
                            ("class:info", "Example implementation:"),
                            ("class:info", "def " + function_name + "(style=None):"),
                            ("class:info", "    # Your implementation here"),
                            (
                                "class:info",
                                '    return {"status": True, "message": "Success"}',
                            ),
                            ("", "\n"),
                            ("class:warning", "Press Enter to continue..."),
                            ("", "\n"),
                        ]
                    ),
                    style=self.style,
                )
                input()  # Pause for user to read
            else:
                print_formatted_text(
                    FormattedText(
                        [
                            ("class:error", f"Failed to import module: {e}"),
                            ("", "\n"),
                            (
                                "class:warning",
                                "Make sure the interface module is installed and accessible",
                            ),
                            ("", "\n"),
                            ("class:info", "Common solutions:"),
                            ("class:info", "1. Check if the module file exists"),
                            ("class:info", "2. Verify the module path is correct"),
                            ("class:info", "3. Ensure all dependencies are installed"),
                            ("class:info", "4. Check for syntax errors in the module"),
                            ("", "\n"),
                            ("class:warning", "Press Enter to continue..."),
                            ("", "\n"),
                        ]
                    ),
                    style=self.style,
                )
                input()  # Pause for user to read
            return False
        except Exception as e:
            print_formatted_text(
                FormattedText(
                    [
                        ("class:error", f"Error executing interface: {e}"),
                        ("", "\n"),
                        (
                            "class:warning",
                            "Unexpected error occurred during execution.",
                        ),
                        ("", "\n"),
                        ("class:info", "Troubleshooting steps:"),
                        (
                            "class:info",
                            "1. Check the interface implementation for errors",
                        ),
                        (
                            "class:info",
                            "2. Verify all required dependencies are available",
                        ),
                        (
                            "class:info",
                            "3. Check the function signature and return values",
                        ),
                        (
                            "class:info",
                            "4. Review the error message for specific issues",
                        ),
                        ("", "\n"),
                        ("class:warning", "Press Enter to continue..."),
                        ("", "\n"),
                    ]
                ),
                style=self.style,
            )
            input()  # Pause for user to read
            return False
        finally:
            input("Press Enter to continue...")

    def go_back(self) -> bool:
        """Go back to previous menu level"""
        if self.current_level <= 1:
            return False

        if self.menu_history:
            self.menu_history.pop()

        if self.current_level == 2:
            self.current_level = 1
            self.current_parent = None
        elif self.current_level == 3:
            self.current_level = 2
            if self.menu_history:
                self.current_parent = self.menu_history[-1]["code"]
            else:
                self.current_parent = None

        return True

    def show_history(self):
        """Show navigation history"""
        if not self.session.navigation_history:
            print_formatted_text(
                FormattedText([("class:info", "No navigation history yet.")]),
                style=self.style,
            )
            return

        lines = []
        lines.append(("class:header", "Navigation History"))
        lines.append(("", "\n"))
        lines.append(("class:separator", "-" * 40))
        lines.append(("", "\n"))

        # Show last 10 items
        recent_history = self.session.navigation_history[-10:]
        for i, code in enumerate(reversed(recent_history), 1):
            item = self.find_menu_item(code)
            if item:
                lines.append(("class:info", f"{i:2d}. "))
                lines.append(("class:menu_code", item["code"]))
                lines.append(("class:menu_item", f' {item["name"]}'))
                lines.append(("", "\n"))

        print_formatted_text(FormattedText(lines), style=self.style)

    def show_help(self):
        """Display comprehensive help"""
        help_text = FormattedText(
            [
                ("class:header", "MatSimPy Interactive Menu - Help"),
                ("", "\n"),
                ("class:separator", "═" * 50),
                ("", "\n"),
                ("class:menu_item", "Basic Navigation:"),
                ("", "\n"),
                ("class:menu_code", "  [number]"),
                ("class:menu_item", "   - Enter menu item (e.g., 11, s11, s111)"),
                ("", "\n"),
                ("class:menu_code", "  b, back"),
                ("class:menu_item", "  - Go back to previous level"),
                ("", "\n"),
                ("class:menu_code", "  q, quit"),
                ("class:menu_item", "  - Exit program"),
                ("", "\n"),
                ("", "\n"),
                ("class:menu_item", "Advanced Features:"),
                ("", "\n"),
                ("class:menu_code", "  search <term>"),
                ("class:menu_item", "     - Search menu items"),
                ("", "\n"),
                ("class:menu_code", "  s <term>"),
                ("class:menu_item", "         - Quick search"),
                ("", "\n"),
                ("class:menu_code", "  history"),
                ("class:menu_item", "         - Show navigation history"),
                ("", "\n"),
                ("class:menu_code", "  stats"),
                ("class:menu_item", "           - Show menu statistics"),
                ("", "\n"),
                ("class:menu_code", "  impl"),
                (
                    "class:menu_item",
                    "            - Show detailed implementation status",
                ),
                ("", "\n"),
                ("class:menu_code", "  clear"),
                ("class:menu_item", "           - Clear screen"),
                ("", "\n"),
                ("class:menu_code", "  goto <code>"),
                ("class:menu_item", "     - Jump directly to any item"),
                ("", "\n"),
                ("class:menu_code", "  ! <command>"),
                ("class:menu_item", "    - Execute system command"),
                ("", "\n"),
                ("", "\n"),
                ("class:menu_item", "Interface Status Indicators:"),
                ("", "\n"),
                ("class:success", "  ✓"),
                ("class:menu_item", " - Fully implemented and ready to use"),
                ("", "\n"),
                ("class:warning", "  ⚠"),
                (
                    "class:menu_item",
                    " - Module exists but function needs implementation",
                ),
                ("", "\n"),
                ("class:error", "  ✗"),
                ("class:menu_item", " - Module not implemented yet"),
                ("", "\n"),
                ("class:error", "  ?"),
                ("class:menu_item", " - Error checking implementation status"),
                ("", "\n"),
                ("", "\n"),
                ("class:menu_item", "Smart Navigation:"),
                ("", "\n"),
                ("class:info", "  • You can jump directly to any menu level"),
                ("", "\n"),
                ("class:info", "  • Use Tab for auto-completion"),
                ("", "\n"),
                ("class:info", "  • Recently accessed items are tracked"),
                ("", "\n"),
                ("class:info", "  • Interface status is shown for Level 3 operations"),
                ("", "\n"),
                ("", "\n"),
                ("class:menu_item", "Menu Structure:"),
                ("", "\n"),
                ("class:info", "  Level 1: Main categories (11-34)"),
                ("", "\n"),
                ("class:info", "  Level 2: Sub-categories (s11, e11, etc.)"),
                ("", "\n"),
                ("class:info", "  Level 3: Specific operations (s111, e111, etc.)"),
                ("", "\n"),
                ("", "\n"),
                ("class:menu_item", "Implementation Information:"),
                ("", "\n"),
                (
                    "class:info",
                    "  • When a module is not implemented, you'll see detailed",
                ),
                ("", "\n"),
                ("class:info", "    instructions on how to implement it"),
                ("", "\n"),
                (
                    "class:info",
                    '  • Use "stats" command to see overall implementation status',
                ),
                ("", "\n"),
                (
                    "class:info",
                    "  • Check operation details for specific implementation info",
                ),
                ("", "\n"),
                ("", "\n"),
                ("class:menu_item", "System Commands:"),
                ("", "\n"),
                ("class:menu_code", "  ! ls"),
                ("class:menu_item", "           - List files"),
                ("", "\n"),
                ("class:menu_code", "  ! pwd"),
                ("class:menu_item", "          - Show current directory"),
                ("", "\n"),
                ("class:menu_code", "  ! ps"),
                ("class:menu_item", "           - Show processes"),
                ("", "\n"),
                ("class:menu_code", "  ! <any_cmd>"),
                ("class:menu_item", "    - Execute any system command"),
                ("", "\n"),
                ("class:separator", "═" * 50),
                ("", "\n"),
            ]
        )

        print_formatted_text(help_text, style=self.style)

    def show_statistics(self):
        """Show session and system statistics"""
        lines = []
        lines.append(("class:header", "System Statistics"))
        lines.append(("", "\n"))
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))

        # Session statistics
        session_time = datetime.now() - self.session.start_time
        lines.append(("class:stats", "Session Information:"))
        lines.append(("", "\n"))
        lines.append(
            (
                "class:info",
                f'  Start Time: {self.session.start_time.strftime("%Y-%m-%d %H:%M:%S")}',
            )
        )
        lines.append(("", "\n"))
        lines.append(
            (
                "class:info",
                f"  Duration: {session_time.seconds // 60}m {session_time.seconds % 60}s",
            )
        )
        lines.append(("", "\n"))
        lines.append(
            ("class:info", f"  Commands Executed: {self.session.commands_executed}")
        )
        lines.append(("", "\n"))
        lines.append(
            (
                "class:info",
                f"  Navigation History: {len(self.session.navigation_history)} items",
            )
        )
        lines.append(("", "\n"))

        # Menu statistics
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))
        lines.append(("class:stats", "Menu Structure:"))
        lines.append(("", "\n"))

        total_items = len(self.menu_data["all_items"])
        level1_count = len(self.menu_data["menu_structure"]["level1_items"])
        level2_count = sum(
            len(items)
            for items in self.menu_data["menu_structure"]["level2_items"].values()
        )
        level3_count = sum(
            len(items)
            for items in self.menu_data["menu_structure"]["level3_items"].values()
        )

        lines.append(("class:info", f"  Total Menu Items: {total_items}"))
        lines.append(("", "\n"))
        lines.append(("class:info", f"  Level 1 (Categories): {level1_count}"))
        lines.append(("", "\n"))
        lines.append(("class:info", f"  Level 2 (Sub-Categories): {level2_count}"))
        lines.append(("", "\n"))
        lines.append(("class:info", f"  Level 3 (Operations): {level3_count}"))
        lines.append(("", "\n"))

        # Interface implementation statistics
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))
        lines.append(("class:stats", "Interface Implementation Status:"))
        lines.append(("", "\n"))

        # Count interfaces by status
        status_counts = {
            "implemented": 0,
            "partial": 0,
            "not_implemented": 0,
            "error": 0,
        }
        total_interfaces = 0

        for code, item in self.menu_data["all_items"].items():
            if item["level"] == 3 and item.get("interface"):
                total_interfaces += 1
                status = self.check_interface_status(item)
                status_counts[status] = status_counts.get(status, 0) + 1

        if total_interfaces > 0:
            lines.append(("class:info", f"  Total Interfaces: {total_interfaces}"))
            lines.append(("", "\n"))
            lines.append(
                (
                    "class:success",
                    f'  ✓ Implemented: {status_counts["implemented"]} ({status_counts["implemented"]/total_interfaces*100:.1f}%)',
                )
            )
            lines.append(("", "\n"))
            lines.append(
                (
                    "class:warning",
                    f'  ⚠ Partial: {status_counts["partial"]} ({status_counts["partial"]/total_interfaces*100:.1f}%)',
                )
            )
            lines.append(("", "\n"))
            lines.append(
                (
                    "class:error",
                    f'  ✗ Not Implemented: {status_counts["not_implemented"]} ({status_counts["not_implemented"]/total_interfaces*100:.1f}%)',
                )
            )
            lines.append(("", "\n"))
            if status_counts["error"] > 0:
                lines.append(
                    (
                        "class:error",
                        f'  ? Error: {status_counts["error"]} ({status_counts["error"]/total_interfaces*100:.1f}%)',
                    )
                )
                lines.append(("", "\n"))
        else:
            lines.append(
                ("class:warning", "  No interfaces found in menu configuration")
            )
            lines.append(("", "\n"))

        # Most accessed items
        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))
        lines.append(("class:stats", "Most Accessed Items:"))
        lines.append(("", "\n"))

        if self.session.last_accessed:
            sorted_access = sorted(
                self.session.last_accessed.items(), key=lambda x: x[1], reverse=True
            )[:5]
            for code, access_time in sorted_access:
                item = self.find_menu_item(code)
                if item:
                    lines.append(
                        (
                            "class:info",
                            f'  {item["name"]} ({code}) - {access_time.strftime("%H:%M:%S")}',
                        )
                    )
                    lines.append(("", "\n"))
        else:
            lines.append(("class:info", "  No items accessed yet"))
            lines.append(("", "\n"))

        lines.append(("class:separator", "-" * 50))
        lines.append(("", "\n"))

        print_formatted_text(FormattedText(lines), style=self.style)

    def check_interface_status(self, item: Dict) -> str:
        """Check if an interface is implemented and return status"""
        interface_path = item.get("interface", "")
        if not interface_path:
            return "not_implemented"

        try:
            module_name = interface_path.split(":")[0]
            function_name = interface_path.split(":")[1]

            import importlib

            module = importlib.import_module(module_name)

            if hasattr(module, function_name):
                return "implemented"
            else:
                return "partial"
        except ImportError:
            return "not_implemented"
        except Exception:
            return "error"

    def get_interface_status_icon(self, status: str) -> str:
        """Get status icon for interface implementation"""
        status_icons = {
            "implemented": "✓",
            "partial": "⚠",
            "not_implemented": "✗",
            "error": "?",
        }
        return status_icons.get(status, "?")

    def get_interface_status_color(self, status: str) -> str:
        """Get status color for interface implementation"""
        status_colors = {
            "implemented": "success",
            "partial": "warning",
            "not_implemented": "error",
            "error": "error",
        }
        return status_colors.get(status, "error")

    def process_command(self, user_input: str) -> bool:
        """Process user command and return True to continue, False to exit"""
        parts = user_input.strip().split()
        if not parts:
            return True

        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Update command count
        self.session.commands_executed += 1

        # Handle system commands
        if command.startswith("!"):
            if len(command) > 1:
                # Command is like !ls
                sys_command = command[1:] + (" " + " ".join(args) if args else "")
            elif args:
                # Command is like ! ls
                sys_command = " ".join(args)
            else:
                print_formatted_text(
                    FormattedText(
                        [("class:warning", "Usage: ! <command> or !<command>")]
                    ),
                    style=self.style,
                )
                input("Press Enter to continue...")
                return True

            self.execute_system_command(sys_command)
            input("Press Enter to continue...")
            clear()  # Clear screen after continuing
            return True

        # Handle regular commands
        if command in ["q", "quit", "exit"]:
            return False

        elif command in ["b", "back"]:
            if not self.go_back():
                print_formatted_text(
                    FormattedText([("class:error", "Already at main menu level")]),
                    style=self.style,
                )
                input("Press Enter to continue...")
                clear()  # Clear screen after continuing

        elif command in ["h", "help"]:
            self.show_help()
            input("Press Enter to continue...")
            clear()  # Clear screen after continuing

        elif command in ["s", "search", "find"]:
            if args:
                query = " ".join(args)
                results = self.search_menu(query)
                self.display_search_results(query, results)
                self.search_results = results
            else:
                query = prompt("Enter search term: ", style=self.style).strip()
                if query:
                    results = self.search_menu(query)
                    self.display_search_results(query, results)
                    self.search_results = results
            input("Press Enter to continue...")
            clear()  # Clear screen after continuing

        elif command == "history":
            self.show_history()
            input("Press Enter to continue...")
            clear()  # Clear screen after continuing

        elif command == "stats":
            self.show_statistics()
            input("Press Enter to continue...")
            clear()  # Clear screen after continuing

        elif command in ["impl", "implementation", "status"]:
            self.show_implementation_status()
            return True

        elif command in ["goto", "go"]:
            if args:
                code = args[0]
                if not self.navigate_to_item(code):
                    print_formatted_text(
                        FormattedText([("class:error", f"Cannot navigate to: {code}")]),
                        style=self.style,
                    )
                    input("Press Enter to continue...")
                else:
                    self.session.navigation_history.append(f"[{code}]")
            else:
                print_formatted_text(
                    FormattedText(
                        [("class:warning", "Usage: goto <code> (e.g., goto s111)")]
                    ),
                    style=self.style,
                )
                input("Press Enter to continue...")

        else:
            # Try to navigate to menu item
            if not self.navigate_to_item(command):
                print_formatted_text(
                    FormattedText(
                        [
                            ("class:error", f"Invalid command or menu code: {command}"),
                            ("", "\n"),
                            (
                                "class:info",
                                'Type "h" for help or use Tab for completion',
                            ),
                        ]
                    ),
                    style=self.style,
                )
                input("Press Enter to continue...")
            else:
                # Add to navigation history
                item = self.find_menu_item(command)
                if item:
                    self.session.navigation_history.append(item["code"])

        return True

    def display_current_menu(self):
        """Display current menu with colored formatting"""
        clear()

        # Use different formatting for main menu vs others
        if self.current_level == 1 and not self.menu_history:
            # Main menu with grouped display
            menu_display = self.format_grouped_main_menu()
            print_formatted_text(menu_display, style=self.style)
        else:
            # Standard menu display
            header = self.format_standard_header()
            print_formatted_text(header, style=self.style)

            # Display menu items
            items = self.get_current_menu_items()
            menu_items = self.format_menu_items(items)
            print_formatted_text(menu_items, style=self.style)

        # Display footer
        footer = self.format_footer()
        print_formatted_text(footer, style=self.style)

    def run(self):
        """Main menu loop with enhanced features"""
        if not self.menu_data:
            print("Error: No menu data loaded")
            return

        if not self.validate_code_uniqueness():
            print("Error: Menu contains duplicate codes")
            return

        while True:
            try:
                # Display current menu
                self.display_current_menu()

                # Get user input with completion
                completer = self.get_command_completer()
                user_input = prompt(
                    FormattedText([("class:prompt", "MatSimPy> ")]),
                    style=self.style,
                    completer=completer,
                    key_bindings=self.key_bindings,
                ).strip()

                # Process command
                if not self.process_command(user_input):
                    break

            except KeyboardInterrupt:
                print_formatted_text(
                    FormattedText(
                        [
                            ("", "\n"),
                            ("class:success", " Thank you for using MatSimPy!"),
                        ]
                    ),
                    style=self.style,
                )
                break
            except EOFError:
                break

        # Session summary
        session_time = datetime.now() - self.session.start_time
        summary = FormattedText(
            [
                ("", "\n"),
                ("class:header", "Session Summary:"),
                ("", "\n"),
                (
                    "class:info",
                    f"Duration: {session_time.seconds // 60}m {session_time.seconds % 60}s",
                ),
                ("", "\n"),
                ("class:info", f"Commands executed: {self.session.commands_executed}"),
                ("", "\n"),
                ("class:info", f"Items accessed: {len(self.session.last_accessed)}"),
                ("", "\n"),
                ("class:success", "Goodbye!"),
                ("", "\n"),
            ]
        )
        print_formatted_text(summary, style=self.style)

    def _paginate_output(self, formatted_lines: List[Tuple], page_size: int = 20):
        """Display output with pagination support (less/more style)"""
        import os

        # Get terminal height, default to 24 if unavailable
        try:
            terminal_height = os.get_terminal_size().lines
            # Reserve 4 lines for header/footer
            page_size = min(page_size, terminal_height - 4)
        except:
            page_size = 20

        # Count approximate lines (each formatted line item counts as 1, plus newlines in text)
        total_items = len(formatted_lines)
        # Simple chunking: divide items into pages
        items_per_page = max(
            1, page_size // 2
        )  # Rough estimate: 2 items per screen line
        total_pages = (
            (total_items + items_per_page - 1) // items_per_page
            if total_items > 0
            else 1
        )
        current_page = 0

        while current_page < total_pages:
            # Clear screen
            clear()

            # Display current page
            start_idx = current_page * items_per_page
            end_idx = min(start_idx + items_per_page, total_items)
            page_lines = formatted_lines[start_idx:end_idx]

            print_formatted_text(FormattedText(page_lines), style=self.style)

            # Show pagination info
            print_formatted_text(
                FormattedText(
                    [
                        ("class:separator", "-" * 70),
                        ("", "\n"),
                        (
                            "class:info",
                            f"Page {current_page + 1}/{total_pages} (showing items {start_idx + 1}-{end_idx} of {total_items})",
                        ),
                        ("", "\n"),
                        (
                            "class:info",
                            "Commands: [Space/Enter/n] Next | [b/p] Previous | [q] Quit | [g<num>] Go to page | [h] Help",
                        ),
                        ("", "\n"),
                    ]
                ),
                style=self.style,
            )

            # Get user input
            user_input = prompt("> ", style=self.style).strip().lower()

            if user_input in ["q", "quit", "exit"]:
                break
            elif user_input in ["b", "back", "p", "prev", "previous"]:
                if current_page > 0:
                    current_page -= 1
            elif user_input in ["", " ", "n", "next"]:
                if current_page < total_pages - 1:
                    current_page += 1
            elif user_input.startswith("g") or (
                user_input.isdigit() and len(user_input) <= 3
            ):
                # Go to specific page
                try:
                    if user_input.startswith("g"):
                        page_num = int(user_input[1:].strip()) - 1
                    else:
                        page_num = int(user_input) - 1
                    if 0 <= page_num < total_pages:
                        current_page = page_num
                except ValueError:
                    pass
            elif user_input == "h" or user_input == "help":
                print_formatted_text(
                    FormattedText(
                        [
                            ("class:info", "\nNavigation Help:"),
                            ("class:info", "  Space/Enter/n - Next page"),
                            ("class:info", "  b/p - Previous page"),
                            ("class:info", "  g<num> or <num> - Go to page number"),
                            ("class:info", "  q - Quit"),
                            ("", "\n"),
                        ]
                    ),
                    style=self.style,
                )
                input("Press Enter to continue...")

        clear()

    def show_implementation_status(self):
        """Show detailed implementation status for all interfaces with pagination"""
        lines = []
        lines.append(("class:header", "Detailed Implementation Status"))
        lines.append(("", "\n"))
        lines.append(("class:separator", "-" * 70))
        lines.append(("", "\n"))

        # Group by status
        status_groups = {
            "implemented": [],
            "partial": [],
            "not_implemented": [],
            "error": [],
        }

        total_interfaces = 0

        for code, item in self.menu_data["all_items"].items():
            if item["level"] == 3 and item.get("interface"):
                total_interfaces += 1
                status = self.check_interface_status(item)
                status_groups[status].append(item)

        # Show summary
        lines.append(("class:stats", f"Total Interfaces: {total_interfaces}"))
        lines.append(("", "\n"))
        lines.append(
            ("class:success", f'✓ Implemented: {len(status_groups["implemented"])}')
        )
        lines.append(("", "\n"))
        lines.append(("class:warning", f'⚠ Partial: {len(status_groups["partial"])}'))
        lines.append(("", "\n"))
        lines.append(
            (
                "class:error",
                f'✗ Not Implemented: {len(status_groups["not_implemented"])}',
            )
        )
        lines.append(("", "\n"))
        if status_groups["error"]:
            lines.append(("class:error", f'? Error: {len(status_groups["error"])}'))
            lines.append(("", "\n"))

        lines.append(("class:separator", "-" * 70))
        lines.append(("", "\n"))

        # Show detailed breakdown
        for status, items in status_groups.items():
            if items:
                status_names = {
                    "implemented": "✓ Fully Implemented",
                    "partial": "⚠ Partially Implemented",
                    "not_implemented": "✗ Not Implemented",
                    "error": "? Error Status",
                }
                status_colors = {
                    "implemented": "success",
                    "partial": "warning",
                    "not_implemented": "error",
                    "error": "error",
                }

                lines.append(
                    (
                        f"class:{status_colors[status]}",
                        f"{status_names[status]} ({len(items)} items):",
                    )
                )
                lines.append(("", "\n"))

                # Sort items by name
                items.sort(key=lambda x: x["name"])

                for item in items:
                    # Show path with color based on status
                    path_parts = []
                    if item.get("parent"):
                        parent_item = self.find_menu_item(item["parent"])
                        if parent_item and parent_item.get("parent"):
                            grandparent_item = self.find_menu_item(
                                parent_item["parent"]
                            )
                            if grandparent_item:
                                path_parts = [
                                    grandparent_item["name"],
                                    parent_item["name"],
                                    item["name"],
                                ]

                    # Use different colors for different statuses
                    status_color_class = status_colors[status]

                    if path_parts:
                        path_str = " → ".join(path_parts)
                        lines.append(
                            (
                                f"class:{status_color_class}",
                                f'  {item["code"]} {path_str}',
                            )
                        )
                    else:
                        lines.append(
                            (
                                f"class:{status_color_class}",
                                f'  {item["code"]} {item["name"]}',
                            )
                        )

                    # Show interface path with appropriate color
                    if item.get("interface"):
                        lines.append(
                            (
                                f"class:{status_color_class}",
                                f'    Interface: {item["interface"]}',
                            )
                        )

                    lines.append(("", "\n"))

                lines.append(("", "\n"))

        lines.append(("class:separator", "-" * 70))
        lines.append(("", "\n"))

        # Use pagination if output is long
        if len(lines) > 30:
            self._paginate_output(lines, page_size=20)
            # Pagination already handles clearing, so no need to clear again
        else:
            # Short output, just display normally
            print_formatted_text(FormattedText(lines), style=self.style)
            input("Press Enter to continue...")
            clear()  # Clear screen after continuing


def main():
    """Main function"""
    json_file = "matsimpy_menu.json"
    if len(sys.argv) > 1:
        json_file = sys.argv[1]

    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' not found.")
        print("Please run the menu parser first to generate the JSON file.")
        return

    menu = AdvancedInteractiveMenu(json_file)
    menu.run()


if __name__ == "__main__":
    main()
