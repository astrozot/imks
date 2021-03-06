# -*- coding: utf-8 -*-

import unittest
from random import randrange
from . import units, currencies
from .units import Value as V


class UnitTestCase(unittest.TestCase):
    def setUp(self):
        units.reset()
        currencies.reset()
        for b in ['m', 'g', 's', 'A', 'K', 'mol', 'cd']:
            units.newbaseunit(b)
        for k, v in [('G', 1000000000.0), ('M', 1000000.0), ('k', 1000.0),
                     ('h', 100.0), ('da', 10.0), ('', 1.0), ('d', 0.1), ('c', 0.01),
                     ('m', 0.001), ('u', 1.0e-6), ('µ', 1.0e-6), ('n', 1.0e-9)]:
            units.newprefix(k, v)
        for k, v, u in [('N', 1.0, 'kg m s^-2'),
                        ('J', 1.0, 'N m'),
                        ('W', 1.0, 'J/s'),
                        ('Pa', 1.0, 'N/m^2'),
                        ('C', 1.0, 'A s'),
                        ('h', 3600.0, 's'),
                        ('mph', 0.44704, 'm s^-1'),
                        ('eV', 1.6021766208e-19, 'm^2 kg s^-2')]:
            units.newunit(k, V(v, u))
        units.newunit('degC', (V(273.15, 'K'), V(1.0, 'K')))
        values = {'pi': V(3.1415926535898),
                  'c': V(299792458.0, 'm/s'),
                  'G': V(6.67408e-11, 'm^3 s^-2 kg^-1'),
                  'g': V(9.80665, 'm/s^2'),
                  'h': V(6.62607004e-34, 'm^2 kg s^-1'),
                  'ke': V(8987551787.3682, 'm^3 kg s^-4 A^-2'),
                  'k': V(1.38064852e-23, 'm^2 kg s^-2 K^-1')}
        values['hbar'] = values['h'] / values['pi'] / 2
        units.user_ns = values
        units.newsystem('si', ['m', 's', 'kg', 'K', 'A', 'cd', 'mol'])
        units.newsystem('SI', ['*', 'si'])
        units.newsystem('planck', ['"c"', '"hbar"', '"G"', '"ke"', '"k"'])

    def test_simple_operations(self):
        tests = [(V(12.0, 'm') + V(3.0, 'cm'), V(0.1203, 'hm')),
                 (V(7200.0, 's') - V(1.0, 'h'), V(1.0, 'h')),
                 (V(20.0, 'm/s'), V(72.0, 'km h^-1')),
                 (V(20.0, 'm/s'), V(44.738725841088, 'mph')),
                 (V(12.0, 'N') / V(2.5, 'dm^2'), V(480.0, 'Pa')),
                 (V(3.0, 'm') * V(20.0, 'dm'), V(6.0, 'm^2')),
                 (V(27.0, 'm/s') ** (1.0/3.0), V(3.0, 'm^1/3 s^-1/3')),
                 (V(300.0, 'K', absolute=0.0), V(26.85, 'degC')),
                 ((V(1.0, 'kPa')*V(40.0, 'cm^3')/V(10.0, 'g'))**0.5, V(2.0, 'km/ks')),
                 (V(4.0, 'm/s') / V(2.0, 'm/s'), V(2.0))]
        for a, b in tests:
            self.assertEqual(a.unit, b.unit,
                             msg="Unit operation failed: %s != %s" % (a, b))
            self.assertAlmostEqual((a - b).value, 0.0,
                                   msg="Unit operation failed: %s != %s" % (a, b))

    def test_comparisons(self):
        tests = [(V(1.2, 'm'), V(119.0, 'cm'), '__gt__'),
                 (V(0.1, 'm'), V(100.0, 'cm'), '__lt__'),
                 (V(12.0, 's'), V(1.3, 'das'), '__le__'),
                 (V(1.0, 'kg'), V(1000.0, 'g'), '__eq__'),
                 (V(30.0, 'm/s'), V(100.0, 'km/h'), '__ge__'),
                 (V(30.0, 'm/s'), V(30.0, 'km/h'), '__ne__')]
        for a, b, c in tests:
            self.assertTrue(getattr(a, c)(b),
                            msg="Comparison %s %s %s failed" % (a, c, b))

    def test_errors_incompatible(self):
        tests = [('m', 's'),
                 ('m', 'kg'),
                 ('m/s', 's/m'),
                 ('m/s^2', 'kg'),
                 ('kg m/s^2', 'kg/s')]
        ops = ['__add__', '__sub__', '__pow__',
               '__lt__', '__le__', '__gt__', '__ge__']
        for u1, u2 in tests:
            for op in ops:
                for n in range(10):
                    v1 = V(float(randrange(-10, 10)), u1)
                    v2 = V(float(randrange(-10, 10)), u2)
                    if v1.value == 0 or v2.value == 0:
                        continue
                    with self.assertRaisesRegexp(units.UnitError,
                                                 "\[.*\] *incompatible with *\[.*\] *in *%s" % op):
                        tmp = getattr(v1, op)(v2)

    def test_simple_conversions(self):
        tests = [(V(12.0, 'm') + V(3.0, 'cm'), (0.1203, 'hm')),
                 (V(7200.0, 's') - V(1.0, 'h'), (1.0, 'h')),
                 (V(20.0, 'm/s'), (72.0, 'km h^-1')),
                 (V(20.0, 'm/s'), (44.738725841088, 'mph')),
                 (V(12.0, 'N') / V(2.5, 'dm^2'), (480.0, 'Pa')),
                 (V(3.0, 'm') * V(20.0, 'dm'), (6.0, 'm^2')),
                 (V(27.0, 'm/s') ** (1.0/3.0), (3.0, 'm^1/3 s^-1/3')),
                 ((V(1.0, 'kPa')*V(40.0, 'cm^3')/V(10.0, 'g'))**0.5, (2.0, 'km/ks'))]
        for a, b in tests:
            x = a | units.System(b[1])
            v = x / x.showunit.to_value()
            self.assertAlmostEqual(v.value, b[0], msg="Conversion failed")
            self.assertFalse(bool(v.unit), "Conversion failed between %s and [%s]:" %
                                 (str(x.unit), b[1]))

    def test_complex_conversions(self):
        tests = [(V(20.0, 'm/s'), (72.0, 'km', 'h')),
                 (V(20.0, 'm/s'), (44.738725841088, 'km', 'h', 'mph')),
                 (V(5.0, "s 'c'"), (1498962.29, 'km')),
                 (V(3.0, "'g'"), (29.41995, 'm s^-2')),
                 (V(300000.0, 'km'), (1.00069228559446, "s 'c'")),
                 (V(1e30, 'kg'), (742.59154861063, "'c'", "'G'")),
                 (V(1200.0, 's'), (1.2, 'ks'))]
        for a, b in tests:
            x = a | units.System(*b[1:])
            v = x / x.showunit.to_value()
            self.assertAlmostEqual(v.value, b[0], msg="Conversion failed")
            self.assertFalse(bool(v.unit), "Conversion failed between %s and %s" %
                                 (str(x.unit), "|".join(b[1:])))

    def test_prefix_conversions(self):
        tests = [(V(1300.0, 's'), ('k', 'M'), '1.3[ks]'),
                 (V(8.0, 'm'), ('.', 'k', 'M'), '8.0[m]'),
                 (V(0.12, 'cm'), ('m', '*'), '1.2[mm]'),
                 (V(12.0, 'cm'), ('m*',), '120.0[mm]'),
                 (V(12.0, 'cm'), ('m',), '0.12[m]'),
                 (V(1400.0, 'm'), ('*m',), '1.4[km]')]
        for a, b, c in tests:
            x = a | units.System(*b)
            self.assertEqual(str(x), c, msg="Conversion failed")

    def test_unit_systems(self):
        tests = [(V(72.0, 'km/h'), ('si',), '20.0[m s^-1]'),
                 (V(5600.0, 'km'), ('SI',), '5.6[Mm]'),
                 (V(1.0, 'N'), ('si',), '1.0[m kg s^-2]'),
                 (V(1.0, 'm'), ('planck',), '6.18724443065e+34'),
                 (V(6.2e34), ('m', 'planck'), '1.00206159131[m]'),
                 (V(1.0), ('kg', 'planck'), '2.17647019563e-08[kg]'),
                 (V(1.0), ('kg/m', '"c"', '"G"'), '1.34663530964e+27[kg m^-1]'),
                 (V(1.0), ('kg', 'm', '"c"', '"G"'), '1.0'),
                 (V(1.0), ('kg', "'planck'"),
                  "2.17647019563e-08['G'^1/2 'c'^-1/2 'hbar'^-1/2 kg]"),
                 (V(2.1764701956342e-8, "'G'^1/2 'c'^-1/2 'hbar'^-1/2 kg"), (),
                  '1.0')]
        for a, b, c in tests:
            x = a | units.System(*b)
            self.assertEqual(str(x), c, msg="Conversion failed")


if __name__ == '__main__':
    unittest.main()
