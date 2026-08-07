#!/usr/bin/env python3
"""Deprecated compatibility wrapper; use qualityctl.py report-check."""
from __future__ import annotations

from qualityctl import parser


if __name__ == "__main__":
    args = parser().parse_args()
    args.func(args)
