"""Derivation of variable `cllmtisccp`."""

from iris import Constraint

from ._baseclass import DerivedVariableBase
from ._shared import cloud_area_fraction


class DerivedVariable(DerivedVariableBase):
    """Derivation of variable `cllmtisccp`."""

    # Required variables
    required = [{'short_name': 'clisccp'}]

    def calculate(self, cubes):
        """Compute ISCCP low level medium-thickness cloud area fraction."""
        tau = Constraint(
            atmosphere_optical_thickness_due_to_cloud=lambda t: 3.6 < t <= 23.)
        plev = Constraint(air_pressure=lambda p: p > 68000.)

        return cloud_area_fraction(cubes, tau, plev)
