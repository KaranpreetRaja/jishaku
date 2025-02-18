from setuptools import setup, find_packages

setup(
    name="pytest-condition-coverage",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
        "coverage>=7.0.0",
    ],
    entry_points={
        "pytest11": ["condition-coverage = pytest_condition_coverage.plugin"],
    },
)