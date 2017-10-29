from . import units

config = {"banner": True,
          "enabled": True,
          "auto_brackets": True,
          "standard_exponent": True,
          "engine": "",
          "sort_units": units.sortunits,
          "unit_tolerant": units.tolerant,
          "unit_verbose": units.verbose,
          "prefix_only": units.prefixonly,
          "show_errors": units.showerrors,
          "complete_currencies": "maybe",
          "digits": 15,
          "min_fixed": None,
          "max_fixed": None}
internals = {"engine": "ufloat",
             "engine_module": None,
             "extensions": set()}
