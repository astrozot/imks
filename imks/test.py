import numpy as np

class Value(np.ndarray):

    def __new__(cls, input, unit=None, absolute=None, original=False):
        obj = np.asanyarray(input).view(cls)
        # add the new attributes to the instance
        if unit:
            if isinstance(unit, str):
                print("setting unit from string = %s" % unit)
                obj.unit = unit
            else:
                print("setting unit = %s" % unit)
                obj.unit = str(unit) if unit else "[]"
        else:
            print("No unit provided.")
            if not hasattr(obj, "unit"):
                obj.unit = "[]"
        return obj

    def __array_finalize__(self, obj):
        print("Object finalize: %s" % type(obj))
        # Call from explicit constructor
        if obj is None: return
        print("  obj.unit = %s" % getattr(obj, "unit", "<none>"))
        # Call from view casting (obj is array) or slice (obj is Value)
        self.unit = getattr(obj, "unit", "[]")

    def __array_prepare__(self, array, context=None):
        print("__array_prepare")
        print(repr(self))
        print(repr(context))
        results = super(Value, self).__array_prepare__(array, context)
        return results