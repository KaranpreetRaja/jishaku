import ast
from typing import Dict, List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ClassInfo:
    def __init__(self, name: str, start_line: int, end_line: int):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.methods: Dict[str, Tuple[int, int]] = {}  # method_name -> (start_line, end_line)
        self.conditions = 0
        self.covered_conditions = 0

    def add_method(self, name: str, start_line: int, end_line: int):
        self.methods[name] = (start_line, end_line)

class ConditionCoverageAnalyzer:
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.conditions: Dict[int, ast.AST] = {}  # line_no -> condition_node
        self.covered_conditions: Set[int] = set()
        self.classes: Dict[str, ClassInfo] = {}

    def _get_node_lines(self, node: ast.AST) -> Tuple[int, int]:
        """Get the start and end line numbers for a node."""
        start_line = getattr(node, 'lineno', 0)
        end_line = getattr(node, 'end_lineno', start_line)
        return start_line, end_line

    def find_conditions(self):
        """Find all conditions in the code."""
        class ConditionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.conditions: Dict[int, ast.AST] = {}
                self.current_class: Optional[ClassInfo] = None
                self.classes: Dict[str, ClassInfo] = {}

            def visit_ClassDef(self, node: ast.ClassDef):
                start_line, end_line = self._get_node_lines(node)
                class_info = ClassInfo(node.name, start_line, end_line)
                self.classes[node.name] = class_info
                self.current_class = class_info
                self.generic_visit(node)
                self.current_class = None

            def visit_FunctionDef(self, node: ast.FunctionDef):
                start_line, end_line = self._get_node_lines(node)
                if self.current_class:
                    self.current_class.add_method(node.name, start_line, end_line)
                self.generic_visit(node)

            def visit_Compare(self, node: ast.Compare):
                self.conditions[node.lineno] = node
                if self.current_class:
                    self.current_class.conditions += 1
                self.generic_visit(node)

            def visit_BoolOp(self, node: ast.BoolOp):
                self.conditions[node.lineno] = node
                if self.current_class:
                    self.current_class.conditions += 1
                self.generic_visit(node)

            def visit_UnaryOp(self, node: ast.UnaryOp):
                if isinstance(node.op, ast.Not):
                    self.conditions[node.lineno] = node
                    if self.current_class:
                        self.current_class.conditions += 1
                self.generic_visit(node)

            def _get_node_lines(self, node: ast.AST) -> Tuple[int, int]:
                start_line = getattr(node, 'lineno', 0)
                end_line = getattr(node, 'end_lineno', start_line)
                return start_line, end_line

        visitor = ConditionVisitor()
        visitor.visit(self.tree)
        self.conditions = visitor.conditions
        self.classes = visitor.classes
        return len(self.conditions)

    def analyze_file(self, coverage_data: Dict) -> Tuple[int, int]:
        """Analyze the file and return (total_conditions, covered_conditions)."""
        total_conditions = self.find_conditions()
        covered_conditions = 0
        executed_lines = coverage_data.get('executed_lines', set())

        # Analyze file-level conditions
        for line_no in self.conditions:
            if line_no in executed_lines:
                covered_conditions += 1
                self.covered_conditions.add(line_no)

        # Update class-level coverage
        for class_info in self.classes.values():
            class_covered = 0
            for line_no in self.conditions:
                if (line_no in executed_lines and 
                    class_info.start_line <= line_no <= class_info.end_line):
                    class_covered += 1
            class_info.covered_conditions = class_covered

        return total_conditions, covered_conditions

    def get_class_coverage(self) -> Dict[str, Dict]:
        """Get coverage information for each class."""
        class_coverage = {}
        for class_name, class_info in self.classes.items():
            if class_info.conditions == 0:
                coverage_percent = 100.0
            else:
                coverage_percent = (class_info.covered_conditions / class_info.conditions) * 100

            class_coverage[class_name] = {
                'total_conditions': class_info.conditions,
                'covered_conditions': class_info.covered_conditions,
                'coverage_percentage': coverage_percent,
                'methods': {}
            }

            # Calculate method-level coverage
            for method_name, (start_line, end_line) in class_info.methods.items():
                method_conditions = 0
                method_covered = 0
                for line_no, _ in self.conditions.items():
                    if start_line <= line_no <= end_line:
                        method_conditions += 1
                        if line_no in self.covered_conditions:
                            method_covered += 1

                if method_conditions == 0:
                    method_coverage = 100.0
                else:
                    method_coverage = (method_covered / method_conditions) * 100

                class_coverage[class_name]['methods'][method_name] = {
                    'total_conditions': method_conditions,
                    'covered_conditions': method_covered,
                    'coverage_percentage': method_coverage
                }

        return class_coverage