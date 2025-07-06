from setuptools import setup, find_packages

setup(
    name="ocelot_log_service",
    version="0.1.0",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        # List dependencies from requirements.txt here
        "fastapi",
        "uvicorn",
        "boto3",
        "pymongo",
        "python-jose",
        "passlib",
        "python-dotenv",
        "pydantic-settings",
        "opensearch-py",
        "requests-aws4auth",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "httpx",  # Required for FastAPI TestClient
        ]
    },
) 