from setuptools import setup, find_packages

with open("README_SIMPLE.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-partstream",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Transform slow Django APIs into fast, progressive experiences by streaming data in parts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/django-partstream",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: Django",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1", 
        "Framework :: Django :: 4.2",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Django>=4.2,<5.0",
        "djangorestframework>=3.14,<4.0",
        "cryptography>=3.4",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-django>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ]
    },
    keywords="django, rest, api, progressive, streaming, performance, chunks, parts",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/django-partstream/issues",
        "Source": "https://github.com/yourusername/django-partstream",
        "Documentation": "https://github.com/yourusername/django-partstream/blob/main/GUIDE.md",
    },
) 