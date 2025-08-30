from setuptools import setup, find_packages
from pathlib import Path

version_file = Path(__file__).parent / "VERSION"
version = version_file.read_text().strip() if version_file.exists() else "2.0.5"

readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

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
    scripts=[
        "scripts/install.sh",
        "scripts/uninstall.sh", 
        "scripts/update.sh",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: Name Service (DNS)",
    ],
)