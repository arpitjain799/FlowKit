from flowmachine.core import Query
from flowmachine.features.location.flows import BaseInOutFlow
from flowmachine.features.location.redacted_location_metric import (
    RedactedLocationMetric,
)


class RedactedInOutFlow(RedactedLocationMetric, BaseInOutFlow, Query):
    """
    An object representing the redacted summation of all movement into or out of
    a set of locations

    Parameters
    ----------
    in_out_flow : BaseInOutFlow
        The underlying Inflow or Outflow to redact; normally created from `flows.inflow` or `flows.outflow`
    """

    def __init__(self, *, in_out_flows: BaseInOutFlow):
        self.redaction_target = in_out_flows
        # self.spatial_unit is used in self._geo_augmented_query
        self.spatial_unit = in_out_flows.spatial_unit
        super().__init__(flow=in_out_flows.flow)