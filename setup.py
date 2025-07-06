"""
Production-ready setup configuration for django-partstream.
"""

from setuptools import setup, find_packages
import os

# Read README file
readme_file = "README.md"
if not os.path.exists(readme_file):
    readme_file = "README_SIMPLE.md"

with open(readme_file, "r", encoding="utf-8") as fh:
    long_description = fh.read()


# Read requirements
def read_requirements(filename):
    """Read requirements from file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        return []


# Core requirements
install_requires = [
    "Django>=4.2,<6.0",  # Support Django 4.2+ and 5.x
    "djangorestframework>=3.14,<4.0",
    "cryptography>=3.4,<42.0",  # For secure cursor encryption
]

# Development requirements
dev_requirements = [
    "pytest>=7.0",
    "pytest-django>=4.5",
    "pytest-cov>=4.0",
    "black>=23.0",
    "flake8>=6.0",
    "mypy>=1.0",
    "pre-commit>=3.0",
    "tox>=4.0",
    "sphinx>=6.0",
    "sphinx-rtd-theme>=1.2",
]

# Production requirements
production_requirements = [
    "gunicorn>=20.0",
    "redis>=4.0",  # For caching and rate limiting
    "psycopg2-binary>=2.9",  # PostgreSQL adapter
]

# Testing requirements
testing_requirements = [
    "pytest>=7.0",
    "pytest-django>=4.5",
    "pytest-cov>=4.0",
    "pytest-mock>=3.10",
    "factory-boy>=3.2",
    "freezegun>=1.2",
]

# Documentation requirements
docs_requirements = [
    "sphinx>=6.0",
    "sphinx-rtd-theme>=1.2",
    "sphinx-autodoc-typehints>=1.19",
    "myst-parser>=1.0",
]

setup(
    name="django-partstream",
    version="1.0.0",
    author="Django PartStream Team",
    author_email="team@django-partstream.com",
    description="Transform slow Django APIs into lightning-fast progressive experiences",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/django-partstream/django-partstream",
    packages=find_packages(exclude=["tests*", "example_project*"]),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Environment :: Web Environment",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        "dev": dev_requirements,
        "production": production_requirements,
        "testing": testing_requirements,
        "docs": docs_requirements,
        "all": dev_requirements
        + production_requirements
        + testing_requirements
        + docs_requirements,
    },
    entry_points={
        "console_scripts": [
            "partstream-health-check=django_partstream.management.commands.partstream_health_check:Command",
        ],
    },
    keywords=[
        "django",
        "rest",
        "api",
        "progressive",
        "streaming",
        "performance",
        "chunks",
        "parts",
        "lazy",
        "caching",
        "optimization",
        "mobile",
        "bandwidth",
        "latency",
        "pagination",
        "cursor",
        "progressive-delivery",
    ],
    project_urls={
        "Homepage": "https://github.com/django-partstream/django-partstream",
        "Documentation": "https://django-partstream.readthedocs.io/",
        "Repository": "https://github.com/django-partstream/django-partstream",
        "Bug Reports": "https://github.com/django-partstream/django-partstream/issues",
        "Changelog": "https://github.com/django-partstream/django-partstream/blob/main/CHANGELOG.md",
        "Funding": "https://github.com/sponsors/django-partstream",
    },
    license="MIT",
    platforms=["any"],
    zip_safe=False,  # Required for Django apps
    # Additional metadata for production
    maintainer="Django PartStream Team",
    maintainer_email="maintainers@django-partstream.com",
    # Package data
    package_data={
        "django_partstream": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
            "locale/*/LC_MESSAGES/*.po",
            "locale/*/LC_MESSAGES/*.mo",
        ],
    },
    # Manifest template
    data_files=[
        ("", ["LICENSE", "CHANGELOG.md"]),
    ],
)
