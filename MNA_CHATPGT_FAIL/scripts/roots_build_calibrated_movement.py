#!/usr/bin/env python3
import sys

NOTE = '''
This file is intentionally a guard.

The prior version created a calibrated movement layer. That approach is no longer part of this project.
Movement observations must remain raw. Diagnostic scripts may report reliability, sensitivity, and uncertainty, but must not alter observed movement states.

Use:
  python3 MNA/scripts/roots_build_movement_diagnostics.py <book>
'''

print(NOTE, file=sys.stderr)
sys.exit(1)
