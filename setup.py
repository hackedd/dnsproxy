#!/usr/bin/env python
from distutils.core import setup

setup(name="dnsproxy",
      version="1.0",
      description="Forwarding DNS Proxy",
      author="Paul Hooijenga",
      author_email="paulhooijenga@gmail.com",
      url="https://github.com/hackedd/dnsproxy",
      packages=["dnsproxy"],
      requires=["dnspython (>=1.0.0)"])
