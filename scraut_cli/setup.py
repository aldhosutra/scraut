from setuptools import setup, find_packages

setup(
    name="scraut",
    version="1.0.0",
    description="Scraut CLI — quick access to your Scrum Automation system",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "scraut=scraut_cli.cli:main",
        ],
    },
    install_requires=[
        "click>=8.1.7",
        "anthropic>=0.28.0",
        "PyGitHub>=2.3.0",
        "PyYAML>=6.0.1",
    ],
    python_requires=">=3.11",
)
