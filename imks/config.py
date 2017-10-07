from . import units

config = {"banner": True,
          "enabled": True,
          "auto_brackets": True,
          "standard_exponent": True,
          "engine": "",
          "sort_units": units.sortunits,
          "unit_tolerant": units.tolerant,
          "prefix_only": units.prefixonly,
          "show_errors": units.showerrors,
          "digits": 15,
          "min_fixed": None,
          "max_fixed": None}
internals = {"engine": "ufloat",
             "engine_module": None,
             "extensions": set()}
