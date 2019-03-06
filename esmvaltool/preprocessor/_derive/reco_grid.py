"""Derivation of variable `reco`."""

import logging

from ._derived_variable_base import DerivedVariableBase
from ._shared import grid_area_correction

logger = logging.getLogger(__name__)


class DerivedVariable(DerivedVariableBase):
    """Derivation of variable `reco`."""

    # Required variables
    _required_variables = {
        'vars': [{
            'short_name': 'reco',
            'field': 'T2{frequency}s'
        }],
        'fx_files': ['areacella', 'sftlf']
    }

    def calculate(self, cubes):
        """Compute ecosystem respiration per grid cell.

        Note
        ----
        By default, `reco` is defined relative to land area. For easy spatial
        integration, the original quantity is multiplied by the land area
        fraction (`sftlf`), so that the resuting derived variable is defined
        relative to the grid cell area. This correction is only relevant for
        coastal regions.

        """
        return grid_area_correction(cubes, 'reco')