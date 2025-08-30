from setuptools import setup, find_packages
from pathlib import Path
import os

# Read version from VERSION file
version_file = Path(__file__).parent / "VERSION"
if not version_file.exists():
    raise FileNotFoundError("VERSION file not found. Please create it with the version number.")
version = version_file.read_text().strip()

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
else:
    requirements = []

# Collect data files for installation
data_files = []
for root, dirs, files in os.walk("data"):
    if files:
        # Convert path for installation
        install_dir = root
        file_list = [os.path.join(root, f) for f in files]
        data_files.append((install_dir, file_list))

# Add scripts to data_files
if os.path.exists("scripts"):
    script_files = []
    for f in os.listdir("scripts"):
        if os.path.isfile(os.path.join("scripts", f)):
            script_files.append(os.path.join("scripts", f))
    if script_files:
        data_files.append(("scripts", script_files))

setup(
    name="unbound-manager",
    version=version,
    author="Regix",
    description="A modern Unbound DNS server management tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/regix1/unbound-manager",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "unbound-manager=unbound_manager.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["VERSION", "*.yaml", "*.j2", "*.sh", "*.py"],
        "unbound_manager": ["../data/**/*"],
    },
    data_files=data_files,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: Name Service (DNS)",
    ],
)