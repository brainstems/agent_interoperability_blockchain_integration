"""
Setup script for the infrastructure package.
"""

from setuptools import setup, find_packages

setup(
    name="infrastructure",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "pytest-asyncio",
        "psutil"
    ],
    test_suite="tests",
    package_data={
        "": ["*.py"]
    }
)
