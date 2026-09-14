"""
Temperature-dependent 304/304L material property correlations.

These are the *corrected* formulas from workbook Sec. 4.2/4.3 (NIST
trc.nist.gov/cryogenics/materials fits), not the earlier uncorrected
thermal-expansion coefficients that the workbook explicitly flags as a
transcription error (see the dL/L docstring below). All functions take T in
Kelvin, per Sec. 4.2's confirmation that NIST's own equation documentation
uses Kelvin.

Substitution note (Sec. 4.2/4.3): cp(T) and E(T) use NIST's 304 (UNS S30400)
fits, not 304L, because NIST's own 304L fits either cover too narrow a range
(cp: 4-23 K only) or aren't published at all (E). The workbook treats this as
a reasonable engineering substitution (the "L" only affects carbon content /
corrosion resistance, not thermal-elastic behavior) but says to flag it, not
present it as native 304L data -- flagged here via the SUBSTITUTED_304_FOR_304L
markers below.
"""

from __future__ import annotations

import math

SUBSTITUTED_304_FOR_304L = {
    "specific_heat": True,   # Sec. 4.2
    "youngs_modulus": True,  # Sec. 4.3 (NIST 304L page has no published E(T) table)
    "thermal_conductivity": False,  # Sec. 4.2: valid 1-300K, no substitution noted
}

# Valid ranges per Sec. 4.2/4.3 (NIST). Values outside these are clipped and
# the clipped T is what's actually evaluated -- callers should treat results
# near/at the boundary as extrapolated.
K_VALID_RANGE_K = (4.0, 300.0)          # data range; equation itself valid 1-300K
CP_VALID_RANGE_K = (4.0, 300.0)
DLL_LOW_T_CUTOFF_K = 23.0               # below this, dL/L is the NIST constant
E_LOW_RANGE_K = (5.0, 57.0)
E_HIGH_RANGE_K = (57.0, 293.0)


def _clip(t_k: float, lo: float, hi: float) -> float:
    return min(max(t_k, lo), hi)


def thermal_conductivity_w_mk(t_k: float) -> float:
    """k(T), Sec. 4.2. Sanity-check point in the workbook: k ~= 1-3 W/m*K
    near -253 C (~20 K), with 2.71 W/m*K cited as a reference value."""
    t = _clip(t_k, *K_VALID_RANGE_K)
    x = math.log10(t)
    log10_k = (
        -1.4087
        + 1.3982 * x
        + 0.2543 * x**2
        - 0.6260 * x**3
        + 0.2334 * x**4
        + 0.4256 * x**5
        - 0.4658 * x**6
        + 0.1650 * x**7
        - 0.0199 * x**8
    )
    return 10**log10_k


def specific_heat_j_kgk(t_k: float) -> float:
    """cp(T), Sec. 4.2 -- BUT with corrected coefficients, not the workbook's.

    The coefficients as transcribed in Sec. 4.2 (c..i terms) are themselves a
    second transcription error, separate from the dL/L bug the workbook
    already caught: evaluated as given, they make cp *decrease* toward ~0 as
    T rises to 293 K, which is backwards (specific heat of 304 SS should rise
    toward ~500 J/kg*K near room temperature per Dulong-Petit/known data, not
    vanish). Confirmed by re-fetching trc.nist.gov/cryogenics/materials'
    304 Stainless Steel page directly: NIST's actual coefficients differ from
    the workbook's from the c-term onward. Using NIST's real values here:
        a=22.0061 b=-127.5528 c=303.647 d=-381.0098 e=274.0328
        f=-112.9212 g=24.7593 h=-2.239153 i=0
    (a, b match the workbook exactly -- only c..h drift, i is dropped to 0.)
    This produces cp(20K)~13 J/kgK, cp(293K)~470 J/kgK, both physically
    sane. This discrepancy is NOT documented in the workbook and should be
    flagged back to engineering alongside the dL/L fix.
    """
    t = _clip(t_k, *CP_VALID_RANGE_K)
    x = math.log10(t)
    log10_cp = (
        22.0061
        - 127.5528 * x
        + 303.647 * x**2
        - 381.0098 * x**3
        + 274.0328 * x**4
        - 112.9212 * x**5
        + 24.7593 * x**6
        - 2.239153 * x**7
        + 0.0 * x**8
    )
    return 10**log10_cp


def thermal_expansion_dl_l(t_k: float) -> float:
    """dL/L(T) relative to 293 K, Sec. 4.2 CORRECTED coefficients.

    The workbook's earlier engineering doc had the b..e coefficients each off
    by ~10x from NIST's actual (x1e-5-scaled) values -- caught via two
    independent checks: (1) self-consistency, dL/L(293K) must be ~0 by
    definition, which only the corrected coefficients satisfy; (2) an
    independent Fermilab cryogenics paper's measured -0.281% contraction
    293K->77K for 304 SS, which the corrected formula matches to 0.001 pp.
    The UNCORRECTED coefficients are intentionally not reproduced here.
    """
    if t_k < DLL_LOW_T_CUTOFF_K:
        return -3.0004e-3
    t = t_k
    return (
        -2.9554e-3
        - 3.9811e-6 * t
        + 9.2683e-8 * t**2
        - 2.0261e-10 * t**3
        + 1.7127e-13 * t**4
    )


def youngs_modulus_gpa(t_k: float) -> float:
    """E(T), Sec. 4.3. NIST 304 fit substituted for 304L (no NIST 304L
    E(T) table is published -- see module docstring). Piecewise at 57 K."""
    if t_k <= E_LOW_RANGE_K[1]:
        t = _clip(t_k, *E_LOW_RANGE_K)
        return (
            209.8145
            + 0.1217019 * t
            - 0.01146999 * t**2
            + 0.0003605430 * t**3
            - 0.0000030179 * t**4
        )
    t = _clip(t_k, *E_HIGH_RANGE_K)
    return (
        210.0593
        + 0.1534883 * t
        - 0.00161739 * t**2
        + 0.000005117060 * t**3
        - 0.000000006154600 * t**4
    )


if __name__ == "__main__":
    for t in (20.0, 77.0, 150.0, 293.0):
        print(
            f"T={t:6.1f} K  k={thermal_conductivity_w_mk(t):6.3f} W/mK  "
            f"cp={specific_heat_j_kgk(t):8.2f} J/kgK  "
            f"dL/L={thermal_expansion_dl_l(t)*100:7.4f} %  "
            f"E={youngs_modulus_gpa(t):7.2f} GPa"
        )
