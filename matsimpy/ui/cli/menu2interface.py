#!/usr/bin/env python3
"""
Enhanced MatSimPy Menu Parser v2
Parse and format the hierarchical menu system with automatic interface generation
Automatically generates organized interface paths based on menu structure
"""

import re
import json
import importlib
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class MenuItem:
    """Represents a single menu item"""
    code: str
    name: str
    level: int
    parent: str = None
    interface: str = ""  


class EnhancedMenuParser:
    """Enhanced parser for MatSimPy menu system with automatic interface generation"""
    
    def __init__(self):
        self.menu_items: Dict[str, MenuItem] = {}
        self.level1_items: List[MenuItem] = []
        self.level2_items: Dict[str, List[MenuItem]] = {}
        self.level3_items: Dict[str, List[MenuItem]] = {}
        self.interface_cache: Dict[str, Any] = {}
        
        # Level 1 category names mapping
        self.level1_name_map = {}

    def parse_menu_file(self, filename: str) -> bool:
        """Parse menu from file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._parse_level2_sections(content)
            self._parse_level3_sections(content)
            self._build_level1_items()
            self._assign_automatic_interfaces()
            
            return True
            
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            return False
        except Exception as e:
            print(f"Error reading file: {e}")
            return False

    def _parse_level2_sections(self, content: str):
        """Parse Level 2 menu sections"""
        # Pattern: #### [XX] Name followed by list items
        pattern = r'#### \[(\d+)\] ([^#\n]+)\n((?:- \[[a-z]\d+\][^\n]+\n?)+)'
        matches = re.findall(pattern, content)
        
        for level1_code, level1_name, items_text in matches:
            level1_key = f"[{level1_code}]"
            
            # Create Level 1 item
            level1_item = MenuItem(
                code=level1_key,
                name=level1_name.strip(),
                level=1,
                interface=""  # Level 1 has no interface
            )
            self.menu_items[level1_key] = level1_item
            
            # Parse Level 2 items
            item_pattern = r'- \[([a-z]\d+)\] ([^\n]+)'
            item_matches = re.findall(item_pattern, items_text)
            
            level2_list = []
            for item_code, item_name in item_matches:
                item_key = f"[{item_code}]"
                item = MenuItem(
                    code=item_key,
                    name=item_name.strip(),
                    level=2,
                    parent=level1_key,
                    interface=""  # Level 2 has no interface
                )
                self.menu_items[item_key] = item
                level2_list.append(item)
            
            self.level2_items[level1_key] = level2_list

    def _parse_level3_sections(self, content: str):
        """Parse Level 3 menu sections"""
        # Pattern: #### [abc] Name followed by list items
        pattern = r'#### \[([a-z]\d+)\] ([^#\n]+)\n((?:- \[[a-z]\d+\][^\n]+\n?)+)'
        matches = re.findall(pattern, content)
        
        for level2_code, level2_name, items_text in matches:
            level2_key = f"[{level2_code}]"
            
            # Parse Level 3 items
            item_pattern = r'- \[([a-z]\d+)\] ([^\n]+)'
            item_matches = re.findall(item_pattern, items_text)
            
            level3_list = []
            for item_code, item_name in item_matches:
                item_key = f"[{item_code}]"
                item = MenuItem(
                    code=item_key,
                    name=item_name.strip(),
                    level=3,
                    parent=level2_key,
                    interface=""  # Will be assigned automatically
                )
                self.menu_items[item_key] = item
                level3_list.append(item)
            
            self.level3_items[level2_key] = level3_list

    def _normalize_name_for_interface(self, name: str) -> str:
        """Convert menu item name to a valid interface module name"""
        # Remove special characters and convert to lowercase
        normalized = re.sub(r'[^\w\s-]', '', name.lower())
        # Replace spaces and hyphens with underscores
        normalized = re.sub(r'[\s-]+', '_', normalized)
        # Remove multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        # Handle common abbreviations and special cases
        replacements = {
            'dos': 'density_of_states',
            'vasp': 'vasp',
            'qe': 'quantum_espresso',
            'ai': 'artificial_intelligence',
            'ml': 'machine_learning',
            'dft': 'density_functional_theory',
            'ir': 'infrared',
            'uv': 'ultraviolet',
            'xyz': 'xyz_format',
            'cif': 'cif_format',
            'poscar': 'poscar_format',
            'pdb': 'pdb_format',
            '3d': 'three_dimensional',
            '2d': 'two_dimensional'
        }
        
        for abbrev, full_name in replacements.items():
            if normalized == abbrev:
                normalized = full_name
                break
        
        return normalized

    def _get_level1_category_from_level3(self, level3_item: MenuItem) -> str:
        """Get Level 1 category code from a Level 3 item"""
        # Traverse up to find Level 1 parent
        level2_code = level3_item.parent
        if level2_code and level2_code in self.menu_items:
            level2_item = self.menu_items[level2_code]
            level1_code = level2_item.parent
            if level1_code and level1_code in self.menu_items:
                # Extract numeric part from [XX] format
                return level1_code[1:-1]
        return "unknown"

    def _assign_automatic_interfaces(self):
        """Automatically assign interface paths to Level 3 items based on hierarchy"""
        for item in self.menu_items.values():
            if item.level == 3:
                # Get parent items
                level2_item = self.menu_items.get(item.parent)
                if not level2_item:
                    continue
                    
                level1_item = self.menu_items.get(level2_item.parent)
                if not level1_item:
                    continue
                
                # Normalize Level 1 and Level 2 names for directory/module names
                level1_normalized = self._normalize_name_for_interface(level1_item.name)
                level2_normalized = self._normalize_name_for_interface(level2_item.name)
                
                # Normalize Level 3 name for function name
                level3_normalized = self._normalize_name_for_interface(item.name)
                
                # Construct interface path: matsimpy.ui.cli.interfaces.l1_item.l2_item:l3_function
                interface_path = f"matsimpy.ui.cli.interfaces.{level1_normalized}.{level2_normalized}:{level3_normalized}"
                
                # Clean up any invalid characters
                interface_path = re.sub(r'[^\w\.:]', '_', interface_path)
                
                item.interface = interface_path

    def _build_level1_items(self):
        """Build sorted list of Level 1 items"""
        level1_codes = []
        for item in self.menu_items.values():
            if item.level == 1:
                level1_codes.append(item.code)
        
        # Sort by numeric code
        level1_codes.sort(key=lambda x: int(x[1:-1]))
        
        for code in level1_codes:
            self.level1_items.append(self.menu_items[code])

    def load_interface(self, interface_path: str) -> Optional[Any]:
        """Dynamically load program interface"""
        if not interface_path:
            return None
            
        # Check cache
        if interface_path in self.interface_cache:
            return self.interface_cache[interface_path]
        
        try:
            # Parse module path and function name
            if ':' in interface_path:
                module_path, function_name = interface_path.split(':')
            else:
                module_path = interface_path
                function_name = 'main'  # Default function name
            
            # Dynamically import module
            module = importlib.import_module(module_path)
            
            # Get the specific function
            if hasattr(module, function_name):
                interface_obj = getattr(module, function_name)
            else:
                # Fallback to common function names
                interface_obj = None
                for attr_name in ['execute', 'run', 'main']:
                    if hasattr(module, attr_name):
                        interface_obj = getattr(module, attr_name)
                        break
                
                if interface_obj is None:
                    # If no standard function found, return module itself
                    interface_obj = module
            
            # Cache interface
            self.interface_cache[interface_path] = interface_obj
            return interface_obj
            
        except ImportError as e:
            print(f"Error importing interface '{interface_path}': {e}")
            return None
        except Exception as e:
            print(f"Error loading interface '{interface_path}': {e}")
            return None

    def execute_operation(self, code: str, *args, **kwargs) -> bool:
        """Execute Level 3 operation"""
        # Find menu item
        if not code.startswith('[') or not code.endswith(']'):
            code = f"[{code}]"
        
        item = self.menu_items.get(code)
        if not item or item.level != 3:
            print(f"Invalid Level 3 operation code: {code}")
            return False
        
        # Load interface
        interface = self.load_interface(item.interface)
        if interface is None:
            print(f"No interface available for operation: {item.name}")
            return False
        
        try:
            print(f"Executing: {item.name}")
            print(f"Interface: {item.interface}")
            
            # Try different execution methods
            if callable(interface):
                result = interface(*args, **kwargs)
            elif hasattr(interface, 'execute'):
                result = interface.execute(*args, **kwargs)
            elif hasattr(interface, 'run'):
                result = interface.run(*args, **kwargs)
            elif hasattr(interface, 'main'):
                result = interface.main(*args, **kwargs)
            else:
                print(f"No executable method found in interface: {item.interface}")
                return False
            
            print(f"Operation completed successfully")
            return True
            
        except Exception as e:
            print(f"Error executing operation '{item.name}': {e}")
            return False

    def get_operation_info(self, code: str) -> Optional[Dict]:
        """Get operation information"""
        if not code.startswith('[') or not code.endswith(']'):
            code = f"[{code}]"
        
        item = self.menu_items.get(code)
        if not item or item.level != 3:
            return None
        
        return {
            'code': item.code,
            'name': item.name,
            'level': item.level,
            'parent': item.parent,
            'interface': item.interface,
            'interface_loaded': item.interface in self.interface_cache,
            'interface_available': self.load_interface(item.interface) is not None
        }

    def list_operations_by_category(self, level1_code: str) -> List[Dict]:
        """List all operations by category"""
        if not level1_code.startswith('['):
            level1_code = f"[{level1_code}]"
        
        operations = []
        level2_items = self.level2_items.get(level1_code, [])
        
        for level2_item in level2_items:
            level3_items = self.level3_items.get(level2_item.code, [])
            for level3_item in level3_items:
                operations.append({
                    'code': level3_item.code,
                    'name': level3_item.name,
                    'parent': level3_item.parent,
                    'interface': level3_item.interface,
                    'category': level2_item.name
                })
        
        return operations

    def get_interface_directory_structure(self) -> Dict:
        """Generate the recommended interface directory structure"""
        structure = {}
        
        for item in self.menu_items.values():
            if item.level == 3 and item.interface:
                # Parse interface path: matsimpy.ui.cli.interfaces.l1_item.l2_item:l3_function
                if ':' in item.interface:
                    module_path, function_name = item.interface.split(':')
                    parts = module_path.split('.')
                    
                    if len(parts) >= 6:  # matsimpy.ui.cli.interfaces.l1_item.l2_item
                        l1_item = parts[4]  # Level 1 directory
                        l2_item = parts[5]  # Level 2 module
                        
                        if l1_item not in structure:
                            structure[l1_item] = {}
                        if l2_item not in structure[l1_item]:
                            structure[l1_item][l2_item] = []
                        
                        structure[l1_item][l2_item].append({
                            'code': item.code,
                            'name': item.name,
                            'interface': item.interface
                        })
        
        return structure

    def format_interface_structure(self) -> str:
        """Format the interface directory structure for display"""
        structure = self.get_interface_directory_structure()
        
        lines = []
        lines.append("=" * 80)
        lines.append("Recommended Interface Directory Structure")
        lines.append("matsimpy/ui/cli/interfaces/l1_item/l2_item.py")
        lines.append("Level 1 = Directories, Level 2 = Modules, Level 3 = Functions")
        lines.append("=" * 80)
        lines.append("matsimpy/ui/cli/interfaces/")
        
        for l1_item, l2_modules in sorted(structure.items()):
            lines.append(f"├── {l1_item}/")
            module_items = list(l2_modules.items())
            
            for i, (l2_module, functions) in enumerate(module_items):
                is_last_module = i == len(module_items) - 1
                module_prefix = "└──" if is_last_module else "├──"
                lines.append(f"│   {module_prefix} {l2_module}.py")
                
                # Show functions in the module
                for j, func_info in enumerate(functions[:3]):  # Show first 3 functions
                    is_last_func = j == len(functions[:3]) - 1 and len(functions) <= 3
                    func_prefix = "└──" if is_last_func else "├──"
                    
                    if is_last_module:
                        func_line_prefix = "    "
                    else:
                        func_line_prefix = "│   "
                    
                    # Extract function name from interface path
                    function_name = func_info['interface'].split(':')[1] if ':' in func_info['interface'] else 'main'
                    lines.append(f"│   {func_line_prefix}       def {function_name}():  # {func_info['name']} ({func_info['code']})")
                
                # Show count if there are more functions
                if len(functions) > 3:
                    if is_last_module:
                        func_line_prefix = "    "
                    else:
                        func_line_prefix = "│   "
                    lines.append(f"│   {func_line_prefix}       ... and {len(functions) - 3} more functions")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("Summary:")
        
        # Count directories, modules and functions
        total_directories = len(structure)
        total_modules = sum(len(l2_modules) for l2_modules in structure.values())
        total_functions = sum(
            len(functions) for l2_modules in structure.values() 
            for functions in l2_modules.values()
        )
        
        lines.append(f"Total Directories (Level 1): {total_directories}")
        lines.append(f"Total Modules (Level 2): {total_modules}")
        lines.append(f"Total Functions (Level 3): {total_functions}")
        lines.append("=" * 80)
        
        return "\n".join(lines)

    def format_complete_menu(self) -> str:
        """Format complete menu structure with interface info"""
        lines = []
        lines.append("=" * 80)
        lines.append("MatSimPy v2.0 - Complete Menu Structure with Auto-Generated Interfaces")
        lines.append("Interface Format: matsimpy.ui.cli.interfaces.l1_item.l2_item:l3_function")
        lines.append("=" * 80)
        
        # Statistics
        level2_count = sum(len(items) for items in self.level2_items.values())
        level3_count = sum(len(items) for items in self.level3_items.values())
        interfaces_count = sum(1 for item in self.menu_items.values() 
                             if item.level == 3 and item.interface)
        
        lines.append(f"Total Structure: {len(self.level1_items)} Level 1, {level2_count} Level 2, {level3_count} Level 3")
        lines.append(f"Auto-Generated Interfaces: {interfaces_count} operations with interfaces")
        lines.append(f"Grand Total: {len(self.menu_items)} menu items")
        lines.append("")
        
        # Complete menu display
        for level1_item in self.level1_items:
            lines.append(f"[LEVEL 1] {level1_item.code} {level1_item.name}")
            lines.append("-" * 60)
            
            # Level 2 items for this parent
            level2_items = self.level2_items.get(level1_item.code, [])
            for level2_item in level2_items:
                lines.append(f"  [LEVEL 2] {level2_item.code} {level2_item.name}")
                
                # Level 3 items for this parent
                level3_items = self.level3_items.get(level2_item.code, [])
                if level3_items:
                    for level3_item in level3_items:
                        interface_info = f" -> {level3_item.interface}" if level3_item.interface else " -> No Interface"
                        lines.append(f"    [LEVEL 3] {level3_item.code} {level3_item.name}{interface_info}")
                else:
                    lines.append("    (No Level 3 operations)")
                lines.append("")
            
            if not level2_items:
                lines.append("  (No Level 2 sub-categories)")
            
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("End of Complete Menu Structure")
        lines.append("=" * 80)
        
        return "\n".join(lines)

    def format_statistics(self) -> str:
        """Format detailed menu statistics with interface info"""
        level2_count = sum(len(items) for items in self.level2_items.values())
        level3_count = sum(len(items) for items in self.level3_items.values())
        interfaces_count = sum(1 for item in self.menu_items.values() 
                             if item.level == 3 and item.interface)
        
        lines = []
        lines.append("=" * 60)
        lines.append("Detailed Menu Statistics with Auto-Generated Interfaces")
        lines.append("Structure: l1_item/l2_item.py with l3_functions")
        lines.append("=" * 60)
        lines.append(f"Level 1 (Main Categories): {len(self.level1_items)}")
        lines.append(f"Level 2 (Sub-Categories): {level2_count}")
        lines.append(f"Level 3 (Operations): {level3_count}")
        lines.append(f"Auto-Generated Interfaces: {interfaces_count}")
        lines.append(f"Total Menu Items: {len(self.menu_items)}")
        lines.append("")
        
        # Interface coverage by category
        lines.append("Interface Coverage by Category:")
        lines.append("-" * 40)
        
        categories = {
            "Structure & Generation": (11, 14),
            "Properties & Analysis": (15, 25), 
            "Computational Tools": (26, 29),
            "Database & Tools": (31, 34)
        }
        
        for cat_name, (start, end) in categories.items():
            cat_items = [item for item in self.level1_items 
                        if start <= int(item.code[1:-1]) <= end]
            
            # Count operations with interfaces in this category
            cat_operations = 0
            cat_interfaces = 0
            for item in cat_items:
                l2_items = self.level2_items.get(item.code, [])
                for l2_item in l2_items:
                    l3_items = self.level3_items.get(l2_item.code, [])
                    cat_operations += len(l3_items)
                    cat_interfaces += sum(1 for l3 in l3_items if l3.interface)
            
            coverage = f"{cat_interfaces}/{cat_operations}" if cat_operations > 0 else "0/0"
            percentage = f"({cat_interfaces/cat_operations*100:.1f}%)" if cat_operations > 0 else "(0%)"
            lines.append(f"  {cat_name}: {coverage} {percentage}")
        
        lines.append("=" * 60)
        return "\n".join(lines)

    def export_to_json(self, filename: str) -> bool:
        """Export complete menu structure to JSON with auto-generated interfaces"""
        try:
            # Prepare data structure
            data = {
                "metadata": {
                    "title": "MatSimPy v2.0 Menu Structure with Auto-Generated Interfaces",
                    "total_items": len(self.menu_items),
                    "level1_count": len(self.level1_items),
                    "level2_count": sum(len(items) for items in self.level2_items.values()),
                    "level3_count": sum(len(items) for items in self.level3_items.values()),
                    "interfaces_count": sum(1 for item in self.menu_items.values() 
                                          if item.level == 3 and item.interface),
                    "auto_generated": True
                },
                "menu_structure": {
                    "level1_items": [asdict(item) for item in self.level1_items],
                    "level2_items": {
                        parent: [asdict(item) for item in items] 
                        for parent, items in self.level2_items.items()
                    },
                    "level3_items": {
                        parent: [asdict(item) for item in items] 
                        for parent, items in self.level3_items.items()
                    }
                },
                "all_items": {
                    code: asdict(item) for code, item in self.menu_items.items()
                },
                "hierarchy": self._build_hierarchy_tree(),
                "interfaces": {
                    item.code: item.interface 
                    for item in self.menu_items.values() 
                    if item.level == 3 and item.interface
                },
                "interface_structure": self.get_interface_directory_structure()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False

    def _build_hierarchy_tree(self) -> Dict:
        """Build hierarchical tree structure with interface info"""
        tree = {}
        
        for level1_item in self.level1_items:
            level1_data = {
                "code": level1_item.code,
                "name": level1_item.name,
                "level2_items": {}
            }
            
            level2_items = self.level2_items.get(level1_item.code, [])
            for level2_item in level2_items:
                level2_data = {
                    "code": level2_item.code,
                    "name": level2_item.name,
                    "level3_items": []
                }
                
                level3_items = self.level3_items.get(level2_item.code, [])
                for level3_item in level3_items:
                    level3_data = {
                        "code": level3_item.code,
                        "name": level3_item.name,
                        "interface": level3_item.interface
                    }
                    level2_data["level3_items"].append(level3_data)
                
                level1_data["level2_items"][level2_item.code] = level2_data
            
            tree[level1_item.code] = level1_data
        
        return tree

    def search_menu(self, query: str) -> List[MenuItem]:
        """Search menu items"""
        results = []
        query_lower = query.lower()
        
        for item in self.menu_items.values():
            if (query_lower in item.name.lower() or 
                query_lower in item.code.lower() or
                (item.interface and query_lower in item.interface.lower())):
                results.append(item)
        
        return results

    def format_search_results(self, query: str) -> str:
        """Format search results with interface info"""
        results = self.search_menu(query)
        
        lines = []
        lines.append(f"Search results for '{query}':")
        lines.append("-" * 50)
        
        if not results:
            lines.append("No results found.")
            return "\n".join(lines)
        
        # Group by level
        by_level = {1: [], 2: [], 3: []}
        for item in results:
            by_level[item.level].append(item)
        
        for level in [1, 2, 3]:
            items = by_level[level]
            if items:
                level_names = {1: "Main Categories", 2: "Sub-Categories", 3: "Operations"}
                lines.append(f"\n{level_names[level]} (Level {level}): {len(items)} items")
                lines.append("-" * 30)
                
                for item in items:
                    parent_info = f" -> {item.parent}" if item.parent else ""
                    interface_info = f" | Interface: {item.interface}" if item.interface else ""
                    lines.append(f"  {item.code} {item.name}{parent_info}{interface_info}")
        
        lines.append(f"\nTotal results: {len(results)}")
        lines.append("-" * 50)
        return "\n".join(lines)


def main():
    """Main function"""
    parser = EnhancedMenuParser()
    
    # Parse menu file
    filename = "menu.md"
    print(f"Parsing menu from {filename}...")
    
    if not parser.parse_menu_file(filename):
        return
    
    print("Menu parsed successfully with auto-generated interfaces!")
    print()
    
    # Display complete statistics
    print(parser.format_statistics())
    print()
    
    # Display interface directory structure
    print(parser.format_interface_structure())
    print()
    
    # Export to JSON
    json_filename = "matsimpy_menu.json"
    print(f"Exporting to JSON file: {json_filename}")
    
    if parser.export_to_json(json_filename):
        print(f"Successfully exported menu structure to {json_filename}")
        
        # Show JSON file info
        import os
        if os.path.exists(json_filename):
            size = os.path.getsize(json_filename)
            print(f"JSON file size: {size:,} bytes")
    else:
        print("Failed to export JSON file")
    
    # Demonstrate interface functionality
    print("\n" + "="*60)
    print("Auto-Generated Interface Demonstration:")
    print("="*60)
    
    # Show some operations with their auto-generated interface info
    demo_codes = ["s111", "e111", "m111", "v111"]
    for code in demo_codes:
        info = parser.get_operation_info(code)
        if info:
            print(f"\nOperation: {info['name']}")
            print(f"Code: {info['code']}")
            print(f"Auto-Generated Interface: {info['interface']}")
            
            # Parse and show the structure
            if ':' in info['interface']:
                module_path, function_name = info['interface'].split(':')
                print(f"Module Path: {module_path}")
                print(f"Function Name: {function_name}")
    
    # Show some search examples
    print("\n" + "="*60)
    print("Search Examples:")
    print("="*60)
    
    search_terms = ["structure", "vasp", "analysis"]
    for term in search_terms:
        print(f"\n{parser.format_search_results(term)}")


if __name__ == "__main__":
    main()
