# -*- coding: utf-8 -*-

import unittest
from . import units, currencies
from .config import *

class UnitTestCase(unittest.TestCase):
    def setUp(self):
        from . import imks_standalone
        units.reset()
        currencies.reset()
        config['banner'] = ""
        imks = imks_standalone.load_imks()
        self.shell = imks.shell

    def run_line(self, line):
        self.shell.push(u"_res_=" + line)
        result = self.shell.locals['_res_']
        s = str(result).split('[')
        if len(s) == 1:
            return result, float(s[0]), ''
        else:
            return result, float(s[0]), s[1][:-1]

    def test_conversions(self):
        tests = [("12m+3cm@km", "0.01203[km]"),
                 ("20[m/s]@[km|hour]", "72.0[km hour^-1]"),
                 ("20[m/s]@[km|hour|mph]", "44.73872584108805[mph]"),
                 ("3['g']", "29.41995[m s^-2]"),
                 ("5[us 'c']@km", "1.49896229[km]"),
                 ("300000[km] @ [s 'c']", "1.00069228559446[s 'c']"),
                 ("1e27[kg] @ ['c'|'G']", "0.742591548611['c'^2 m 'G'^-1]"),
                 ("~1e5K @ ['k'|eV]", "8.61733033722[eV 'k'^-1]"),
                 ('300000[km] @ [s|"c"]', "1.00069228559446[s]"),
                 ("300[K] @ [Celsius]", "26.85[Celsius]"),
                 ("1200s @ k", "1.2[ks]"),
                 ("1200[s] @ [k|M]", "1.2[ks]"),
                 ("8[m]  @  [.|k|M]", "8.0[m]"),
                 ("0.12[cm] @ [m|*]", "1.2[mm]"),
                 ("12[cm] @ [m]", "0.12[m]"),
                 ("12[cm] @ [m*]", "120.0[mm]"),
                 ("1200[m] @ [*m]", "1.2[km]"),
                 ("72[km/hour] @ [si]", "20.0[m s^-1]"),
                 ("5600[K] @ [*si]", "5.6[kK]"),
                 ("5600[K] @ [si|*]", "5.6[kK]"),
                 ("5600[K] @ [SI]", "5.6[kK]"),
                 ("1e-34[m] @ [planck]", "6.187244430648[]"),
                 ("6.2e34 @ [m|planck]", "1.0020615913101[m]"),
                 ("1 @ [planck|kg]", "1[]"),
                 ('1e-27 @ [kg/m|"c"|"G"]', "1.3466353096409[kg m^-1]"),
                 ('1 @ [kg|m|"c"|"G"]', "1[]"),
                 ("1e8 @ [kg|'planck']",
                  "2.1764701956342['G'^1/2 'c'^-1/2 'hbar'^-1/2 kg]"),
                 ("2.1764701956342e-8['G'^1/2 'c'^-1/2 'hbar'^-1/2 kg]", "1[]")]
                 
        for x1, x2 in tests:
            c1, v1, u1 = self.run_line(x1)
            v2, u2 = x2.split('[')
            v2 = float(v2)
            u2 = u2[:-1]
            self.assertAlmostEqual(v1, v2,
                msg="Conversion failed: %s != %s" % (x1, x2))
            self.assertEqual(u1, u2,
                msg="Conversion failed (unit error): %s != %s" % (u1, u2))

    def test_functions(self):
        tests = [("sqrt(3m)", "1.7320508075689[m^1/2]"),
                 ("sqrt(3[m]^2+16m^2)", "5.0[m]"),
                 ("(G*c)^(1/3)", "0.27147970608887[m^4/3 s^-1 kg^-1/3]"),
                 ("atan2(3km, 2[mi]) @ deg", "42.9859516735[deg]"),
                 ("fraction(3m, 2s)", "1.5[m s^-1]")]
        for x1, x2 in tests:
            c1, v1, u1 = self.run_line(x1)
            v2, u2 = x2.split('[')
            v2 = float(v2)
            u2 = u2[:-1]
            self.assertAlmostEqual(v1, v2,
                msg="Operation failed: %s = %s[%s] != %s" % (x1, v1, u1, x2))
            self.assertEqual(u1, u2,
                msg="Operation failed (unit error): %s != %s" % (u1, u2))

    def test_calendars(self):
        tests = [('Gregorian(1900, 2, 28) + 1[day]', 'Thursday, 1 March 1900'),
                 ('(Julian(1900, 2, 28) + 1[day]).month', '2'),
                 ('Gregorian(1973, "Easter")', "Sunday, 22 April 1973"),
                 ("2020.1.1", "Wednesday, 1 January 2020"),
                 ('Julian(1973, "Easter")', "Solis dies (Dies dominica), 9 Aprilis 1973 C.E."),
                 ('Hebrew(5778, "Passover")', "Yom shabbat, 15 Nisan 5778"),
                 ('Gregorian("today") - Gregorian("yesterday") @ day', "1.0[day]"),
                 ('Tibetan(2144, "snron", 0, 3, 0)', "gza' nyi ma, 3 snron 2144")]
        self.shell.push(u"%load_imks_ext calendars")
        for x1, x2 in tests:
            if "[" in x2:
                c1, v1, u1 = self.run_line(x1)
                v2, u2 = x2.split('[')
                v2 = float(v2)
                u2 = u2[:-1]
                self.assertAlmostEqual(v1, v2,
                    msg="Operation failed: %s = %s[%s] != %s" % (x1, v1, u1, x2))
                self.assertEqual(u1, u2,
                    msg="Operation failed (unit error): %s != %s" % (u1, u2))
            else:
                self.shell.push(u"_res_=" + x1)
                r1 = str(self.shell.locals['_res_'])
                self.assertEqual(r1, x2,
                    msg="Operation failed: %s = %s != %s" % (x1, r1, x2))

            
if __name__ == '__main__':
    unittest.main()
