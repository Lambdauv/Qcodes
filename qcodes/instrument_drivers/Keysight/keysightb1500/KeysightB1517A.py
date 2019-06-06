from typing import Optional, Dict, Any, Union, TYPE_CHECKING

from .KeysightB1500_module import B1500Module, parse_spot_measurement_response
from .message_builder import MessageBuilder
from . import constants
from .constants import ModuleKind, ChNr
if TYPE_CHECKING:
    from .KeysightB1500 import KeysightB1500


class B1517A(B1500Module):
    MODULE_KIND = ModuleKind.SMU

    def __init__(self, parent: 'KeysightB1500', name: Optional[str], slot_nr,
                 **kwargs):
        super().__init__(parent, name, slot_nr, **kwargs)

        self.channels = (ChNr(slot_nr),)

        self._measure_config: Dict[str, Optional[Any]] = {
            k: None for k in ("measure_range",)}
        self._source_config: Dict[str, Optional[Any]] = {
            k: None for k in ("output_range", "compliance",
                              "compl_polarity", "min_compliance_range")}

        self.add_parameter(
            name="voltage",
            set_cmd=self._set_voltage,
            get_cmd=self._get_voltage
        )

        self.add_parameter(
            name="current",
            set_cmd=self._set_current,
            get_cmd=self._get_current
        )

    def _set_voltage(self, value: float) -> None:
        if self._source_config["output_range"] is None:
            self._source_config["output_range"] = constants.VOutputRange.AUTO
        if not isinstance(self._source_config["output_range"],
                          constants.VOutputRange):
            raise TypeError(
                "Asking to force current, but source_config contains a "
                "voltage output range"
            )
        msg = MessageBuilder().dv(
            chnum=self.channels[0],
            v_range=self._source_config["output_range"],
            voltage=value,
            i_comp=self._source_config["compliance"],
            comp_polarity=self._source_config["compl_polarity"],
            i_range=self._source_config["min_compliance_range"],
        )
        self.write(msg.message)

    def _set_current(self, value: float) -> None:
        if self._source_config["output_range"] is None:
            self._source_config["output_range"] = constants.IOutputRange.AUTO
        if not isinstance(self._source_config["output_range"],
                          constants.IOutputRange):
            raise TypeError(
                "Asking to force current, but source_config contains a "
                "voltage output range"
            )
        msg = MessageBuilder().di(
            chnum=self.channels[0],
            i_range=self._source_config["output_range"],
            current=value,
            v_comp=self._source_config["compliance"],
            comp_polarity=self._source_config["compl_polarity"],
            v_range=self._source_config["min_compliance_range"],
        )
        self.write(msg.message)

    def _get_current(self) -> float:
        try:
            msg = MessageBuilder().ti(
                chnum=self.channels[0],
                i_range=self._measure_config["measure_range"],
            )
            response = self.ask(msg.message)

            parsed = parse_spot_measurement_response(response)
            return parsed["value"]
        except AttributeError:
            raise ValueError(
                "Measurement range unconfigured. Call B1517A.measure_config() "
                "before using measure commands."
            )

    def _get_voltage(self) -> float:
        try:
            msg = MessageBuilder().tv(
                chnum=self.channels[0],
                v_range=self._measure_config["measure_range"],
            )
            response = self.ask(msg.message)

            parsed = parse_spot_measurement_response(response)
            return parsed["value"]

        except AttributeError:
            raise ValueError(
                "Measurement range unconfigured. Call B1517A.measure_config() "
                "before using measure commands."
            )

    def source_config(
            self,
            output_range: constants.OutputRange,
            compliance: Optional[Union[float, int]] = None,
            compl_polarity: Optional[constants.CompliancePolarityMode] = None,
            min_compliance_range: Optional[constants.OutputRange] = None,
    ) -> None:
        if min_compliance_range is not None:
            if isinstance(min_compliance_range, type(output_range)):
                raise TypeError(
                    "When forcing voltage, min_compliance_range must be an "
                    "current output range (and vice versa)."
                )

        self._source_config = {
            "output_range": output_range,
            "compliance": compliance,
            "compl_polarity": compl_polarity,
            "min_compliance_range": min_compliance_range,
        }

    def measure_config(self, measure_range: constants.MeasureRange) -> None:
        self._measure_config = {"measure_range": measure_range}
