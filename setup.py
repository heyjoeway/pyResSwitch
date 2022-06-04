import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyResSwitch-heyjoeway",
    version="0.1.0",
    author="Joseph Judge",
    author_email="joe@jojudge.com",
    description="System tray resolution switcher for Windows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/heyjoeway/pyResSwitch",
    project_urls={
        "Bug Tracker": "https://github.com/heyjoeway/pyResSwitch/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    include_package_data= True,
    package_data={
        '': ['icon.png']
    },
    install_requires=[
        'pywin32',
        'pystray'
    ]
)