from setuptools import setup, find_packages

setup(
    name="douyin-fashion-clip-remix",
    version="0.1.0",
    description="Automatic clip remixing for Douyin fashion/live-commerce videos",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="https://github.com/your-org/douyin-fashion-clip-remix",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "clip-remix-classify=clip_remix.classifier:main",
            "clip-remix-compose=clip_remix.composer:main",
            "clip-remix-render=clip_remix.renderer:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video :: Conversion",
    ],
)
