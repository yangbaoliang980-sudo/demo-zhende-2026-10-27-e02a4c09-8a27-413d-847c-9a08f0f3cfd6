"""P18 reward/recovery/atomic author tests, a subset of tools/author_tests.py."""
import unittest

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'tests.stage_unit.test_settlement', 'tests.stage_unit.test_recovery', 'tests.stage_unit.test_transactions'])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
