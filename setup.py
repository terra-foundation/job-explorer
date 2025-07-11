from setuptools import setup, find_packages

setup(
    name="jobserp-explorer",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
        "jobserp-explorer=jobserp_explorer.cli:main",        ],
    },
    package_data={
        "jobserp_explorer": [
            "flow_jobposting/*.json",
            "flow_jobposting/*.jinja2",
            "flow_jobposting/*.yaml",
            "flow_pagecateg/*.json",
            "flow_pagecateg/*.jinja2",
            "flow_pagecateg/*.yaml",
            "assets/css/*.css",
            "assets/img/*.*",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.9",
)
