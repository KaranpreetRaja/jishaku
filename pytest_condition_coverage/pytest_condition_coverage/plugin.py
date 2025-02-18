from coverage.files import PathAliases
from coverage.data import CoverageData
import pytest
import os
from typing import Dict, List, Optional
import json
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConditionCoveragePlugin:
    def __init__(self):
        self.coverage_data = None
        self.condition_coverage_results = {}
        self.package_name = None

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionstart(self, session):
        # Try to determine package name from pytest args
        if session.config.args:
            for arg in session.config.args:
                if arg.startswith('--cov='):
                    self.package_name = arg.split('=')[1]
                    break
        
        logger.info(f"Initializing condition coverage for package: {self.package_name}")
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session):
        # Load coverage data
        coverage_data = CoverageData()
        coverage_data.read()
        self.coverage_data = coverage_data
        
        logger.info("Calculating condition coverage...")
        self._calculate_condition_coverage()
        
        logger.info("Generating reports...")
        self._generate_report()
        
        yield

    def _find_package_files(self) -> List[str]:
        """Find all Python files in the package."""
        if not self.package_name:
            logger.warning("No package name specified. Using current directory.")
            base_path = "."
        else:
            base_path = self.package_name

        python_files = []
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.abspath(os.path.join(root, file))
                    python_files.append(full_path)
        
        logger.info(f"Found {len(python_files)} Python files")
        return python_files

    def _calculate_condition_coverage(self):
        """Calculate condition coverage for all Python files."""
        files_to_analyze = self._find_package_files()
        measured_files = set(self.coverage_data.measured_files())
        
        logger.info(f"Found {len(measured_files)} files with coverage data")
        
        for file_path in files_to_analyze:
            abs_path = os.path.abspath(file_path)
            if abs_path not in measured_files:
                logger.warning(f"No coverage data for: {file_path}")
                continue
                
            try:
                with open(file_path, 'r') as f:
                    source = f.read()
                
                from .analyzer import ConditionCoverageAnalyzer
                analyzer = ConditionCoverageAnalyzer(source)
                
                # Get line coverage data
                lines = self.coverage_data.lines(abs_path) or set()
                file_coverage = {'executed_lines': lines}
                
                total, covered = analyzer.analyze_file(file_coverage)
                condition_cov = (covered / total * 100) if total > 0 else 100.0
                
                # Get class coverage information
                class_coverage = analyzer.get_class_coverage()
                
                logger.info(f"File: {file_path}")
                logger.info(f"Total conditions: {total}")
                logger.info(f"Covered conditions: {covered}")
                logger.info(f"Coverage: {condition_cov:.1f}%")
                
                self.condition_coverage_results[file_path] = {
                    'condition_coverage': condition_cov,
                    'total_conditions': total,
                    'covered_conditions': covered,
                    'classes': class_coverage
                }
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")


    def _generate_report(self):
        """Generate reports with condition coverage."""
        report_dir = "htmlcov"
        os.makedirs(report_dir, exist_ok=True)
        
        report_data = {
            'files': {},
            'total_condition_coverage': 0.0
        }
        
        total_conditions = 0
        covered_conditions = 0
        
        for file_path, data in self.condition_coverage_results.items():
            relative_path = os.path.relpath(file_path)
            total_conditions += data['total_conditions']
            covered_conditions += data['covered_conditions']
            
            # Include both file coverage and class coverage in the report data
            report_data['files'][relative_path] = {
                'condition_coverage': data['condition_coverage'],
                'total_conditions': data['total_conditions'],
                'covered_conditions': data['covered_conditions'],
                'classes': data.get('classes', {})  # Include class data if it exists
            }
        
        if total_conditions > 0:
            report_data['total_condition_coverage'] = (covered_conditions / total_conditions) * 100
        
        # Save JSON report
        report_path = os.path.join(report_dir, 'condition_coverage.json')
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        # Generate HTML report
        html_report = self._generate_html_report(report_data)
        html_path = os.path.join(report_dir, 'condition_coverage.html')
        with open(html_path, 'w') as f:
            f.write(html_report)
        
        logger.info(f"Reports generated in {report_dir}")
        logger.info("Debug: Number of files with class data: " + 
                   str(sum(1 for f in report_data['files'].values() if 'classes' in f)))

    def _generate_html_report(self, data: Dict) -> str:
        """Generate HTML report from coverage data."""
        total_coverage = data.get('total_condition_coverage', 0.0)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Condition Coverage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .coverage-good {{ background-color: #dff0d8; }}
        .coverage-warning {{ background-color: #fcf8e3; }}
        .coverage-bad {{ background-color: #f2dede; }}
        .class-header {{ background-color: #e9ecef; font-weight: bold; }}
        .method-row {{ background-color: #f8f9fa; }}
        .indent {{ padding-left: 40px; }}
        .double-indent {{ padding-left: 80px; }}
        .file-row {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Condition Coverage Report</h1>
    <h2>Total Condition Coverage: {total_coverage:.1f}%</h2>
    
    <h3>Coverage Details</h3>
    <table>
        <tr>
            <th>Name</th>
            <th>Coverage</th>
            <th>Covered/Total</th>
        </tr>"""

        # File coverage with nested class and method information
        for file_path, file_data in data['files'].items():
            coverage = file_data['condition_coverage']
            coverage_class = 'coverage-good' if coverage >= 80 else 'coverage-warning' if coverage >= 60 else 'coverage-bad'
            
            html += f"""
        <tr class="{coverage_class} file-row">
            <td>{file_path}</td>
            <td>{coverage:.1f}%</td>
            <td>{file_data['covered_conditions']}/{file_data['total_conditions']}</td>
        </tr>"""

            # Add class coverage
            if 'classes' in file_data and file_data['classes']:
                for class_name, class_data in file_data['classes'].items():
                    class_coverage = class_data['coverage_percentage']
                    class_coverage_class = 'coverage-good' if class_coverage >= 80 else 'coverage-warning' if class_coverage >= 60 else 'coverage-bad'
                    
                    html += f"""
        <tr class="{class_coverage_class}">
            <td class="indent">Class: {class_name}</td>
            <td>{class_coverage:.1f}%</td>
            <td>{class_data['covered_conditions']}/{class_data['total_conditions']}</td>
        </tr>"""

                    # Add method coverage
                    if 'methods' in class_data:
                        for method_name, method_data in class_data['methods'].items():
                            method_coverage = method_data['coverage_percentage']
                            method_coverage_class = 'coverage-good' if method_coverage >= 80 else 'coverage-warning' if method_coverage >= 60 else 'coverage-bad'
                            
                            html += f"""
        <tr class="{method_coverage_class}">
            <td class="double-indent">Method: {method_name}</td>
            <td>{method_coverage:.1f}%</td>
            <td>{method_data['covered_conditions']}/{method_data['total_conditions']}</td>
        </tr>"""

        html += """
    </table>
</body>
</html>"""
        return html

def pytest_configure(config):
    config.pluginmanager.register(ConditionCoveragePlugin())