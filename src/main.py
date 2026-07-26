#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序入口"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import run_gui

if __name__ == "__main__":
    run_gui()