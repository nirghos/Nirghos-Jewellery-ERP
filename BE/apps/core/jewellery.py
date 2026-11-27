"""Jewellery calculations. Decimal only - never floats."""
from decimal import Decimal, ROUND_HALF_UP

D = Decimal
W3 = D("0.001")
M2 = D("0.01")


def q3(v): return D(v).quantize(W3, rounding=ROUND_HALF_UP)
def q2(v): return D(v).quantize(M2, rounding=ROUND_HALF_UP)


def net_weight(gross, stone):
    gross, stone = D(gross), D(stone)
    if stone > gross:
        raise ValueError("Stone weight cannot exceed gross weight")
    return q3(gross - stone)


def fine_weight(net, purity):
    """purity is fineness as a fraction, e.g. 0.916 for 22K."""
    purity = D(purity)
    if not (D("0") < purity <= D("1")):
        raise ValueError("Purity must be between 0 and 1")
    return q3(D(net) * purity)


def karat_to_fineness(karat):
    return (D(karat) / D(24)).quantize(D("0.001"), rounding=ROUND_HALF_UP)


def making_charge(kind, value, net, metal_value):
    value = D(value)
    if kind == "per_gram":
        return q2(value * D(net))
    if kind == "percent":
        return q2(D(metal_value) * value / D(100))
    if kind == "fixed":
        return q2(value)
    raise ValueError("Unknown making charge type")
